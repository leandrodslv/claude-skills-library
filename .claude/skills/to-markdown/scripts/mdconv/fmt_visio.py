"""Visio (.vsdx, .vsdm) → Markdown, en bibliothèque standard : une section par page, formes et connecteurs → Mermaid.

Un fichier Visio est un paquet OPC : ``visio/pages/pageN.xml`` liste les formes (avec leur texte et leur position) et les
connexions (``<Connect>`` : quelle extrémité de quel connecteur est collée à quelle forme). On en tire un graphe (nœuds =
formes étiquetées, liens = connecteurs, sens d'après les pointes de flèche), rendu en bloc ``mermaid``, plus la liste des
textes non reliés. Les anciens ``.vsd`` binaires ne sont pas lisibles sans Visio/LibreOffice (exporter en .vsdx ou PDF).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

from .core import Ctx, Result, Unsupported, engine
from .fmt_diagram import Graph, to_mermaid
from .ooxml import core_props
from .util import Rels, SafeZip, clean_text, esc_inline, local


def _cells(shape: ET.Element) -> Dict[str, str]:
    return {c.get("N", ""): c.get("V", "") for c in shape if local(c.tag) == "Cell"}


def _num(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except ValueError:
        return default


def _shape_text(shape: ET.Element) -> str:
    t = next((c for c in shape if local(c.tag) == "Text"), None)
    if t is None:
        return ""
    return clean_text("".join(t.itertext())).strip()


class _Page:
    def __init__(self, name: str):
        self.name = name
        self.shapes: Dict[str, Dict[str, object]] = {}     # id → {text, x, y, name, master, group}
        self.connects: List[Tuple[str, str, str]] = []      # (connecteur, extrémité BeginX/EndX, forme visée)


def _walk(container: ET.Element, page: _Page, group: str = "") -> None:
    for sh in container:
        if local(sh.tag) != "Shape":
            continue
        sid = sh.get("ID", "")
        cells = _cells(sh)
        page.shapes[sid] = {
            "text": _shape_text(sh), "x": _num(cells.get("PinX", "0")), "y": _num(cells.get("PinY", "0")),
            "name": sh.get("NameU") or sh.get("Name") or "", "master": sh.get("Master", ""), "group": group,
            "begin_arrow": cells.get("BeginArrow"), "end_arrow": cells.get("EndArrow"), "type": sh.get("Type", ""),
        }
        inner = next((c for c in sh if local(c.tag) == "Shapes"), None)
        if inner is not None:
            _walk(inner, page, sid)


def _arrow(shape: Dict[str, object]) -> str:
    b, e = shape.get("begin_arrow"), shape.get("end_arrow")
    name = str(shape.get("name", "")).lower()
    default_end = "connector" in name and e is None and b is None    # connecteur dynamique : pointe finale par défaut
    has_b = b not in (None, "", "0")
    has_e = e not in (None, "", "0") or default_end
    if has_b and has_e:
        return "<->"
    if has_e:
        return "->"
    if has_b:
        return "<-"
    return "--"


def _page_graph(page: _Page) -> Tuple[Graph, List[str]]:
    connectors: Dict[str, Dict[str, str]] = {}
    for conn, end, target in page.connects:
        connectors.setdefault(conn, {})["begin" if end.startswith("Begin") else "end"] = target
    linked = {c for c, ends in connectors.items() if len(ends) == 2}
    g = Graph()
    used: set = set()
    for conn in linked:
        used.update(connectors[conn].values())
    for sid, sh in page.shapes.items():
        if sid in linked or sh["type"] == "Group":
            continue
        label = str(sh["text"])
        if label or sid in used:
            g.nodes[sid] = label or str(sh["name"])
    for conn in sorted(linked, key=lambda c: (-float(page.shapes.get(c, {}).get("y", 0)), c)):
        ends = connectors[conn]
        if ends["begin"] in g.nodes and ends["end"] in g.nodes:
            g.edges.append((ends["begin"], ends["end"], str(page.shapes.get(conn, {}).get("text", "")), _arrow(page.shapes.get(conn, {}))))
    connected = {x for e in g.edges for x in e[:2]}
    rest = [str(sh["text"]) for sid, sh in sorted(page.shapes.items(), key=lambda kv: (-float(kv[1]["y"]), float(kv[1]["x"])))
            if sh["text"] and sid not in connected and sid not in linked]
    return g, rest


@engine("vsdx", name="native", prio=10)
def vsdx_native(path, ctx: Ctx) -> Result:
    with SafeZip(path) as zf:
        pages_xml = zf.xml("visio/pages/pages.xml")
        if pages_xml is None:
            raise Unsupported("visio/pages/pages.xml introuvable")
        rels = Rels(zf, "visio/pages/pages.xml")
        sections: List[str] = []
        src: List[str] = []
        n_pages = 0
        for page_el in pages_xml:
            if local(page_el.tag) != "Page" or page_el.get("Background") in ("1", "true"):
                continue
            rel = next((c for c in page_el if local(c.tag) == "Rel"), None)
            part = rels.target(rel.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")) if rel is not None else None
            if not part or not zf.has(part):
                continue
            root = zf.xml(part)
            if root is None:
                continue
            n_pages += 1
            page = _Page(page_el.get("Name") or page_el.get("NameU") or "")
            shapes = next((c for c in root if local(c.tag) == "Shapes"), None)
            if shapes is not None:
                _walk(shapes, page)
            connects = next((c for c in root if local(c.tag) == "Connects"), None)
            for c in (connects if connects is not None else []):
                if local(c.tag) == "Connect":
                    page.connects.append((c.get("FromSheet", ""), c.get("FromCell", ""), c.get("ToSheet", "")))
            g, rest = _page_graph(page)
            head = f"## Page {n_pages}" + (f" — {esc_inline(page.name)}" if page.name else "")
            body: List[str] = []
            if g.is_meaningful():
                body.append(to_mermaid(g))
                src.extend(g.texts())
            if rest:
                body.append(("**Textes :**\n\n" if g.is_meaningful() else "") + "\n".join(f"- {esc_inline(t)}" for t in rest))
                src.extend(rest)
            if not body:
                if page.shapes:
                    ctx.need_vision("page", str(path), f"page Visio {n_pages} sans texte : à décrire depuis un export image/PDF")
                    body.append("> **[À COMPLÉTER : description visuelle]** page sans texte extractible.")
                else:
                    body.append("_(page vide)_")
            sections.append("\n\n".join([head] + body))
        if not sections:
            raise Unsupported("aucune page lisible")
        props = core_props(zf)
        md = "\n\n".join(sections)
        title = props.get("title", "")
        if title:
            md = f"# {esc_inline(title)}\n\n{md}"
        res = Result(markdown=md, fmt="vsdx", engine="native", title=title, meta=props)
        res.units, res.unit_name, res.units_found = n_pages, "page", len(re.findall(r"(?m)^## Page \d+", md))
        res.source_text = " ".join(src)
        res.stats["partial_source"] = True
        return res

