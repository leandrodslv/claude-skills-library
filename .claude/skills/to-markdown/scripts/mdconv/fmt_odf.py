"""OpenDocument (ODT, ODP, ODS, ODG) → Markdown, en bibliothèque standard."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .grid import grid_blocks
from .inline import Fmt, Span, alt_clean, md_url, render_spans
from .util import SafeZip, clean_text, esc_inline, fence, local, md_table, parse_xml

N = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "dc": "http://purl.org/dc/elements/1.1/",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "math": "http://www.w3.org/1998/Math/MathML",
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
}


def q(ns: str, name: str) -> str:
    return "{%s}%s" % (N[ns], name)


_MONO = {"courier", "courier new", "consolas", "liberation mono", "dejavu sans mono", "monospace", "menlo",
         "monaco", "source code pro", "lucida console", "andale mono", "noto mono"}
_CODE_STYLE = re.compile(r"(?i)^(preformatted|source[_ ]20[_ ]text|source_text|code|verbatim|programlisting|listing)")
_QUOTE_STYLE = re.compile(r"(?i)^(quotations?|block[_ ]quote|citation)")


def _length_pt(v: Optional[str]) -> float:
    if not v:
        return 0.0
    m = re.match(r"(-?\d*\.?\d+)\s*(cm|mm|in|pt|pc|px)?", v)
    if not m:
        return 0.0
    n, unit = float(m.group(1)), m.group(2) or "pt"
    return n * {"cm": 28.3465, "mm": 2.83465, "in": 72.0, "pt": 1.0, "pc": 12.0, "px": 0.75}[unit]


class OdfConverter:
    def __init__(self, zf: SafeZip, ctx: Ctx, kind: str):
        self.zf, self.ctx, self.opts, self.kind = zf, ctx, ctx.opts, kind
        self.styles: Dict[str, Dict[str, object]] = {}
        self.list_styles: Dict[str, Dict[int, str]] = {}
        self.footnotes: List[str] = []
        self.comments: List[str] = []
        self.src: List[str] = []
        self.images_seen = 0

    # -- styles -----------------------------------------------------------
    def load_styles(self, *roots: Optional[ET.Element]) -> None:
        for root in roots:
            if root is None:
                continue
            for st in root.iter(q("style", "style")):
                name = st.get(q("style", "name"), "")
                d: Dict[str, object] = {"parent": st.get(q("style", "parent-style-name"), ""), "family": st.get(q("style", "family"), "")}
                tp = st.find(q("style", "text-properties"))
                if tp is not None:
                    fw = tp.get(q("fo", "font-weight"), "")
                    d["bold"] = fw == "bold" or (fw.isdigit() and int(fw) >= 600)
                    d["italic"] = tp.get(q("fo", "font-style"), "") in ("italic", "oblique")
                    ls = tp.get(q("style", "text-line-through-style"), "none")
                    d["strike"] = ls not in ("none", "")
                    fam = (tp.get(q("style", "font-name"), "") or tp.get(q("fo", "font-family"), "")).strip("'\" ").lower()
                    d["mono"] = fam in _MONO
                    pos = tp.get(q("style", "text-position"), "")
                    if pos.startswith("super"):
                        d["sup"] = True
                    elif pos.startswith("sub"):
                        d["sub"] = True
                self.styles[name] = d
            for ls in root.iter(q("text", "list-style")):
                name = ls.get(q("style", "name"), "")
                levels: Dict[int, str] = {}
                for lv in ls:
                    n = lv.get(q("text", "level"), "1")
                    if local(lv.tag) == "list-level-style-number":
                        levels[int(n)] = "ord"
                    elif local(lv.tag) in ("list-level-style-bullet", "list-level-style-image"):
                        levels[int(n)] = "bullet"
                self.list_styles[name] = levels

    def sprop(self, name: str, key: str) -> object:
        seen = set()
        while name and name in self.styles and name not in seen:
            seen.add(name)
            d = self.styles[name]
            if key in d:
                return d[key]
            name = str(d.get("parent", ""))
        return None

    def style_chain_matches(self, name: str, rx: "re.Pattern[str]") -> bool:
        seen = set()
        while name and name not in seen:
            seen.add(name)
            if rx.match(name):
                return True
            name = str(self.styles.get(name, {}).get("parent", ""))
        return False

    # -- inline -------------------------------------------------------------
    def spans(self, el: ET.Element, f: Fmt, out: List[Span]) -> None:
        if el.text:
            self._text(el.text, f, out)
        for c in el:
            n = local(c.tag)
            if n == "span":
                sn = c.get(q("text", "style-name"), "")
                f2 = f.copy(bold=f.bold or bool(self.sprop(sn, "bold")), italic=f.italic or bool(self.sprop(sn, "italic")),
                            strike=f.strike or bool(self.sprop(sn, "strike")), code=f.code or bool(self.sprop(sn, "mono")),
                            sup=bool(self.sprop(sn, "sup")) or f.sup, sub=bool(self.sprop(sn, "sub")) or f.sub)
                self.spans(c, f2, out)
            elif n == "a":
                href = c.get(q("xlink", "href"), "")
                self.spans(c, f.copy(link=href) if href and not href.startswith("#") else f, out)
            elif n == "s":
                out.append(Span("t", " " * int(c.get(q("text", "c"), "1") or 1), f.copy()))
            elif n == "tab":
                out.append(Span("t", " ", f.copy()))
            elif n == "line-break":
                out.append(Span("br"))
            elif n == "note":
                out.append(Span("raw", self.note(c)))
            elif n == "annotation":
                out.append(Span("raw", self.annotation(c)))
            elif n == "frame":
                out.append(Span("raw", self.frame(c)))
            elif n in ("soft-page-break", "bookmark", "bookmark-start", "bookmark-end", "reference-mark", "tracked-changes",
                       "change", "change-start", "change-end", "page-number", "sequence-decls"):
                pass
            elif n in ("custom-shape", "g", "rect", "line", "path", "polygon"):
                self.spans(c, f, out)
            else:
                self.spans(c, f, out)
            if c.tail:
                self._text(c.tail, f, out)

    @staticmethod
    def _text(t: str, f: Fmt, out: List[Span]) -> None:
        t = re.sub(r"[ \t\r\n]+", " ", t)
        if t:
            out.append(Span("t", t, f.copy()))

    def inline_md(self, el: ET.Element, inline_only: bool = False) -> str:
        out: List[Span] = []
        self.spans(el, Fmt(), out)
        self.src.append("".join(s.text for s in out if s.kind == "t"))
        return render_spans(out, inline_only=inline_only, escape_start=True)

    def note(self, n: ET.Element) -> str:
        body = n.find(q("text", "note-body"))
        text = " ".join(self.inline_md(p, True) for p in (body if body is not None else []) if local(p.tag) in ("p", "list", "h"))
        if not self.opts.notes:
            return ""
        self.footnotes.append(text.strip())
        return f"[^{len(self.footnotes)}]"

    def annotation(self, a: ET.Element) -> str:
        if not self.opts.comments:
            return ""
        who = (a.findtext(q("dc", "creator")) or "").strip()
        when = (a.findtext(q("dc", "date")) or "")[:10]
        text = " ".join(self.inline_md(p, True) for p in a if local(p.tag) == "p")
        self.comments.append(f"**{esc_inline(who)}**" + (f" ({when})" if when else "") + f" : {text}" if who else text)
        return f"[^c{len(self.comments)}]"

    def frame(self, fr: ET.Element) -> str:
        tbl = fr.find(q("table", "table"))
        if tbl is not None:
            return "\n\n".join(self.table(tbl))
        alt = ""
        for tag in ("title", "desc"):
            t = fr.find(q("svg", tag))
            if t is not None and (t.text or "").strip():
                alt = t.text.strip()
                break
        obj = fr.find(q("draw", "object"))
        if obj is not None:
            md = self.embedded_object(obj.get(q("xlink", "href"), ""))
            if md:
                return md
        img = fr.find(q("draw", "image"))
        if img is not None:
            href = img.get(q("xlink", "href"), "")
            if href.startswith(("http:", "https:")):
                return f"![{alt_clean(alt)}]({md_url(href)})"
            if href.lstrip("./").startswith("ObjectReplacements/") or href.lower().endswith((".svm", ".emf", ".wmf")):
                return ""
            data = self.zf.read_opt(href.lstrip("./")) if href else None
            if data:
                ext = href.rsplit(".", 1)[-1] if "." in href else ""
                link = self.ctx.add_asset(data, ext, stem="img", alt=alt)
                if alt:
                    self.src.append(alt)
                if link:
                    return f"![{alt_clean(alt)}]({link})"
                return f"*[image : {alt_clean(alt)}]*" if alt else ""
            return ""
        tb = fr.find(q("draw", "text-box"))
        if tb is not None:
            inner = "\n\n".join(self.blocks(tb))
            return "\n" + "\n".join(("> " + ln) if ln.strip() else ">" for ln in inner.split("\n")) + "\n" if inner.strip() else ""
        return ""

    def embedded_object(self, href: str) -> str:
        """Graphique (données du tableau local) ou formule (StarMath) embarqués."""
        base = href.lstrip("./").rstrip("/")
        data = self.zf.read_opt(base + "/content.xml") if base else None
        if not data:
            return ""
        try:
            root = parse_xml(data)
        except Exception:
            return ""
        ann = next((a for a in root.iter() if local(a.tag) == "annotation"), None)
        if ann is not None and (ann.text or "").strip():
            return f"`{ann.text.strip()}`"
        chart = next((c for c in root.iter(q("chart", "chart"))), None)
        if chart is None:
            return ""
        kinds = {"bar": "histogramme/barres", "line": "courbes", "circle": "secteurs", "area": "aires", "scatter": "nuage de points",
                 "ring": "anneau", "radar": "radar", "stock": "cours de bourse", "bubble": "bulles", "gantt": "Gantt"}
        kind = kinds.get(chart.get(q("chart", "class"), "").split(":")[-1], "graphique")
        title_el = chart.find(q("chart", "title"))
        title = " ".join(t for t in ("".join(p.itertext()).strip() for p in title_el.iter(q("text", "p"))) if t) if title_el is not None else ""
        tbl = next((t for t in chart.iter(q("table", "table"))), None)
        head = f"**Graphique ({kind})" + (f" — {esc_inline(title)}" if title else "") + "**"
        if title:
            self.src.append(title)
        if tbl is None:
            return head + "\n\n_(données du graphique non embarquées)_"
        rows = self.table(tbl)
        for cell in re.findall(r"\|\s*([^|]+?)\s*(?=\|)", "\n".join(rows)):
            self.src.append(cell)
        return head + "\n\n" + "\n\n".join(rows)

    # -- blocs ----------------------------------------------------------------
    def blocks(self, parent: ET.Element) -> List[str]:
        out: List[str] = []
        code_buf: List[str] = []

        def flush_code() -> None:
            if code_buf:
                out.append(fence("\n".join(code_buf)))
                code_buf.clear()

        last_list = False
        for el in parent:
            n = local(el.tag)
            if n != "list":
                last_list = False
            if n == "p":
                sn = el.get(q("text", "style-name"), "")
                if self.style_chain_matches(sn, _CODE_STYLE) or (self.sprop(sn, "mono") and el.find(q("text", "span")) is None):
                    code_buf.append("".join(el.itertext()))
                    continue
                flush_code()
                text = self.inline_md(el)
                if not text.strip():
                    continue
                if self.style_chain_matches(sn, _QUOTE_STYLE):
                    text = "\n".join("> " + ln for ln in text.split("\n"))
                out.append(text)
            elif n == "h":
                flush_code()
                text = re.sub(r"\s+", " ", self.inline_md(el, True)).strip()
                if text:
                    lvl = int(el.get(q("text", "outline-level"), "1") or 1)
                    out.append("#" * max(1, min(lvl, 6)) + " " + text)
            elif n == "list":
                flush_code()
                md = self.list_md(el, 0)
                if md.strip():
                    if last_list and out:  # LibreOffice scinde une même liste en plusieurs <text:list> voisins
                        out[-1] += "\n" + md
                    else:
                        out.append(md)
                    last_list = True
                continue
            elif n == "table":
                flush_code()
                out.extend(self.table(el))
            elif n in ("section", "index-body", "table-of-content", "illustration-index", "alphabetical-index",
                       "bibliography", "user-index"):
                flush_code()
                if n in ("table-of-content", "illustration-index", "alphabetical-index") and not self.opts.keep_toc:
                    continue
                out.extend(self.blocks(el))
            elif n in ("tracked-changes", "sequence-decls", "variable-decls", "user-field-decls", "forms"):
                continue
            elif n in ("frame", "custom-shape", "g"):
                flush_code()
                md = self.frame(el) if n == "frame" else ""
                if md.strip():
                    out.append(md.strip())
            elif len(el):
                flush_code()
                out.extend(self.blocks(el))
        flush_code()
        return out

    def list_md(self, lst: ET.Element, depth: int, style: str = "") -> str:
        style = lst.get(q("text", "style-name"), style)
        kind = self.list_styles.get(style, {}).get(depth + 1, "bullet")
        lines: List[str] = []
        idx = 1
        for item in lst:
            if local(item.tag) not in ("list-item", "list-header"):
                continue
            head: List[str] = []
            nested: List[str] = []
            for k in item:
                kn = local(k.tag)
                if kn in ("p", "h"):
                    t = re.sub(r"\s+", " ", self.inline_md(k, True)).strip()
                    if t:
                        head.append(t)
                elif kn == "list":
                    nested.append(self.list_md(k, depth + 1, style))
                elif kn == "table":
                    head.extend(re.sub(r"\s+", " ", x) for x in self.table(k))
            if not head and nested:  # LibreOffice imbrique via un élément « vide » : la sous-liste suit l'élément précédent
                for nl in nested:
                    lines.append("\n".join("  " + ln for ln in nl.split("\n")))
                continue
            marker = f"{idx}." if kind == "ord" else "-"
            idx += 1
            pad = " " * (len(marker) + 1)
            lines.append(f"{marker} {' '.join(head)}".rstrip())
            for nl in nested:
                lines.append("\n".join(pad + ln for ln in nl.split("\n")))
        return "\n".join(lines)

    def table(self, tbl: ET.Element) -> List[str]:
        grid: List[List[str]] = []
        vfill: Dict[int, str] = {}
        for row in tbl.iter(q("table", "table-row")):
            cells: List[str] = []
            col = 0
            for c in row:
                cn = local(c.tag)
                if cn not in ("table-cell", "covered-table-cell"):
                    continue
                rep = int(c.get(q("table", "number-columns-repeated"), "1") or 1)
                if cn == "covered-table-cell":
                    for _ in range(min(rep, 50)):
                        cells.append(vfill.get(col, ""))
                        col += 1
                    continue
                text = "<br>".join(t for t in (self.inline_md(p, True) for p in c if local(p.tag) in ("p", "h")) if t.strip())
                span = int(c.get(q("table", "number-columns-spanned"), "1") or 1)
                rs = int(c.get(q("table", "number-rows-spanned"), "1") or 1)
                for k in range(min(rep, 50)):
                    cells.append(text)
                    if rs > 1:
                        vfill[col] = text
                    else:
                        vfill.pop(col, None)
                    for _ in range(span - 1):
                        cells.append("")
                    col += span
            if any(x.strip() for x in cells):
                grid.append(cells)
        if not grid:
            return []
        cap = self.opts.table_rows
        if cap and len(grid) - 1 > cap:
            extra = len(grid) - 1 - cap
            width = max(len(r) for r in grid)
            grid = grid[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (width - 1)]
        return [md_table(grid)]

    # -- sortie ------------------------------------------------------------------
    def tail(self) -> str:
        lines = [f"[^{i}]: {t}" for i, t in enumerate(self.footnotes, 1)]
        lines += [f"[^c{i}]: {t}" for i, t in enumerate(self.comments, 1)]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# ODT
# --------------------------------------------------------------------------

def _load(zf: SafeZip, ctx: Ctx):
    content = zf.xml("content.xml")
    if content is None:
        raise Unsupported("content.xml illisible")
    meta = zf.xml("meta.xml")
    props: Dict[str, str] = {}
    if meta is not None:
        for el in meta.iter():
            n = local(el.tag)
            if n == "title" and (el.text or "").strip():
                props["title"] = clean_text(el.text.strip())
            elif n == "creator" and (el.text or "").strip():
                props["author"] = clean_text(el.text.strip())
            elif n == "creation-date" and el.text:
                props["created"] = el.text[:10]
            elif n == "language" and el.text:
                props["language"] = el.text.strip()
    return content, zf.xml("styles.xml"), props


def _flat(path) -> Optional[ET.Element]:
    """ODF « à plat » (.fodt/.fods/.fodp) : un seul fichier XML."""
    try:
        root = parse_xml(open(path, "rb").read())
    except Exception:
        return None
    return root if local(root.tag) == "document" else None


class _FlatZip:
    """Façade minimale de SafeZip pour un ODF à plat (aucun média externe)."""

    def read_opt(self, name: str):
        return None

    def xml(self, name: str):
        return None

    def has(self, name: str) -> bool:
        return False


@engine("odt", name="native", prio=10)
def odt_native(path, ctx: Ctx) -> Result:
    zf, flat = _open(path)
    with _ctxmgr(zf):
        content, styles, props = _content(zf, flat, path)
        conv = OdfConverter(zf, ctx, "odt")
        conv.load_styles(content.find(q("office", "automatic-styles")), styles, content)
        body = content.find(q("office", "body"))
        text = body.find(q("office", "text")) if body is not None else None
        if text is None:
            raise Unsupported("pas de corps texte")
        blocks = conv.blocks(text)
        md = "\n\n".join(b for b in blocks if b.strip())
        tail = conv.tail()
        if tail:
            md += "\n\n" + tail
        res = Result(markdown=md, fmt="odt", engine="native", title=props.get("title", ""), meta=props)
        res.source_text = " ".join(conv.src)
        res.stats["partial_source"] = True
        return res


@engine("odp", name="native", prio=10)
def odp_native(path, ctx: Ctx) -> Result:
    zf, flat = _open(path)
    with _ctxmgr(zf):
        content, styles, props = _content(zf, flat, path)
        conv = OdfConverter(zf, ctx, "odp")
        conv.load_styles(content.find(q("office", "automatic-styles")), styles, content)
        pres = content.find(q("office", "body") + "/" + q("office", "presentation"))
        if pres is None:
            raise Unsupported("pas de présentation")
        parts: List[str] = []
        n = 0
        for page in pres.findall(q("draw", "page")):
            n += 1
            parts.append(_odp_slide(conv, page, n))
        title = props.get("title", "")
        md = "\n\n".join(parts)
        if title:
            md = f"# {esc_inline(title)}\n\n{md}"
        tail = conv.tail()
        if tail:
            md += "\n\n" + tail
        res = Result(markdown=md, fmt="odp", engine="native", title=title, meta=props)
        res.units, res.unit_name, res.units_found = n, "slide", len(re.findall(r"(?m)^## Slide \d+", md))
        res.source_text = " ".join(conv.src)
        res.stats["partial_source"] = True
        return res


def _odp_slide(conv: OdfConverter, page: ET.Element, num: int) -> str:
    title = ""
    items: List[Tuple[float, float, str]] = []
    notes: List[str] = []
    ids: Dict[str, str] = {}
    edges: List[Tuple[str, str]] = []

    def walk(container: ET.Element) -> None:
        nonlocal title
        for fr in container:
            n = local(fr.tag)
            if n in ("frame", "custom-shape", "rect", "ellipse", "caption"):
                cls = fr.get(q("presentation", "class"), "")
                y = _length_pt(fr.get(q("svg", "y")))
                x = _length_pt(fr.get(q("svg", "x")))
                sid = fr.get(q("draw", "id"), "")
                tb = fr.find(q("draw", "text-box"))
                target = tb if tb is not None else (fr if n != "frame" else None)
                md = ""
                if target is not None:
                    blocks = conv.blocks(target)
                    md = "\n\n".join(blocks)
                    if sid and md:
                        ids[sid] = re.sub(r"\s+", " ", " ".join(re.sub(r"^[-\d.]+\s+", "", b) for b in blocks)).strip()
                if n == "frame" and not md:
                    md = conv.frame(fr)
                if cls == "title" and md.strip() and not title:
                    title = re.sub(r"\s+", " ", re.sub(r"^#+\s*", "", md.replace("\\\n", " "))).strip()
                elif cls == "notes":
                    if md.strip():
                        notes.append(md)
                elif cls in ("page-number", "footer", "date-time", "header", "handout"):
                    pass
                elif md.strip():
                    items.append((round(y / 30), x, md))
            elif n == "g":
                walk(fr)
            elif n == "connector":
                s, e = fr.get(q("draw", "start-shape")), fr.get(q("draw", "end-shape"))
                if s and e:
                    edges.append((s, e))
            elif n == "notes" and local(fr.tag) == "notes":
                walk(fr)

    walk(page)
    nt = page.find(q("presentation", "notes"))
    if nt is not None and conv.opts.notes:
        walk(nt)
    head = f"## Slide {num}" + (f" — {esc_inline(title)}" if title else "")
    parts = [head] + [md for _y, _x, md in sorted(items, key=lambda t: (t[0], t[1]))]
    linked = [(a, b) for a, b in edges if a in ids and b in ids]
    if len(linked) >= 2:
        idx: Dict[str, str] = {}

        def node(i: str) -> str:
            idx.setdefault(i, f"N{len(idx) + 1}")
            return f'{idx[i]}["{ids[i][:80].replace(chr(34), chr(39))}"]'

        parts.append("**Diagramme (connecteurs) :**\n\n```mermaid\nflowchart LR\n" + "\n".join(f"    {node(a)} --> {node(b)}" for a, b in linked) + "\n```")
    if notes and conv.opts.notes:
        parts.append("**Notes du présentateur :**\n\n" + "\n".join(("> " + ln) if ln.strip() else ">" for ln in "\n\n".join(notes).split("\n")))
    return "\n\n".join(p for p in parts if p.strip())


# --------------------------------------------------------------------------
# ODS
# --------------------------------------------------------------------------

@engine("ods", name="native", prio=10)
def ods_native(path, ctx: Ctx) -> Result:
    zf, flat = _open(path)
    with _ctxmgr(zf):
        content, styles, props = _content(zf, flat, path)
        conv = OdfConverter(zf, ctx, "ods")
        conv.load_styles(content.find(q("office", "automatic-styles")), styles, content)
        sheet_root = content.find(q("office", "body") + "/" + q("office", "spreadsheet"))
        if sheet_root is None:
            raise Unsupported("pas de tableur")
        parts: List[str] = []
        sheets = sheet_root.findall(q("table", "table"))
        strings: List[str] = []
        truncated = False
        for tbl in sheets:
            name = tbl.get(q("table", "name"), "Feuille")
            rows: Dict[int, Dict[int, str]] = {}
            r_idx = 0
            total = 0
            for row in tbl.iter(q("table", "table-row")):
                rep = int(row.get(q("table", "number-rows-repeated"), "1") or 1)
                cells: Dict[int, str] = {}
                col = 0
                for c in row:
                    cn = local(c.tag)
                    if cn not in ("table-cell", "covered-table-cell"):
                        continue
                    crep = int(c.get(q("table", "number-columns-repeated"), "1") or 1)
                    text = _ods_cell(c, conv, ctx.opts.formulas) if cn == "table-cell" else ""
                    if text:
                        strings.append(text)
                        for k in range(min(crep, 200)):
                            cells[col + k + 1] = text
                    col += crep
                if cells:
                    for k in range(min(rep, 1000)):
                        rows[r_idx + k + 1] = dict(cells)
                    total += min(rep, 1000)
                r_idx += rep
            head = f"## {esc_inline(name)}"
            if not rows:
                parts.append(f"{head}\n\n_(feuille vide)_")
            else:
                blocks = grid_blocks(ctx, rows, name, "", total)
                truncated = truncated or any(b.startswith("_Tableau tronqué") for b in blocks)
                parts.append("\n\n".join([head] + blocks))
        md = "\n\n".join(parts)
        res = Result(markdown=md, fmt="ods", engine="native", title=props.get("title", ""), meta=props)
        res.units, res.unit_name, res.units_found = len(sheets), "feuille", len(re.findall(r"(?m)^## ", md))
        res.source_text = None if truncated else "\n".join(s for s in strings if not re.fullmatch(r"[-\d.,:%\s TRUEFALS]+", s))
        res.stats["partial_source"] = True
        return res


def _ods_cell(c: ET.Element, conv: OdfConverter, formulas: bool) -> str:
    vt = c.get(q("office", "value-type"), "")
    text = "<br>".join(t for t in (conv.inline_md(p, True) for p in c if local(p.tag) == "p") if t.strip())
    if vt in ("float", "currency"):
        v = c.get(q("office", "value"), "")
        try:
            f = float(v)
            out = str(int(f)) if f == int(f) and abs(f) < 1e15 else format(f, ".15g")
        except ValueError:
            out = text
    elif vt == "percentage":
        v = c.get(q("office", "value"), "")
        try:
            out = f"{float(v) * 100:.4g}%"
        except ValueError:
            out = text
    elif vt == "date":
        out = (c.get(q("office", "date-value"), "") or text).replace("T00:00:00", "").replace("T", " ")
    elif vt == "time":
        v = c.get(q("office", "time-value"), "")
        m = re.match(r"PT(\d+)H(\d+)M(\d+)", v)
        out = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}:{int(m.group(3)):02d}" if m else text
    elif vt == "boolean":
        out = "TRUE" if c.get(q("office", "boolean-value")) == "true" else "FALSE"
    else:
        out = text
    if formulas and c.get(q("table", "formula")):
        out = f"{out} ({c.get(q('table', 'formula'))})"
    return out


# --------------------------------------------------------------------------
# Ouverture commune
# --------------------------------------------------------------------------

def _open(path):
    flat = _flat(path) if str(path).lower().endswith(("fodt", "fods", "fodp")) else None
    if flat is not None:
        return _FlatZip(), flat
    return SafeZip(path), None


class _ctxmgr:
    def __init__(self, zf):
        self.zf = zf

    def __enter__(self):
        return self.zf

    def __exit__(self, *exc):
        if hasattr(self.zf, "close"):
            self.zf.close()


def _content(zf, flat, path):
    if flat is not None:
        props: Dict[str, str] = {}
        meta = flat.find(q("office", "meta"))
        if meta is not None:
            t = meta.find(q("dc", "title"))
            if t is not None and (t.text or "").strip():
                props["title"] = t.text.strip()
        return flat, flat.find(q("office", "styles")), props
    return _load(zf, None)
