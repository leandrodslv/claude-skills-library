"""Diagrammes : reconstruit un graphe (nœuds, liens, groupes) depuis draw.io, Graphviz, Mermaid, Excalidraw.

Le graphe est rendu en bloc Mermaid — la représentation la plus compacte et la
plus lisible par une IA d'un schéma d'architecture ou d'un logigramme.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .util import decode_text, esc_inline, html_to_text, local, parse_xml, clean_text

MAX_INFLATE = 64 << 20


@dataclass
class Graph:
    nodes: Dict[str, str] = field(default_factory=dict)                 # id → libellé
    edges: List[Tuple[str, str, str, str]] = field(default_factory=list)  # (source, cible, libellé, flèche)
    groups: Dict[str, Tuple[str, List[str]]] = field(default_factory=dict)  # id → (libellé, membres)
    shapes: Dict[str, str] = field(default_factory=dict)                 # id → aspect : round | stadium | circle | diamond | cyl (défaut : rectangle)
    free_text: List[str] = field(default_factory=list)                   # textes non reliés à un nœud
    direction: str = "TD"

    def is_meaningful(self) -> bool:
        return len(self.nodes) >= 2 and (len(self.edges) >= 1 or len(self.groups) >= 1)

    def texts(self) -> List[str]:
        out = [t for t in self.nodes.values() if t]
        out += [e[2] for e in self.edges if e[2]]
        out += [g[0] for g in self.groups.values() if g[0]]
        out += self.free_text
        return out


def _q(label: str) -> str:
    label = re.sub(r"\s+", " ", label.replace("\n", " ")).strip()
    label = label.replace('"', "'")
    return label if len(label) <= 120 else label[:117] + "…"


_SHAPE_FMT = {"round": '("{}")', "stadium": '(["{}"])', "circle": '(("{}"))', "diamond": '{{"{}"}}', "cyl": '[("{}")]'}


def _node(g: Graph, nid: str, nid_out: str, label: str) -> str:
    fmt = _SHAPE_FMT.get(g.shapes.get(nid, ""), '["{}"]')
    return f"{nid_out}{fmt.format(label)}"


def to_mermaid(g: Graph) -> str:
    """Bloc ```mermaid``` d'un graphe (identifiants n1…nk, libellés entre guillemets)."""
    ids = {nid: f"n{i}" for i, nid in enumerate(g.nodes, 1)}
    # les extrémités de liens sans nœud déclaré deviennent des nœuds anonymes
    for s, t, _l, _a in g.edges:
        for x in (s, t):
            if x not in ids and x not in g.groups:
                ids[x] = f"n{len(ids) + 1}"
    lines = [f"flowchart {g.direction}"]
    in_group = {m for _l, members in g.groups.values() for m in members}
    for nid, label in g.nodes.items():
        if nid not in in_group:
            lines.append("    " + _node(g, nid, ids[nid], _q(label) or nid))
    for gi, (gid, (label, members)) in enumerate(g.groups.items(), 1):
        members = [m for m in members if m in ids]
        if not members:
            continue
        lines.append(f'    subgraph g{gi}["{_q(label) or gid}"]')
        for m in members:
            lines.append("        " + _node(g, m, ids[m], _q(g.nodes.get(m, m))))
        lines.append("    end")
    gids = {gid: f"g{gi}" for gi, gid in enumerate(g.groups, 1)}
    for s, t, label, arrow in g.edges:
        s_id, t_id = ids.get(s) or gids.get(s), ids.get(t) or gids.get(t)
        if s_id is None or t_id is None:
            continue
        a = {"->": "-->", "<-": "<--", "<->": "<-->", "--": "---"}.get(arrow, "-->")
        if label:
            a = {"-->": "-->|{}|", "<--": "<--|{}|", "<-->": "<-->|{}|", "---": "---|{}|"}[a].format(_q(label))
        lines.append(f"    {s_id} {a} {t_id}")
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def _cell(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("|", "\\|")).strip()


