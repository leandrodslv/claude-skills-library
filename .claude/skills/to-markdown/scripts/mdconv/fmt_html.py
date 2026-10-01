"""HTML → Markdown, en bibliothèque standard (analyseur tolérant + rendu structuré).

Sert aussi de brique aux e-books (EPUB), e-mails HTML, MHTML et aux faux « .xls/.doc »
qui ne sont que du HTML. Gère : titres, listes imbriquées, tableaux (fusions, tableaux de
mise en page aplatis), code, citations, liens, images (data-URI extraites), maths (KaTeX/MathJax),
suppression du bruit de page (menus, pieds de page, cookies) et sélection du contenu principal.
"""
from __future__ import annotations

import base64
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from .core import Ctx, Result, Unsupported, engine
from .inline import Fmt, Span, alt_clean, md_url, render_spans
from .util import clean_text, decode_text, esc_inline, fence, md_table

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCKS = {"address", "article", "aside", "blockquote", "body", "caption", "dd", "details", "dialog", "div", "dl", "dt",
          "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup",
          "hr", "html", "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot",
          "th", "thead", "tr", "ul", "center", "dir", "menu", "noscript"}
SKIP = {"script", "style", "noscript", "template", "head", "canvas", "object", "embed", "iframe", "select", "button",
        "textarea", "datalist", "map", "audio", "video", "dialog", "svg", "link", "meta", "base", "title", "frame", "frameset"}
NOISE_TAGS = {"nav", "aside", "footer"}
NOISE_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search", "dialog", "alertdialog"}
NOISE_CLASS = re.compile(r"(^|[-_\s])(nav|navbar|navigation|menu|sidebar|side-bar|footer|cookie|cookies|consent|banner|"
                         r"advert|adverts|ads|ad|popup|modal|breadcrumb|breadcrumbs|share|social|newsletter|toc-hidden|"
                         r"skip-link|visually-hidden|sr-only|screen-reader-text|printfooter|mw-editsection|noprint|"
                         r"reference-back|catlinks|mw-jump-link)([-_\s]|$)", re.I)
