"""RTF → Markdown, en bibliothèque standard : texte, gras/italique, titres (styles Word), listes, tableaux,
liens, images PNG/JPEG, notes de bas de page, caractères Unicode et pages de codes."""
from __future__ import annotations

import binascii
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .inline import Fmt, Span, render_spans
from .util import md_table

_DEST_SKIP = {
    "fonttbl", "colortbl", "stylesheet", "info", "header", "headerl", "headerr", "headerf", "footer", "footerl",
    "footerr", "footerf", "generator", "listtable", "listoverridetable", "rsidtbl", "latentstyles", "datastore",
    "themedata", "colorschememapping", "xmlnstbl", "wgrffmtfilter", "pnseclvl", "bkmkstart", "bkmkend", "object",
    "objdata", "private", "revtbl", "userprops", "mmathPr", "defchp", "defpap", "shpinst", "nonshppict",
    "operator", "author", "title_dest", "keywords", "comment", "doccomm", "template", "filetbl", "pgptbl",
    "fchars", "lchars", "ftnsep", "ftnsepc", "aftnsep", "aftnsepc", "falt", "panose", "fname", "fontemb",
    "fontfile", "docvar", "protusertbl", "shpgrp", "sp", "sn", "sv",
}
_MONO = ("courier", "consolas", "monaco", "lucida console", "menlo", "andale mono", "liberation mono", "dejavu sans mono")
_CTRL = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z])|([{}])|([^\\{}]+)")


class _State:
    __slots__ = ("skip", "bold", "italic", "strike", "sup", "sub", "font", "uc", "kind", "dest_name")

    def __init__(self, other: Optional["_State"] = None):
        if other:
            self.skip, self.bold, self.italic, self.strike = other.skip, other.bold, other.italic, other.strike
            self.sup, self.sub, self.font, self.uc, self.kind, self.dest_name = (
                other.sup, other.sub, other.font, other.uc, other.kind, other.dest_name)
        else:
            self.skip = False
            self.bold = self.italic = self.strike = self.sup = self.sub = False
            self.font = -1
            self.uc = 1
            self.kind = ""          # "", "pict", "fldinst", "fldrslt", "footnote", "label"
            self.dest_name = ""