def to_text(g: Graph) -> str:
    """Le même schéma en Markdown pur (tableau des liens, groupes, éléments isolés) : lisible sans moteur Mermaid."""
    names = dict(g.nodes)
    names.update({gid: label for gid, (label, _m) in g.groups.items()})
    for s, t, _l, _a in g.edges:
        names.setdefault(s, s)
        names.setdefault(t, t)
    parts: List[str] = []
    if g.edges:
        sym = {"->": "→", "<-": "←", "<->": "↔", "--": "—"}
        rows = ["| De | | Vers | Étiquette |", "| --- | :---: | --- | --- |"]
        for s, t, lab, arrow in g.edges:
            rows.append(f"| {_cell(names.get(s, s))} | {sym.get(arrow, '→')} | {_cell(names.get(t, t))} | {_cell(lab)} |")
        parts.append("**Liens du schéma :**\n\n" + "\n".join(rows))
    if g.groups:
        lines = []
        for _gid, (label, members) in g.groups.items():
            lines.append(f"- **{_cell(label)}** : " + ", ".join(_cell(names.get(m, m)) for m in members))
        parts.append("**Groupes (cadres, couloirs) :**\n\n" + "\n".join(lines))
    decisions = [_cell(v) for k, v in g.nodes.items() if g.shapes.get(k) == "diamond" and v]
    if decisions:
        parts.append("**Décisions (losanges) :** " + ", ".join(decisions))
    linked = {x for e in g.edges for x in e[:2]} | {m for _l, ms in g.groups.values() for m in ms}
    alone = [_cell(v) for k, v in g.nodes.items() if k not in linked and v]
    if alone:
        parts.append("**Éléments sans lien :** " + ", ".join(alone))
    return "\n\n".join(parts)


def render_graph(g: Graph, mode: str = "both") -> str:
    """mode : « mermaid », « text » (Markdown pur) ou « both » (défaut : un bloc Mermaid puis la version texte)."""
    if mode == "mermaid":
        return to_mermaid(g)
    if mode == "text":
        return to_text(g)
    text = to_text(g)
    return to_mermaid(g) + ("\n\n" + text if text else "")


# --------------------------------------------------------------------------
# draw.io / diagrams.net
# --------------------------------------------------------------------------

def _inflate(data: bytes) -> bytes:
    d = zlib.decompressobj(-15)
    out = d.decompress(data, MAX_INFLATE)
    if d.unconsumed_tail:
        raise ValueError("diagramme trop volumineux une fois décompressé")
    return out


def decode_diagram_text(text: str) -> Optional[ET.Element]:
    """Contenu d'un <diagram> compressé (base64 + deflate brut + URL-encodage) → mxGraphModel."""
    try:
        xml = urllib.parse.unquote(_inflate(base64.b64decode(text.strip())).decode("utf-8"))
        return parse_xml(xml.encode("utf-8"))
    except Exception:
        return None


def _label(raw: Optional[str], style: str = "") -> str:
    if not raw:
        return ""
    if "html=1" in style or re.search(r"<[a-zA-Z/][^>]*>", raw):
        return clean_text(html_to_text(raw)).strip()
    return clean_text(raw).strip()


def _arrow(style: str) -> str:
    st = dict(kv.split("=", 1) for kv in style.split(";") if "=" in kv)
    end, start = st.get("endArrow", "classic"), st.get("startArrow", "none")
    if end != "none" and start != "none":
        return "<->"
    if end != "none":
        return "->"
    if start != "none":
        return "<-"
    return "--"