IMPLIED_END = {  # à l'ouverture de la clé, ces éléments ouverts sont fermés d'office
    "li": {"li"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"}, "tr": {"tr", "td", "th"}, "td": {"td", "th"},
    "th": {"td", "th"}, "thead": {"tbody", "tfoot", "thead"}, "tbody": {"tbody", "thead", "tfoot"},
    "tfoot": {"tbody", "thead"}, "option": {"option"}, "p": {"p"},
}
CLOSE_P_BEFORE = {"address", "article", "aside", "blockquote", "div", "dl", "fieldset", "footer", "form", "h1", "h2",
                  "h3", "h4", "h5", "h6", "header", "hr", "main", "nav", "ol", "pre", "section", "table", "ul", "p"}
MAX_DEPTH = 250


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "depth")

    def __init__(self, tag: str, attrs: Optional[Dict[str, str]] = None, parent: Optional["Node"] = None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: List[Union["Node", str]] = []
        self.parent = parent
        self.depth = parent.depth + 1 if parent else 0

    def get(self, k: str, d: str = "") -> str:
        return self.attrs.get(k, d)

    def cls(self) -> str:
        return self.attrs.get("class", "")

    def text(self) -> str:
        out: List[str] = []

        def rec(n: "Node") -> None:
            for c in n.children:
                if isinstance(c, str):
                    out.append(c)
                elif c.tag not in SKIP:
                    rec(c)

        rec(self)
        return "".join(out)

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root
        self.title = ""
        self.meta: Dict[str, str] = {}
        self.base = ""
        self._in_title = False
        self._raw: Optional[Node] = None

    def _close_to(self, names: set) -> None:
        n: Optional[Node] = self.cur
        while n is not None and n is not self.root:
            if n.tag in names:
                break
            if n.tag in ("table", "ul", "ol", "dl", "body", "html") and n.tag not in names:
                return  # ne franchit pas une frontière structurelle
            n = n.parent
        if n is not None and n is not self.root and n.tag in names:
            self.cur = n.parent or self.root

    def _in_svg(self) -> bool:
        n: Optional[Node] = self.cur
        while n is not None:
            if n.tag == "svg":
                return True
            n = n.parent
        return False

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag == "title" and not self._in_svg():      # le <title> d'un <svg> n'est pas celui du document
            self._in_title = True
            return
        if tag == "meta":
            name = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            if name and a.get("content"):
                self.meta.setdefault(name, a["content"])
            return
        if tag == "base" and a.get("href"):
            self.base = a["href"]
            return
        if tag in CLOSE_P_BEFORE and self.cur.tag == "p":
            self.cur = self.cur.parent or self.root
        implied = IMPLIED_END.get(tag)
        if implied and tag != "p":
            self._close_to(implied)
        if self.cur.depth >= MAX_DEPTH:  # imbrication pathologique : on aplatit
            if tag not in VOID:
                return
        node = Node(tag, a, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node
            if tag in ("script", "style", "textarea"):
                self._raw = node

    def handle_startendtag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag in ("meta", "link", "base"):
            self.handle_starttag(tag, attrs)
            return
        node = Node(tag, a, self.cur)
        self.cur.children.append(node)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            return
        if tag in VOID:
            return
        n: Optional[Node] = self.cur
        while n is not None and n is not self.root:
            if n.tag == tag:
                self.cur = n.parent or self.root
                if self._raw is n:
                    self._raw = None
                return
            n = n.parent
        # balise fermante orpheline : ignorée

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if data:
            self.cur.children.append(data)


def parse_html(text: str) -> TreeBuilder:
    b = TreeBuilder()
    b.feed(text)
    b.close()
    return b


# --------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------

_SVG_CASE = {"viewbox": "viewBox", "preserveaspectratio": "preserveAspectRatio", "foreignobject": "foreignObject", "textpath": "textPath",
             "lineargradient": "linearGradient", "radialgradient": "radialGradient", "clippath": "clipPath",
             "gradienttransform": "gradientTransform", "gradientunits": "gradientUnits", "patterntransform": "patternTransform",
             "textlength": "textLength", "startoffset": "startOffset", "markerwidth": "markerWidth", "markerheight": "markerHeight",
             "refx": "refX", "refy": "refY", "lengthadjust": "lengthAdjust"}
_SVG_DROP = {"metadata", "script", "style"}


def _svg_xml(n: "Node") -> str:
    """Re-sérialise un <svg> lu par l'analyseur HTML (noms mis en minuscules) en XML SVG valide."""
    def esc(s: str, attr: bool = False) -> str:
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return s.replace('"', "&quot;") if attr else s

    def rec(node: "Node", root: bool = False) -> str:
        tag = _SVG_CASE.get(node.tag, node.tag)
        if ":" in tag or tag in _SVG_DROP:
            return ""
        attrs = []
        for k, v in node.attrs.items():
            k = _SVG_CASE.get(k, k)
            if ":" in k and k not in ("xlink:href", "xml:space"):
                continue
            if k == "xmlns" or k.startswith("on"):
                continue
            attrs.append(f' {k}="{esc(v, True)}"')
        ns = ' xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"' if root else ""
        inner = "".join(esc(c) if isinstance(c, str) else rec(c) for c in node.children)
        return f"<{tag}{ns}{''.join(attrs)}>{inner}</{tag}>"

    return rec(n, True)


def _px(v: str) -> float:
    m = re.match(r"^\s*([\d.]+)\s*(?:px)?\s*$", v or "")
    return float(m.group(1)) if m else 0.0


class HtmlRenderer:
    def __init__(self, ctx: Ctx, base: str = "", stem: str = "img", image_loader: Optional[Callable[[str], Optional[bytes]]] = None):
        self.ctx, self.opts = ctx, ctx.opts
        self.base = base
        self.stem = stem
        self.image_loader = image_loader
        self.src_parts: List[str] = []
        self.footnotes: List[str] = []
        self.counter = 0
        self.svg_blind = 0

    # -- filtrage ---------------------------------------------------------
    def hidden(self, n: Node) -> bool:
        a = n.attrs
        if "hidden" in a or a.get("aria-hidden") == "true" and n.tag not in ("svg",) and not n.text().strip():
            return True
        st = a.get("style", "").replace(" ", "").lower()
        if "display:none" in st or "visibility:hidden" in st:
            return True
        return False

    def noise(self, n: Node) -> bool:
        if n.tag in NOISE_TAGS:
            return True
        if n.get("role") in NOISE_ROLES:
            return True
        ident = f"{n.cls()} {n.get('id')}"
        if ident.strip() and NOISE_CLASS.search(ident):
            return True
        return False

    def select_root(self, root: Node) -> Tuple[Node, str]:
        mode = self.opts.html_mode
        if mode == "full":
            body = next((c for c in root.iter() if c.tag == "body"), root)
            return body, "page entière"
        main = next((c for c in root.iter() if c.tag == "main" or c.get("role") == "main"), None)
        if main is None:
            arts = [c for c in root.iter() if c.tag == "article"]
            if len(arts) == 1 and len(arts[0].text().strip()) > 200:
                main = arts[0]
        if main is not None and (mode == "main" or mode == "auto"):
            return main, "contenu principal"
        body = next((c for c in root.iter() if c.tag == "body"), root)
        return body, "page entière"

    # -- blocs ---------------------------------------------------------------
    def render(self, root: Node, filter_noise: bool) -> str:
        blocks = self.blocks(root, filter_noise)
        md = "\n\n".join(b for b in blocks if b.strip())
        if self.footnotes:
            md += "\n\n" + "\n".join(self.footnotes)
        return md

    def blocks(self, n: Node, fn: bool) -> List[str]:
        out: List[str] = []
        inline_buf: List[Union[Node, str]] = []

        def flush() -> None:
            if inline_buf:
                t = self.inline_md(inline_buf)
                if t.strip():
                    out.append(t)
                inline_buf.clear()

        for c in n.children:
            if isinstance(c, str):
                inline_buf.append(c)
                continue
            if c.tag == "svg" and not (fn and self.noise(c)):        # SVG en ligne : légende, libellés, diagramme
                flush()
                block = self.svg_block(c)
                if block:
                    out.append(block)
                continue
            if c.tag in SKIP or self.hidden(c) or (fn and self.noise(c)):
                continue
            if c.tag in BLOCKS:
                flush()
                out.extend(self.block(c, fn))
            else:
                inline_buf.append(c)
        flush()
        return out

    def block(self, n: Node, fn: bool) -> List[str]:
        t = n.tag
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = re.sub(r"\s+", " ", self.inline_md(n.children, heading=True)).strip()
            return [f"{'#' * int(t[1])} {text}"] if text else []
        if t == "p":
            text = self.inline_md(n.children)
            return [text] if text.strip() else []
        if t == "pre":
            return [self.pre(n)]
        if t in ("ul", "ol", "menu", "dir"):
            return [self.list_md(n, fn)] if any(isinstance(c, Node) and c.tag == "li" for c in n.children) else self.blocks(n, fn)
        if t == "dl":
            return [self.dl(n, fn)]
        if t == "blockquote":
            inner = "\n\n".join(self.blocks(n, fn))
            return ["\n".join(("> " + ln) if ln.strip() else ">" for ln in inner.split("\n"))] if inner.strip() else []
        if t == "hr":
            return ["---"]
        if t == "table":
            return self.table(n, fn)
        if t == "figure":
            return self.blocks(n, fn)
        if t == "figcaption":
            text = self.inline_md(n.children)
            return [f"*{text}*"] if text.strip() and not text.startswith("*") else ([text] if text.strip() else [])
        if t == "details":
            return self.blocks(n, fn)
        if t == "summary":
            text = self.inline_md(n.children)
            return [f"**{text}**"] if text.strip() else []
        if t in ("li", "dd", "dt"):
            return self.blocks(n, fn)
        return self.blocks(n, fn)

    def svg_block(self, n: Node) -> str:
        """Texte d'un <svg> en ligne : nom accessible, libellés dans l'ordre de lecture, ou diagramme Mermaid.
        Icônes et décorations (masquées, petites, sans texte) sont ignorées sans bruit."""
        a = n.attrs
        if a.get("aria-hidden") == "true" or a.get("role") in ("presentation", "none") or a.get("focusable") == "false":
            return ""
        w, h = _px(a.get("width", "")), _px(a.get("height", ""))
        vb = [float(x) for x in re.findall(r"[-\d.]+", a.get("viewbox", ""))]
        if (w or h) and max(w, h) <= 48 or (not (w or h) and len(vb) == 4 and max(vb[2], vb[3]) <= 48):
            return ""
        from .fmt_diagram import render_graph
        from .fmt_svg import svg_outline
        from .util import parse_xml

        xml = _svg_xml(n).encode("utf-8")
        try:
            info = svg_outline(parse_xml(xml), xml, self.ctx)
        except Exception:
            return ""
        title, desc, texts, graph = str(info["title"]), str(info["desc"]), list(info["texts"]), info["graph"]  # type: ignore[arg-type]
        label = esc_inline(title) if title else ""
        if graph is not None:
            head = f"**Figure SVG — {label} (diagramme)**" if label else "**Figure SVG (diagramme)**"
            return head + "\n\n" + render_graph(graph, self.ctx.opts.diagrams)  # type: ignore[arg-type]
        shown, size = [], 0
        for t in texts:
            t = re.sub(r"\s+", " ", t).strip()[:80]
            if t and size + len(t) < 700 and len(shown) < 40:
                shown.append(esc_inline(t))
                size += len(t)
        more = f" … (+{len(texts) - len(shown)})" if len(texts) > len(shown) else ""
        bits = []
        if desc and desc != title:
            bits.append(esc_inline(desc))
        if shown:
            bits.append(" · ".join(shown) + more)
        if not label and not bits:
            if int(info["shapes"]) >= 20:  # type: ignore[arg-type]
                self.svg_blind += 1
            return ""
        head = f"**Figure SVG — {label}**" if label else "**Figure SVG**"
        return head + (" : " + " — ".join(bits) if bits else "")

    def pre(self, n: Node) -> str:
        code = next((c for c in n.children if isinstance(c, Node) and c.tag == "code"), None)
        src = code if code is not None else n
        raw = "".join(self._pre_text(src))
        lang = ""
        for el in (code, n):
            if el is not None:
                m = re.search(r"(?:language|lang|highlight-source)-([\w+#-]+)", el.cls())
                if m:
                    lang = m.group(1)
                    break
        raw = raw.strip("\n").replace("\r\n", "\n").replace(" ", " ")
        self.src_parts.append(raw)
        return fence(raw, lang)

    def _pre_text(self, n: Node) -> List[str]:
        out: List[str] = []
        for c in n.children:
            if isinstance(c, str):
                out.append(c)
            elif c.tag == "br":
                out.append("\n")
            elif c.tag not in SKIP:
                out.extend(self._pre_text(c))
        return out

    def list_md(self, n: Node, fn: bool, depth: int = 0) -> str:
        ordered = n.tag == "ol"
        try:
            start = int(n.get("start", "1"))
        except ValueError:
            start = 1
        lines: List[str] = []
        idx = start
        for c in n.children:
            if not isinstance(c, Node) or c.tag != "li" or self.hidden(c) or (fn and self.noise(c)):
                continue
            marker = f"{idx}." if ordered else "-"
            idx += 1
            inline_parts: List[Union[Node, str]] = []
            nested: List[str] = []
            extra: List[str] = []
            for k in c.children:
                if isinstance(k, Node) and k.tag in ("ul", "ol"):
                    nested.append(self.list_md(k, fn, depth + 1))
                elif isinstance(k, Node) and (k.tag in BLOCKS and k.tag not in ("li",)):
                    if inline_parts:
                        pass
                    if k.tag in ("p", "div", "span") or k.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                        inline_parts.append(" ")
                        inline_parts.append(k)
                    else:
                        extra.extend(self.block(k, fn))
                else:
                    inline_parts.append(k)
            text = self.inline_md(inline_parts).strip()
            text = re.sub(r"\n+", " ", text)
            pad = " " * len(marker + " ")
            head = f"{marker} {text}".rstrip()
            lines.append(head)
            for e in extra:
                lines.append(pad + e.replace("\n", "\n" + pad))
            for nl in nested:
                lines.append("\n".join(pad + ln for ln in nl.split("\n")))
        return "\n".join(lines)

    def dl(self, n: Node, fn: bool) -> str:
        out: List[str] = []
        for c in n.children:
            if not isinstance(c, Node) or c.tag not in ("dt", "dd"):
                continue
            text = self.inline_md(c.children).strip()
            if not text:
                continue
            out.append(f"**{text}**" if c.tag == "dt" else f": {text}")
        return "\n".join(out)

    # -- tableaux -----------------------------------------------------------------
    def table(self, n: Node, fn: bool) -> List[str]:
        rows: List[List[Node]] = []
        caption = ""
        head_rows = 0

        def collect(node: Node, in_head: bool = False) -> None:
            nonlocal caption, head_rows
            for c in node.children:
                if not isinstance(c, Node):
                    continue
                if c.tag == "caption":
                    caption = self.inline_md(c.children).strip()
                elif c.tag in ("thead", "tbody", "tfoot"):
                    collect(c, c.tag == "thead")
                elif c.tag == "tr":
                    cells = [k for k in c.children if isinstance(k, Node) and k.tag in ("td", "th")]
                    if cells:
                        rows.append(cells)
                        if in_head:
                            head_rows += 1
        collect(n)
        if not rows:
            return []
        ncols = max(sum(int(c.get("colspan", "1") or 1) if c.get("colspan", "1").isdigit() else 1 for c in r) for r in rows)
        has_th = any(c.tag == "th" for r in rows for c in r)
        nested = any(isinstance(x, Node) and x.tag == "table" for r in rows for c in r for x in c.iter()) if len(rows) < 400 else False
        long_cells = any(len(c.text().strip()) > 400 for r in rows for c in r)
        block_cells = sum(1 for r in rows for c in r if any(isinstance(x, Node) and x.tag in ("p", "div", "ul", "ol", "h1", "h2", "h3", "table") for x in c.children))
        layout = (n.get("role") in ("presentation", "none") or ncols == 1 and not has_th or nested
                  or (not has_th and (long_cells or block_cells > len(rows) * ncols * 0.5) and ncols <= 3))
        out: List[str] = []
        if layout:
            for r in rows:
                for c in r:
                    out.extend(self.blocks(c, fn))
            return out
        grid: List[List[str]] = []
        pending: Dict[int, Tuple[int, str]] = {}
        for r in rows:
            row: List[str] = []
            col = 0
            for c in r:
                while col in pending:
                    left, val = pending[col]
                    row.append(val)
                    if left <= 1:
                        del pending[col]
                    else:
                        pending[col] = (left - 1, val)
                    col += 1
                text = self.cell_text(c, fn)
                cs = int(c.get("colspan", "1")) if c.get("colspan", "1").isdigit() else 1
                rs = int(c.get("rowspan", "1")) if c.get("rowspan", "1").isdigit() else 1
                row.append(text)
                for k in range(1, cs):
                    row.append("")
                if rs > 1:
                    for k in range(cs):
                        pending[col + k] = (rs - 1, text if k == 0 else "")
                col += cs
            while col in pending:
                left, val = pending[col]
                row.append(val)
                if left <= 1:
                    del pending[col]
                else:
                    pending[col] = (left - 1, val)
                col += 1
            if any(x.strip() for x in row):
                grid.append(row)
        cap = self.opts.table_rows
        if cap and len(grid) - 1 > cap:
            extra = len(grid) - 1 - cap
            width = max(len(r) for r in grid)
            grid = grid[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (width - 1)]
        if caption:
            out.append(f"**{caption}**")
        out.append(md_table(grid))
        return out

    def cell_text(self, c: Node, fn: bool) -> str:
        parts: List[str] = []
        for blk in self.blocks(c, fn):
            if not blk.strip():
                continue
            lines = blk.split("\n")
            if all(re.match(r"^\s*(?:[-*+]|\d+[.)])\s", ln) or not ln.strip() for ln in lines):
                parts.extend("• " + re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", ln) for ln in lines if ln.strip())
                continue
            blk = blk.replace("\\\n", "<br>")
            parts.append(re.sub(r"\s*\n+\s*", " ", blk).strip())
        return "<br>".join(p for p in parts if p.strip())

    # -- inline -------------------------------------------------------------------
    def inline_md(self, nodes: List[Union[Node, str]], heading: bool = False) -> str:
        spans: List[Span] = []
        self.spans(nodes, Fmt(), spans, heading)
        text = render_spans(spans, inline_only=False, escape_start=True)
        text = re.sub(r"\\\n[ \t]*", "\\\n", text)
        return text.strip()

    def spans(self, nodes: List[Union[Node, str]], f: Fmt, out: List[Span], heading: bool = False) -> None:
        for c in nodes:
            if isinstance(c, str):
                t = re.sub(r"[ \t\r\n\f]+", " ", c)
                if t:
                    out.append(Span("t", t, f.copy()))
                    self.src_parts.append(t)
                continue
            tag = c.tag
            if tag in SKIP or self.hidden(c):
                if tag == "script" and c.get("type", "").startswith("math/tex"):
                    tex = c.text().strip()
                    out.append(Span("math", tex, display="mode=display" in c.get("type", "")))
                continue
            if tag == "br":
                out.append(Span("br"))
            elif tag in ("strong", "b"):
                self.spans(c.children, f.copy(bold=not heading), out, heading)
            elif tag in ("em", "i", "cite", "dfn", "var"):
                self.spans(c.children, f.copy(italic=not heading), out, heading)
            elif tag in ("del", "s", "strike"):
                self.spans(c.children, f.copy(strike=True), out, heading)
            elif tag in ("code", "kbd", "samp", "tt"):
                txt = c.text()
                if txt:
                    out.append(Span("t", txt, f.copy(code=True)))
                    self.src_parts.append(txt)
            elif tag == "sub":
                self.spans(c.children, f.copy(sub=True), out, heading)
            elif tag == "sup":
                txt = c.text().strip()
                if re.fullmatch(r"\[[^\]]{1,24}\]", txt) or "reference" in c.cls() or c.get("id", "").startswith("cite_ref"):
                    if txt:
                        out.append(Span("t", txt.replace("[", "\\[").replace("]", "\\]"), f.copy()))
                else:
                    self.spans(c.children, f.copy(sup=True), out, heading)
            elif tag == "q":
                out.append(Span("raw", "“"))
                self.spans(c.children, f, out, heading)
                out.append(Span("raw", "”"))
            elif tag == "a":
                href = c.get("href")
                if href and not href.lower().startswith(("javascript:", "#", "data:")) and not c.get("aria-hidden") == "true":
                    url = self.resolve(href)
                    self.spans(c.children, f.copy(link=url), out, heading)
                else:
                    self.spans(c.children, f, out, heading)
            elif tag == "img":
                md = self.image(c)
                if md:
                    out.append(Span("raw", md))
            elif tag in ("picture",):
                img = next((k for k in c.iter() if k.tag == "img"), None)
                if img is not None:
                    md = self.image(img)
                    if md:
                        out.append(Span("raw", md))
            elif tag == "input":
                if c.get("type") == "checkbox":
                    if re.search(r"(?i)toggle|hack|dropdown|menu|collapse|switch|hamburger|nav|sidebar", f"{c.cls()} {c.get('id')} {c.get('name')}"):
                        continue
                    out.append(Span("raw", "☑ " if "checked" in c.attrs else "☐ "))
                elif c.get("type") == "radio":
                    out.append(Span("raw", "◉ " if "checked" in c.attrs else "○ "))
            elif tag == "math":
                tex = next((k.text().strip() for k in c.iter() if k.tag == "annotation" and "tex" in k.get("encoding", "").lower()), "")
                out.append(Span("math", tex or re.sub(r"\s+", " ", c.text()).strip()))
            elif tag == "span" and "katex" in c.cls() and "katex-html" not in c.cls():
                tex = next((k.text().strip() for k in c.iter() if k.tag == "annotation"), "")
                if tex:
                    out.append(Span("math", tex, display="katex-display" in c.cls()))
                else:
                    self.spans(c.children, f, out, heading)
            elif tag == "span" and ("katex-html" in c.cls()):
                continue
            elif tag == "label":
                self.spans(c.children, f, out, heading)
            elif tag in ("abbr", "acronym", "time", "span", "font", "small", "big", "u", "mark", "ins", "bdi", "bdo", "data",
                         "wbr", "nobr", "center", "label", "output", "ruby", "rt", "rp"):
                if tag == "rp" or tag == "rt":
                    continue
                self.spans(c.children, f, out, heading)
            elif tag in BLOCKS:
                # bloc à l'intérieur d'un contexte en ligne (ex. <a><div>…</div></a>)
                inner: List[Span] = []
                self.spans(c.children, f, inner, heading)
                if inner and out and out[-1].kind != "br":
                    out.append(Span("t", " ", f.copy()))
                out.extend(inner)
                if inner:
                    out.append(Span("t", " ", f.copy()))
            else:
                self.spans(c.children, f, out, heading)

    def resolve(self, url: str) -> str:
        url = url.strip()
        if self.base and not re.match(r"^[a-zA-Z][\w+.-]*:", url) and not url.startswith(("//", "#")):
            from urllib.parse import urljoin

            return urljoin(self.base, url)
        return url

    def svg_alt(self, data: bytes) -> str:
        """Texte alternatif de secours pour une image SVG : son titre, sinon ses premiers libellés."""
        from .fmt_svg import svg_outline
        from .util import parse_xml

        try:
            info = svg_outline(parse_xml(data), data, self.ctx)
        except Exception:
            return ""
        label = str(info["title"]) or " · ".join(str(t) for t in list(info["texts"])[:12])  # type: ignore[call-overload]
        return alt_clean(label)[:200]

    def image(self, n: Node) -> str:
        src = n.get("src") or n.get("data-src") or ""
        alt = alt_clean(n.get("alt") or n.get("title") or "")
        w, h = n.get("width", ""), n.get("height", "")
        if (w.isdigit() and int(w) <= 2) or (h.isdigit() and int(h) <= 2):
            return ""
        if alt:
            self.src_parts.append(alt)
        m = re.match(r"data:image/([\w.+-]+);base64,(.*)$", src, re.S)
        if m:
            try:
                data = base64.b64decode(re.sub(r"\s+", "", m.group(2)))
            except Exception:
                return f"*[image : {alt}]*" if alt else ""
            ext = {"jpeg": "jpg", "svg+xml": "svg"}.get(m.group(1).lower(), m.group(1).lower())
            alt = alt or (self.svg_alt(data) if ext == "svg" else "")
            link = self.ctx.add_asset(data, ext, stem=self.stem, alt=alt)
            return f"![{alt}]({link})" if link else (f"*[image : {alt}]*" if alt else "")
        if not src:
            return f"*[image : {alt}]*" if alt else ""
        if self.image_loader and not re.match(r"^(https?:|//)", src):
            blob = self.image_loader(src)
            if blob:
                alt = alt or (self.svg_alt(blob) if src.lower().split("?")[0].endswith(".svg") else "")
                link = self.ctx.add_asset(blob, "", stem=self.stem, alt=alt)
                if link:
                    return f"![{alt}]({link})"
                return f"*[image : {alt}]*" if alt else ""
        if self.opts.images == "skip":
            return f"*[image : {alt}]*" if alt else ""
        return f"![{alt}]({md_url(self.resolve(src))})"


def html_to_markdown(text: str, ctx: Ctx, stem: str = "img",
                     image_loader: Optional[Callable[[str], Optional[bytes]]] = None,
                     base: str = "") -> Tuple[str, str, Dict[str, str], str]:
    """(markdown, titre, métadonnées, texte source) d'un document HTML.

    ``image_loader(src)`` renvoie les octets d'une image locale (pièce d'e-mail, membre d'EPUB…).
    """
    tb = parse_html(text)
    r = HtmlRenderer(ctx, base=tb.base or base, stem=stem, image_loader=image_loader)
    root, scope = r.select_root(tb.root)
    md = r.render(root, filter_noise=(scope == "page entière" and ctx.opts.html_mode != "full") or scope == "contenu principal")
    title = clean_text(re.sub(r"\s+", " ", tb.title)).strip()
    meta = {k: clean_text(v) for k, v in tb.meta.items()
            if k in ("description", "author", "og:title", "og:description", "article:published_time", "og:site_name", "date", "keywords")}
    if not title:
        title = meta.get("og:title", "")
    src = " ".join(r.src_parts)
    if r.svg_blind:
        ctx.warn(f"{r.svg_blind} SVG intégré(s) sans texte (illustration ou graphique) non restitué(s) : voir --render")
    if scope == "contenu principal":
        meta["_scope"] = "contenu principal"
    return md, title, meta, src


def decode_html(data: bytes) -> str:
    m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', data[:4096], re.I)
    if m and not data.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode(m.group(1).decode("ascii"), "replace")
        except (LookupError, UnicodeDecodeError):
            pass
    return decode_text(data)[0]


@engine("html", name="native", prio=10)
def html_native(path, ctx: Ctx) -> Result:
    p = Path(path)
    text = decode_html(p.read_bytes())
    if not re.search(r"<[a-zA-Z]", text):
        raise Unsupported("aucune balise HTML")
    md, title, meta, src = html_to_markdown(text, ctx, stem=re.sub(r"\W+", "-", p.stem).strip("-") or "img")
    if meta.pop("_scope", "") == "contenu principal":
        ctx.warn("bruit de page retiré : seul le contenu principal (<main>/<article>) est converti (--html-mode full pour tout garder)")
    author = meta.get("author")
    bits = [x for x in (author, (meta.get("article:published_time") or "")[:10]) if x]
    byline = ("_" + " · ".join(esc_inline(b) for b in bits) + "_") if bits else ""
    m1 = re.match(r"(#\s+[^\n]*\n+)", md)
    if m1:
        md = m1.group(1) + (byline + "\n\n" if byline else "") + md[m1.end():]
        head = ""
    else:
        head = (f"# {esc_inline(title)}\n\n" if title else "") + (byline + "\n\n" if byline else "")
    res = Result(markdown=head + md, fmt="html", engine="native", title=title, meta={k: v for k, v in meta.items() if k in ("author",)})
    res.source_text = src
    res.stats["partial_source"] = True
    return res