class RtfParser:
    def __init__(self, data: bytes, ctx: Ctx):
        self.ctx = ctx
        text = data.decode("latin-1")
        self.text = text
        m = re.search(r"\\ansicpg(\d+)", text[:4000])
        self.codepage = f"cp{m.group(1)}" if m else "cp1252"
        self.fonts: Dict[int, str] = {}
        self.styles: Dict[int, str] = {}
        self.spans: List[Span] = []
        self.paras: List[Tuple[str, str, int, bool]] = []   # (kind, text, level, in_table)
        self.rows: List[List[str]] = []
        self.cells: List[str] = []
        self.cell_spans: List[Span] = []
        self.in_row = False
        self.pstyle = -1
        self.para_label = ""
        self.list_kind: Optional[str] = None
        self.footnotes: List[str] = []
        self.pict: Optional[Dict[str, object]] = None
        self.field_url: Optional[str] = None
        self.fld_instr = ""
        self.fld_depth: Dict[str, int] = {}
        self.src: List[str] = []
        self.blocks: List[str] = []
        self.pending_table: List[List[str]] = []
        self._cur_style = -1

    # -- pile de groupes ---------------------------------------------------
    def parse(self) -> None:
        st = _State()
        stack: List[_State] = []
        pos_uc_skip = 0
        for m in _CTRL.finditer(self.text):
            word, num, hexv, sym, brace, plain = m.groups()
            if brace == "{":
                stack.append(st)
                st = _State(st)
                pos_uc_skip = 0
                continue
            if brace == "}":
                self._close_group(st, len(stack))
                st = stack.pop() if stack else _State()
                continue
            if plain is not None:
                if pos_uc_skip:
                    n = min(pos_uc_skip, len(plain))
                    plain = plain[n:]
                    pos_uc_skip -= n
                if st.kind == "pict" and self.pict is not None:
                    self._pict_data(plain)
                    continue
                if st.skip:
                    if st.dest_name == "fonttbl":
                        self._font_name(plain, st)
                    elif st.dest_name == "stylesheet":
                        self._style_name(plain)
                    continue
                self._text(plain.replace("\r", "").replace("\n", ""), st)
                continue
            if hexv is not None:
                if pos_uc_skip:
                    pos_uc_skip -= 1
                    continue
                if st.skip or st.kind == "pict":
                    continue
                self._text(bytes([int(hexv, 16)]).decode(self.codepage, "replace"), st)
                continue
            if sym is not None:
                if sym == "*":
                    st.skip = True
                    st.dest_name = st.dest_name or "star"
                elif sym in "\\{}" and not st.skip:
                    self._text(sym, st)
                elif sym == "~" and not st.skip:
                    self._text(" ", st)
                elif sym == "_" and not st.skip:
                    self._text("-", st)
                continue
            # mot de contrôle
            w = word
            n = int(num) if num is not None else None
            if st.skip and st.dest_name == "stylesheet":
                if w in ("s", "cs", "ds") and n is not None:
                    self._cur_style = n if w == "s" else -1
                continue
            if w in _DEST_SKIP:
                st.skip = True
                st.dest_name = w
                continue
            if w == "pict":
                st.kind = "pict"
                self.pict = {"kind": "", "hex": [], "depth": len(stack)}
                continue
            if w == "field":
                self.field_url = None
                self.fld_instr = ""
                continue
            if w == "fldinst":
                st.skip = False
                st.kind = "fldinst"
                self.fld_depth["fldinst"] = len(stack)     # Word imbrique souvent {\*\fldinst {HYPERLINK "…"}}
                continue
            if w == "fldrslt":
                st.kind = "fldrslt"
                self.fld_depth["fldrslt"] = len(stack)
                continue
            if w == "footnote":
                st.kind = "footnote"
                self._flush_spans_marker()
                continue
            if w in ("pntext", "listtext"):
                st.kind = "label"
                continue
            if st.kind == "pict" and self.pict is not None:
                if w in ("pngblip", "jpegblip"):
                    self.pict["kind"] = w  # type: ignore[index]
                elif w in ("emfblip", "wmetafile", "macpict", "pmmetafile", "dibitmap", "wbitmap"):
                    self.pict["kind"] = "unsupported"  # type: ignore[index]
                continue
            if st.skip:
                continue
            if w == "par" or w == "sect":
                self._end_par(st)
            elif w == "line":
                self.spans.append(Span("br"))
            elif w in ("tab", "emdash", "endash", "bullet", "lquote", "rquote", "ldblquote", "rdblquote", "emspace", "enspace", "qmspace"):
                self._text({"tab": " ", "emdash": "—", "endash": "–", "bullet": "•", "lquote": "‘", "rquote": "’",
                            "ldblquote": "“", "rdblquote": "”"}.get(w, " "), st)
            elif w == "u" and n is not None:
                ch = chr(n if n >= 0 else n + 65536)
                self._text(ch, st)
                pos_uc_skip = st.uc
            elif w == "uc" and n is not None:
                st.uc = n
            elif w == "b":
                st.bold = n != 0
            elif w == "i":
                st.italic = n != 0
            elif w == "strike":
                st.strike = n != 0
            elif w == "super":
                st.sup, st.sub = True, False
            elif w == "sub":
                st.sub, st.sup = True, False
            elif w == "nosupersub":
                st.sup = st.sub = False
            elif w == "plain":
                st.bold = st.italic = st.strike = st.sup = st.sub = False
            elif w == "f" and n is not None:
                st.font = n
            elif w == "pard":
                self.pstyle = -1
                self.list_kind = None
            elif w == "s" and n is not None:
                self.pstyle = n
            elif w == "trowd":
                self.in_row = True
                self.cells = []
            elif w == "cell":
                self._end_cell(st)
            elif w == "row":
                self._end_row()
            elif w == "intbl":
                self.in_row = True
            elif w == "ilvl" and n is not None:
                pass
            elif w == "ls":
                self.list_kind = self.list_kind or "bullet"
            elif w == "outlinelevel" and n is not None:
                self.pstyle = 1000 + n
        self._end_par(st)
        self._flush_table()

    # -- éléments --------------------------------------------------------------
    def _font_name(self, plain: str, st: _State) -> None:
        name = plain.strip(" ;")
        if name and st.font >= 0:
            self.fonts[st.font] = name.lower()

    def _style_name(self, plain: str) -> None:
        name = plain.strip(" ;")
        if name and self._cur_style >= 0:
            self.styles.setdefault(self._cur_style, name)

    def _text(self, t: str, st: _State) -> None:
        if not t:
            return
        if st.kind == "label":
            self.para_label += t
            return
        if st.kind == "fldinst":
            self.fld_instr += t
            return
        f = Fmt(bold=st.bold, italic=st.italic, strike=st.strike, sup=st.sup, sub=st.sub,
                code=any(m in self.fonts.get(st.font, "") for m in _MONO))
        if self.field_url and st.kind == "fldrslt":
            f.link = self.field_url
        self.spans.append(Span("t", t, f))

    def _flush_spans_marker(self) -> None:
        self.footnotes.append("")
        self.spans.append(Span("raw", f"[^{len(self.footnotes)}]"))

    def _close_group(self, st: _State, depth: int) -> None:
        if self.pict is not None and depth == self.pict["depth"]:  # fin du groupe qui contient \pict
            self._finish_pict()
            self.pict = None
        elif st.kind == "fldinst" and depth == self.fld_depth.get("fldinst"):
            m = re.search(r'HYPERLINK\s+"?([^"\s]+)"?', self.fld_instr)
            self.field_url = m.group(1) if m and not m.group(1).startswith("\\") else None
            self.fld_instr = ""
        elif st.kind == "fldrslt" and depth == self.fld_depth.get("fldrslt"):
            self.field_url = None

    def _pict_data(self, plain: str) -> None:
        if self.pict is not None:
            self.pict["hex"].append(re.sub(r"[^0-9a-fA-F]", "", plain))  # type: ignore[union-attr]

    def _finish_pict(self) -> None:
        assert self.pict is not None
        kind = self.pict["kind"]
        if kind in ("pngblip", "jpegblip"):
            hexdata = "".join(self.pict["hex"])  # type: ignore[arg-type]
            if len(hexdata) % 2:
                hexdata = hexdata[:-1]
            try:
                data = binascii.unhexlify(hexdata)
            except binascii.Error:
                return
            link = self.ctx.add_asset(data, "png" if kind == "pngblip" else "jpg", stem="img")
            if link:
                self.spans.append(Span("raw", f"![]({link})"))
        elif kind == "unsupported":
            self.ctx.warn("image EMF/WMF ignorée (format non affichable)")

    def _end_cell(self, st: _State) -> None:
        text = render_spans(self.spans, inline_only=True, escape_start=False)
        self.spans = []
        self.cells.append(text)

    def _end_row(self) -> None:
        if self.cells:
            self.pending_table.append(self.cells)
        self.cells = []
        self.in_row = False

    def _flush_table(self) -> None:
        if self.pending_table:
            grid = [r for r in self.pending_table if any(c.strip() for c in r)]
            if grid:
                cap = self.ctx.opts.table_rows
                if cap and len(grid) - 1 > cap:
                    extra = len(grid) - 1 - cap
                    grid = grid[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (max(len(r) for r in grid) - 1)]
                self.blocks.append(md_table(grid))
            self.pending_table = []

    def _end_par(self, st: _State) -> None:
        if self.in_row:
            return  # dans un tableau, seul \cell termine le contenu
        self._flush_table()
        spans = self.spans
        self.spans = []
        label = self.para_label.strip()
        self.para_label = ""
        if not any(s.text.strip() or s.kind != "t" for s in spans):
            return
        self.src.append("".join(s.text for s in spans if s.kind == "t"))
        style_name = self.styles.get(self.pstyle, "").lower() if self.pstyle < 1000 else ""
        m = re.match(r"(?:heading|titre|überschrift)\s*(\d)", style_name)
        level = int(m.group(1)) if m else (self.pstyle - 1000 + 1 if self.pstyle >= 1000 and self.pstyle < 1009 else 0)
        if style_name == "title":
            level = 1
        if level:
            for s in spans:
                s.fmt.bold = s.fmt.italic = False
            text = render_spans(spans, inline_only=True, escape_start=False)
            self.blocks.append("#" * min(level, 6) + " " + text)
            return
        text = render_spans(spans, escape_start=True)
        if label:
            m_num = re.fullmatch(r"(\d+)[.)]?", label)
            self.blocks.append(f"{m_num.group(1)}. {text}" if m_num else f"- {text}")
            return
        self.blocks.append(text)


@engine("rtf", name="native", prio=10)
def rtf_native(path, ctx: Ctx) -> Result:
    data = Path(path).read_bytes()
    if not data.lstrip().startswith(b"{\\rtf"):
        raise Unsupported("signature RTF absente")
    p = RtfParser(data, ctx)
    p.parse()
    # regroupe les éléments de liste consécutifs en un seul bloc
    out: List[str] = []
    for b in p.blocks:
        if out and re.match(r"^(- |\d+\. )", b) and re.match(r"^(- |\d+\. )", out[-1].split("\n")[-1]):
            out[-1] += "\n" + b
        else:
            out.append(b)
    md = "\n\n".join(x for x in out if x.strip())
    if p.footnotes:
        md += "\n\n" + "\n".join(f"[^{i}]: …" for i in range(1, len(p.footnotes) + 1))
    if not md.strip():
        raise Unsupported("aucun texte extrait")
    res = Result(markdown=md, fmt="rtf", engine="native", title="")
    res.source_text = "\n".join(p.src)
    res.stats["partial_source"] = True
    return res