def graph_from_mxmodel(model: ET.Element) -> Graph:
    g = Graph()
    cells: Dict[str, Dict[str, str]] = {}
    order: List[str] = []
    root = model.find("root") if local(model.tag) == "mxGraphModel" else model
    if root is None:
        return g
    for ch in root:
        tag = local(ch.tag)
        if tag == "mxCell":
            cell, label = ch, ch.get("value", "")
            cid = ch.get("id", "")
        elif tag in ("object", "UserObject", "Object"):
            cell = ch.find("mxCell")
            if cell is None:
                continue
            label, cid = ch.get("label", ch.get("value", "")), ch.get("id", "")
        else:
            continue
        cells[cid] = {"label": _label(label, cell.get("style", "")), "style": cell.get("style", ""),
                      "vertex": cell.get("vertex", ""), "edge": cell.get("edge", ""),
                      "parent": cell.get("parent", ""), "source": cell.get("source", ""),
                      "target": cell.get("target", "")}
        order.append(cid)
    edge_ids = {c for c, v in cells.items() if v["edge"] == "1"}
    parents = {v["parent"] for c, v in cells.items() if v["vertex"] == "1"}
    edge_label: Dict[str, str] = {}
    for cid in order:  # étiquettes posées sur un lien (sommets enfants d'un lien)
        v = cells[cid]
        if v["vertex"] == "1" and v["parent"] in edge_ids and v["label"]:
            edge_label[v["parent"]] = v["label"]
    endpoints = {x for c in edge_ids for x in (cells[c]["source"], cells[c]["target"]) if x}
    for cid in order:
        v = cells[cid]
        if v["vertex"] != "1" or v["parent"] in edge_ids:
            continue
        is_container = cid in parents and cid not in endpoints
        if is_container and (v["label"] or any(cells[o]["parent"] == cid and cells[o]["vertex"] == "1" for o in order)):
            members = [o for o in order if cells[o]["parent"] == cid and cells[o]["vertex"] == "1" and cells[o]["label"]]
            g.groups[cid] = (v["label"], members)
            continue
        if v["label"] or cid in endpoints:
            g.nodes[cid] = v["label"]
    for cid in edge_ids:
        v = cells[cid]
        s, t = v["source"], v["target"]
        if s in cells and t in cells:
            for x in (s, t):
                if x not in g.nodes and x not in g.groups:
                    g.nodes[x] = cells[x]["label"]
            label = v["label"] or edge_label.get(cid, "")
            g.edges.append((s, t, label, _arrow(v["style"])))
    # les groupes deviennent nœuds pour les liens qui les visent
    for gid, (label, _m) in g.groups.items():
        if any(gid in (e[0], e[1]) for e in g.edges) and gid not in g.nodes:
            g.nodes[gid] = label
    return g


def parse_mxfile(root: ET.Element) -> List[Tuple[str, Graph]]:
    pages: List[Tuple[str, Graph]] = []
    tag = local(root.tag)
    if tag == "mxfile":
        for d in root:
            if local(d.tag) != "diagram":
                continue
            model = d.find("mxGraphModel")
            if model is None and (d.text or "").strip():
                model = decode_diagram_text(d.text)
            if model is not None:
                pages.append((d.get("name", "Page"), graph_from_mxmodel(model)))
    elif tag == "mxGraphModel":
        pages.append(("", graph_from_mxmodel(root)))
    return pages


# --------------------------------------------------------------------------
# Excalidraw
# --------------------------------------------------------------------------

def graph_from_excalidraw(scene: dict) -> Graph:
    g = Graph()
    els = [e for e in scene.get("elements", []) if not e.get("isDeleted")]
    label_of: Dict[str, str] = {}
    for e in els:
        if e.get("type") == "text" and e.get("containerId"):
            label_of[e["containerId"]] = clean_text(e.get("text", "")).strip()
    shapes = {"rectangle", "ellipse", "diamond", "frame", "magicframe", "image", "embeddable"}
    endpoints = set()
    for e in els:
        if e.get("type") in ("arrow", "line"):
            for k in ("startBinding", "endBinding"):
                b = e.get(k) or {}
                if b.get("elementId"):
                    endpoints.add(b["elementId"])
    for e in els:
        t, eid = e.get("type"), e.get("id", "")
        if t in shapes and (label_of.get(eid) or eid in endpoints):
            g.nodes[eid] = label_of.get(eid, "")
        elif t == "text" and not e.get("containerId"):
            txt = clean_text(e.get("text", "")).strip()
            if txt:
                if eid in endpoints:
                    g.nodes[eid] = txt
                else:
                    g.free_text.append(txt)
    for e in els:
        if e.get("type") not in ("arrow", "line"):
            continue
        s = (e.get("startBinding") or {}).get("elementId")
        d = (e.get("endBinding") or {}).get("elementId")
        if s and d and s in g.nodes and d in g.nodes:
            head_end = e.get("endArrowhead") not in (None, "")
            head_start = e.get("startArrowhead") not in (None, "")
            arrow = "<->" if head_end and head_start else ("->" if head_end else ("<-" if head_start else "--"))
            g.edges.append((s, d, label_of.get(e.get("id", ""), ""), arrow))
    return g


def excalidraw_from_svg_comments(root: ET.Element) -> Optional[dict]:
    """Charge utile Excalidraw embarquée dans un commentaire d'un SVG exporté."""
    blob = ""
    active = False
    for node in root.iter():
        if node.tag is ET.Comment:
            t = (node.text or "").strip()
            if t == "payload-start":
                active = True
            elif t == "payload-end":
                active = False
            elif active:
                blob += t
    if not blob:
        return None
    try:
        meta = json.loads(base64.b64decode(blob).decode("utf-8"))
        enc = meta.get("encoded", "")
        raw = enc.encode("latin-1") if meta.get("compressed", True) else enc.encode("utf-8")
        if meta.get("compressed", True):
            d = zlib.decompressobj()
            raw = d.decompress(raw, MAX_INFLATE)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


# --------------------------------------------------------------------------
# Graphviz (SVG produit par « dot »)
# --------------------------------------------------------------------------

def _texts_in(el: ET.Element) -> List[str]:
    out = []
    for t in el.iter("{http://www.w3.org/2000/svg}text"):
        s = "".join(t.itertext()).strip()
        if s:
            out.append(s)
    return out


def _shape_box(el: ET.Element):
    """Boîte englobante (x0, y0, x1, y1) de la première forme d'un groupe Graphviz."""
    svg = "{http://www.w3.org/2000/svg}"
    poly = el.find(svg + "polygon")
    if poly is None:
        poly = el.find(svg + "path")
    if poly is not None and poly.get("points"):
        pts = [tuple(float(v) for v in p.split(",")) for p in poly.get("points", "").split() if "," in p]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            return min(xs), min(ys), max(xs), max(ys)
    ell = el.find(svg + "ellipse")
    if ell is not None:
        cx, cy, rx, ry = (float(ell.get(k, 0)) for k in ("cx", "cy", "rx", "ry"))
        return cx - rx, cy - ry, cx + rx, cy + ry
    path = el.find(svg + "path")  # formes courbes (cylindre…) : boîte des coordonnées absolues de « d »
    if path is not None and path.get("d"):
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", path.get("d", ""))]
        if len(nums) >= 4:
            xs, ys = nums[0::2], nums[1::2]
            return min(xs), min(ys), max(xs), max(ys)
    return None


def graph_from_graphviz_svg(root: ET.Element) -> Optional[Graph]:
    svg = "{http://www.w3.org/2000/svg}"
    top = next((g for g in root.iter(svg + "g") if "graph" in (g.get("class", "").split())), None)
    if top is None:
        return None
    g = Graph()
    cluster_box: Dict[str, Tuple[float, float, float, float]] = {}
    node_box: Dict[str, Tuple[float, float, float, float]] = {}
    for el in top.iter(svg + "g"):
        cls = el.get("class", "").split()
        title = el.find(svg + "title")
        ttl = (title.text or "").strip() if title is not None else ""
        if "node" in cls:
            texts = _texts_in(el)
            g.nodes[ttl] = " ".join(texts) if texts else ttl
            box = _shape_box(el)
            if box:
                node_box[ttl] = box
        elif "cluster" in cls:
            texts = _texts_in(el)
            g.groups[ttl] = (" ".join(texts), [])
            box = _shape_box(el)
            if box:
                cluster_box[ttl] = box
        elif "edge" in cls and ttl:
            m = re.match(r"^(.*?)\s*(->|--|<-)\s*(.*)$", ttl)
            if m:
                s = re.sub(r":[\w.]+(:[nsew]{1,2})?$", "", m.group(1)) if ttl.count(":") and m.group(1) not in g.nodes else m.group(1)
                t = re.sub(r":[\w.]+(:[nsew]{1,2})?$", "", m.group(3)) if m.group(3) not in g.nodes else m.group(3)
                arrow = "->" if m.group(2) == "->" else ("<-" if m.group(2) == "<-" else "--")
                g.edges.append((s, t, " ".join(_texts_in(el)), arrow))
    # un nœud appartient au plus petit cluster qui contient son centre
    for nid, (x0, y0, x1, y1) in node_box.items():
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        best = None
        for cid, (a0, b0, a1, b1) in cluster_box.items():
            if a0 <= cx <= a1 and b0 <= cy <= b1:
                area = (a1 - a0) * (b1 - b0)
                if best is None or area < best[0]:
                    best = (area, cid)
        if best:
            g.groups[best[1]][1].append(nid)
    return g if g.nodes else None


# --------------------------------------------------------------------------
# Mermaid (SVG produit par mermaid-cli / mermaid.js) — diagrammes de flux
# --------------------------------------------------------------------------

def graph_from_mermaid_svg(root: ET.Element) -> Optional[Graph]:
    svg = "{http://www.w3.org/2000/svg}"
    nodes: Dict[str, str] = {}
    for el in root.iter(svg + "g"):
        cls = el.get("class", "").split()
        gid = el.get("id", "")
        if "node" in cls and gid.startswith("flowchart-"):
            m = re.match(r"^flowchart-(.+)-\d+$", gid)
            if not m:
                continue
            txt = " ".join(t for t in (_html_or_svg_text(el),) if t)
            nodes[m.group(1)] = txt or m.group(1)
    if len(nodes) < 2:
        return None
    labels: Dict[str, str] = {}
    for el in root.iter(svg + "g"):
        if "edgeLabel" in el.get("class", "").split():
            inner = el.find(".//" + svg + "g[@data-id]")
            key = inner.get("data-id") if inner is not None else ""
            txt = _html_or_svg_text(el)
            if key and txt:
                labels[key] = txt
    g = Graph(nodes=nodes)
    known = set(nodes)
    for p in root.iter(svg + "path"):
        pid = p.get("id", "")
        m = re.match(r"^L[-_](.+)[-_]\d+$", pid)
        if not m:
            continue
        body = m.group(1)
        cut = None
        for sep in ("_", "-"):
            for i in range(1, len(body) - 1):
                if body[i] == sep and body[:i] in known and body[i + 1:] in known:
                    cut = i
                    break
            if cut:
                break
        if cut is None:
            continue
        s, t = body[:cut], body[cut + 1:]
        me, ms = p.get("marker-end"), p.get("marker-start")
        arrow = "<->" if (me and ms) else ("->" if me else ("<-" if ms else "--"))
        g.edges.append((s, t, labels.get(pid, ""), arrow))
    return g


def _html_or_svg_text(el: ET.Element) -> str:
    fo = next((x for x in el.iter() if local(x.tag) == "foreignObject"), None)
    if fo is not None:
        raw = ET.tostring(fo, encoding="unicode")
        return clean_text(html_to_text(re.sub(r"^<[^>]*foreignObject[^>]*>|</[^>]*foreignObject>$", "", raw))).replace("\n", " ").strip()
    return " ".join(_texts_in(el))


# --------------------------------------------------------------------------
# Moteurs pour fichiers .drawio et .excalidraw
# --------------------------------------------------------------------------

def _graph_md(pages: List[Tuple[str, Graph]], mode: str = "both") -> str:
    out: List[str] = []
    for name, g in pages:
        if name and len(pages) > 1:
            out.append(f"## {esc_inline(name)}")
        if g.nodes or g.edges:
            out.append(render_graph(g, mode))
        free = [t for t in g.free_text if t]
        if free:
            out.append("**Textes libres :**\n\n" + "\n".join(f"- {esc_inline(t)}" for t in free))
    return "\n\n".join(out)


@engine("drawio", name="native", prio=10)
def drawio_native(path, ctx: Ctx) -> Result:
    root = parse_xml(Path(path).read_bytes())
    pages = parse_mxfile(root)
    if not pages:
        raise Unsupported("aucun diagramme lisible (fichier draw.io vide ou chiffré)")
    md = _graph_md(pages, ctx.opts.diagrams)
    stem = Path(path).stem
    src = "\n".join(t for _n, g in pages for t in g.texts())
    n_nodes = sum(len(g.nodes) for _n, g in pages)
    n_edges = sum(len(g.edges) for _n, g in pages)
    md = f"# {esc_inline(stem)}\n\n_Diagramme draw.io : {n_nodes} nœud(s), {n_edges} lien(s), {len(pages)} page(s)._\n\n{md}"
    res = Result(markdown=md, fmt="drawio", engine="native", title=stem)
    res.source_text = src
    return res


@engine("excalidraw", name="native", prio=10)
def excalidraw_native(path, ctx: Ctx) -> Result:
    try:
        scene = json.loads(decode_text(Path(path).read_bytes())[0])
    except ValueError as exc:
        raise Unsupported(f"JSON Excalidraw invalide : {exc}")
    g = graph_from_excalidraw(scene)
    stem = Path(path).stem
    md = f"# {esc_inline(stem)}\n\n_Diagramme Excalidraw : {len(g.nodes)} nœud(s), {len(g.edges)} lien(s)._\n\n{_graph_md([('', g)], ctx.opts.diagrams)}"
    res = Result(markdown=md, fmt="excalidraw", engine="native", title=stem)
    res.source_text = "\n".join(g.texts())
    return res
