"""DOCX → Markdown, en bibliothèque standard.

Fidélité visée : titres (styles, niveaux de plan, numérotation), listes
(à puces / numérotées / multi-niveaux), tableaux (fusions), liens, gras/italique/
code, notes de bas de page, commentaires, modifications suivies, images
(extraites), graphiques (données en tableau), SmartArt, équations (LaTeX),
zones de texte, cases à cocher, champs.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .inline import Fmt, Span, alt_clean, md_url, render_spans
from .ooxml import (NS, A, C, M, R, W, chart_markdown, chart_source_text, core_props, load_xml,
                    omml_to_latex, parse_chart, smartart_outline)
from .util import Rels, SafeZip, esc_inline, fence, local, md_table

# balises usuelles pré-calculées (les recherches ElementTree sont coûteuses)
T_P, T_R, T_T, T_TBL, T_TR, T_TC = W("p"), W("r"), W("t"), W("tbl"), W("tr"), W("tc")
T_PPR, T_RPR, T_PSTYLE, T_NUMPR = W("pPr"), W("rPr"), W("pStyle"), W("numPr")
VAL = W("val")

_MONO_FONTS = {
    "courier", "courier new", "consolas", "menlo", "monaco", "lucida console", "source code pro", "fira code",
    "fira mono", "dejavu sans mono", "liberation mono", "andale mono", "cascadia code", "cascadia mono",
    "jetbrains mono", "ubuntu mono", "roboto mono", "sf mono", "inconsolata", "hack", "monospace", "terminal",
    "lucida sans typewriter", "courier std", "ocr a extended", "noto mono", "noto sans mono", "space mono",
}
_CODE_PSTYLES = re.compile(r"^(code|source ?code|preformatted( text)?|html preformatted|verbatim|code ?block|"
                           r"codeblock|macro( text)?|plain text|listing|programlisting)\b", re.I)
_CODE_RSTYLES = re.compile(r"(verbatim ?char|html code|html typewriter|html sample|code ?char|source ?code|"
                           r"inline ?code|macro ?text|code$)", re.I)
_HEADING_NAME = re.compile(r"^(?:heading|titre|überschrift|título|rubrik|kop|nagłówek|заголовок)\s*(\d)$", re.I)
_MANUAL_BULLET = re.compile(r"^\s*([•·▪◦●○■□◆◇➢➤▶►‣⁃–—*-])[\s\t]+(?=\S)")
_SYM = {"F0FC": "✓", "F0FB": "✗", "F0FE": "☑", "F0A8": "☐", "F0A7": "▪", "F0B7": "•", "F076": "❖",
        "F0D8": "➢", "F0E0": "→", "F0E8": "➔", "F0A1": "☺", "F06E": "■", "F06F": "□", "F071": "❑"}
def _is_on(el: Optional[ET.Element]) -> Optional[bool]:
    """Interrupteur booléen OOXML : absent → None, <w:b/> → True, val=0/false/off → False."""
    if el is None:
        return None
    v = el.get(VAL)
    if v is None:
        return True
    return v.lower() not in ("0", "false", "off", "none")


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------

@dataclass
class Style:
    sid: str
    name: str = ""
    kind: str = "paragraph"
    based_on: Optional[str] = None
    outline: Optional[int] = None
    num_id: Optional[int] = None
    ilvl: Optional[int] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    strike: Optional[bool] = None
    mono: Optional[bool] = None
    size: Optional[float] = None


def _rpr_props(rpr: Optional[ET.Element]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    if rpr is None:
        return out
    b, i = _is_on(rpr.find(W("b"))), _is_on(rpr.find(W("i")))
    st = _is_on(rpr.find(W("strike")))
    if st is None:
        st = _is_on(rpr.find(W("dstrike")))
    if b is not None:
        out["bold"] = b
    if i is not None:
        out["italic"] = i
    if st is not None:
        out["strike"] = st
    sz = rpr.find(W("sz"))
    if sz is not None and sz.get(VAL, "").isdigit():
        out["size"] = int(sz.get(VAL)) / 2.0
    fonts = rpr.find(W("rFonts"))
    if fonts is not None:
        names = [fonts.get(W(k), "") for k in ("ascii", "hAnsi", "cs", "eastAsia")]
        if any(n.lower() in _MONO_FONTS for n in names if n):
            out["mono"] = True
        elif any(names):
            out["mono"] = False
    return out


class Styles:
    def __init__(self, root: Optional[ET.Element]):
        self.by_id: Dict[str, Style] = {}
        self.default_size = 11.0
        self.default_pstyle: Optional[str] = None
        self._cache: Dict[str, Style] = {}
        if root is None:
            return
        dd = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        props = _rpr_props(dd)
        if "size" in props:
            self.default_size = float(props["size"])  # type: ignore[arg-type]
        for s in root.findall("w:style", NS):
            sid = s.get(W("styleId"), "")
            st = Style(sid, kind=s.get(W("type"), "paragraph"))
            n = s.find("w:name", NS)
            st.name = n.get(VAL, "") if n is not None else sid
            b = s.find("w:basedOn", NS)
            st.based_on = b.get(VAL) if b is not None else None
            if s.get(W("default")) in ("1", "true") and st.kind == "paragraph":
                self.default_pstyle = sid
            ppr = s.find("w:pPr", NS)
            if ppr is not None:
                ol = ppr.find("w:outlineLvl", NS)
                if ol is not None and ol.get(VAL, "").isdigit():
                    st.outline = int(ol.get(VAL))
                npr = ppr.find("w:numPr", NS)
                if npr is not None:
                    nid, il = npr.find("w:numId", NS), npr.find("w:ilvl", NS)
                    if nid is not None and nid.get(VAL, "").lstrip("-").isdigit():
                        st.num_id = int(nid.get(VAL))
                    if il is not None and il.get(VAL, "").isdigit():
                        st.ilvl = int(il.get(VAL))
            props = _rpr_props(s.find("w:rPr", NS))
            st.bold, st.italic = props.get("bold"), props.get("italic")  # type: ignore[assignment]
            st.strike, st.mono, st.size = props.get("strike"), props.get("mono"), props.get("size")  # type: ignore[assignment]
            self.by_id[sid] = st

    def resolve(self, sid: Optional[str]) -> Style:
        """Style avec héritage (basedOn) appliqué."""
        if not sid or sid not in self.by_id:
            return Style(sid or "")
        if sid in self._cache:
            return self._cache[sid]
        chain: List[Style] = []
        seen = set()
        cur: Optional[str] = sid
        while cur and cur in self.by_id and cur not in seen:
            seen.add(cur)
            chain.append(self.by_id[cur])
            cur = self.by_id[cur].based_on
        merged = Style(sid, name=self.by_id[sid].name, kind=self.by_id[sid].kind)
        for st in reversed(chain):  # du plus générique au plus spécifique
            for attr in ("outline", "num_id", "ilvl", "bold", "italic", "strike", "mono", "size"):
                v = getattr(st, attr)
                if v is not None:
                    setattr(merged, attr, v)
        self._cache[sid] = merged
        return merged


# --------------------------------------------------------------------------
# Numérotation
# --------------------------------------------------------------------------

@dataclass
class Lvl:
    fmt: str = "decimal"
    text: str = "%1."
    start: int = 1
    is_lgl: bool = False


def _roman(n: int, upper: bool) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
            (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out.upper() if upper else out


def _alpha(n: int, upper: bool) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(97 + r) + s
    return s.upper() if upper else s


def format_counter(n: int, fmt: str) -> str:
    if fmt == "lowerLetter":
        return _alpha(n, False)
    if fmt == "upperLetter":
        return _alpha(n, True)
    if fmt == "lowerRoman":
        return _roman(n, False)
    if fmt == "upperRoman":
        return _roman(n, True)
    if fmt == "decimalZero":
        return f"{n:02d}"
    if fmt == "none":
        return ""
    return str(n)


class Numbering:
    def __init__(self, root: Optional[ET.Element]):
        self.abstract: Dict[int, Dict[int, Lvl]] = {}
        self.num_abs: Dict[int, int] = {}
        self.overrides: Dict[int, Dict[int, int]] = {}
        self._counters: Dict[Tuple[int, int], List[int]] = {}
        if root is None:
            return
        for an in root.findall("w:abstractNum", NS):
            aid = int(an.get(W("abstractNumId"), "0"))
            lv: Dict[int, Lvl] = {}
            for l in an.findall("w:lvl", NS):
                il = int(l.get(W("ilvl"), "0"))
                fmt = l.find("w:numFmt", NS)
                txt = l.find("w:lvlText", NS)
                st = l.find("w:start", NS)
                lgl = l.find("w:isLgl", NS)
                lv[il] = Lvl(
                    fmt=fmt.get(VAL, "decimal") if fmt is not None else "decimal",
                    text=txt.get(VAL, "") if txt is not None else "%1.",
                    start=int(st.get(VAL, "1")) if st is not None and st.get(VAL, "").lstrip("-").isdigit() else 1,
                    is_lgl=_is_on(lgl) is True,
                )
            self.abstract[aid] = lv
        for n in root.findall("w:num", NS):
            nid = int(n.get(W("numId"), "0"))
            a = n.find("w:abstractNumId", NS)
            if a is not None:
                self.num_abs[nid] = int(a.get(VAL, "0"))
            ov: Dict[int, int] = {}
            for o in n.findall("w:lvlOverride", NS):
                so = o.find("w:startOverride", NS)
                if so is not None and so.get(VAL, "").lstrip("-").isdigit():
                    ov[int(o.get(W("ilvl"), "0"))] = int(so.get(VAL))
            if ov:
                self.overrides[nid] = ov

    def level(self, num_id: int, ilvl: int) -> Lvl:
        aid = self.num_abs.get(num_id)
        lv = self.abstract.get(aid if aid is not None else -1, {})
        return lv.get(ilvl) or lv.get(0) or Lvl(fmt="bullet", text="•")

    def next(self, num_id: int, ilvl: int) -> Tuple[Lvl, str, int]:
        """Avance le compteur du niveau et renvoie (définition, étiquette « 1.2. », numéro)."""
        aid = self.num_abs.get(num_id, -1)
        key = (aid, num_id if num_id in self.overrides else 0)
        counters = self._counters.setdefault(key, [])
        lvl = self.level(num_id, ilvl)
        while len(counters) <= ilvl:
            idx = len(counters)
            base = self.level(num_id, idx).start
            ov = self.overrides.get(num_id, {}).get(idx)
            counters.append((ov if ov is not None else base) - 1)
        counters[ilvl] += 1
        for deeper in range(ilvl + 1, len(counters)):
            base = self.level(num_id, deeper).start
            ov = self.overrides.get(num_id, {}).get(deeper)
            counters[deeper] = (ov if ov is not None else base) - 1
        if lvl.fmt == "bullet":
            return lvl, lvl.text, counters[ilvl]

        def sub(m: "re.Match[str]") -> str:
            k = int(m.group(1)) - 1
            if k >= len(counters):
                return ""
            f = self.level(num_id, k).fmt
            if lvl.is_lgl and f not in ("decimal", "decimalZero"):
                f = "decimal"
            return format_counter(max(counters[k], 0), f)

        label = re.sub(r"%(\d)", sub, lvl.text)
        return lvl, label, counters[ilvl]


# --------------------------------------------------------------------------
# Structures intermédiaires
# --------------------------------------------------------------------------

@dataclass
class Block:
    kind: str                # h | p | li | code | quote | raw | hr | table
    text: str = ""
    level: int = 0
    marker: str = ""         # bullet | ord | label
    label: str = ""
    lines: List[str] = field(default_factory=list)
    size: float = 0.0        # taille dominante (inférence de titres)
    bold: bool = False


TOC_STYLE = re.compile(r"^(toc|table of contents|tdm|index|table des mati)", re.I)


# --------------------------------------------------------------------------
# Convertisseur
# --------------------------------------------------------------------------

class DocxConverter:
    def __init__(self, zf: SafeZip, ctx: Ctx, main: str):
        self.zf, self.ctx, self.opts = zf, ctx, ctx.opts
        self.main = main
        self.rels = Rels(zf, main)
        self.styles = Styles(load_xml(zf, self._sibling("styles.xml")))
        self.numbering = Numbering(load_xml(zf, self._sibling("numbering.xml")))
        self.footnote_defs: Dict[str, ET.Element] = {}
        self.endnote_defs: Dict[str, ET.Element] = {}
        self.comments: Dict[str, Dict[str, object]] = {}
        self.fn_order: List[str] = []
        self.en_order: List[str] = []
        self.cm_order: List[str] = []
        self.cm_anchor: Dict[str, List[str]] = {}
        self._open_ranges: List[str] = []
        self.field_stack: List[Dict[str, object]] = []
        self.tracked = 0
        self.headings_seen = 0
        self.src_parts: List[str] = []
        self.math_count = 0
        self._notes_loaded = False
        self.in_note = False
        self.skip_toc_depth = 0
        self._load_notes()

    # -- chargement --------------------------------------------------------
    def _sibling(self, name: str) -> str:
        base = self.main.rsplit("/", 1)[0] if "/" in self.main else ""
        return f"{base}/{name}" if base else name

    def _load_notes(self) -> None:
        for fname, store, tag in (("footnotes.xml", self.footnote_defs, "footnote"),
                                  ("endnotes.xml", self.endnote_defs, "endnote")):
            root = load_xml(self.zf, self._sibling(fname))
            if root is None:
                continue
            for n in root.findall("w:" + tag, NS):
                if n.get(W("type"), "normal") in ("separator", "continuationSeparator", "continuationNotice"):
                    continue
                store[n.get(W("id"), "")] = n
        root = load_xml(self.zf, self._sibling("comments.xml"))
        if root is not None:
            parent_of: Dict[str, str] = {}
            ext = load_xml(self.zf, self._sibling("commentsExtended.xml"))
            if ext is not None:
                for ce in ext:
                    if local(ce.tag) == "commentEx":
                        pid = ce.get("{http://schemas.microsoft.com/office/word/2012/wordml}paraIdParent")
                        para = ce.get("{http://schemas.microsoft.com/office/word/2012/wordml}paraId")
                        if pid and para:
                            parent_of[para] = pid
            last_para: Dict[str, str] = {}
            for c in root.findall("w:comment", NS):
                cid = c.get(W("id"), "")
                paras = c.findall(".//w:p", NS)
                pid = paras[-1].get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId") if paras else None
                self.comments[cid] = {"el": c, "author": c.get(W("author"), ""), "date": (c.get(W("date"), "") or "")[:10],
                                      "para": pid, "parent_para": None}
                if pid:
                    last_para[pid] = cid
            for cid, info in self.comments.items():
                for p in info["el"].findall(".//w:p", NS):  # type: ignore[union-attr]
                    pp = p.get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId")
                    if pp in parent_of:
                        info["parent"] = last_para.get(parent_of[pp])

    # -- utilitaires de style ---------------------------------------------
    def pstyle_of(self, p: ET.Element) -> Style:
        ppr = p.find(T_PPR)
        sid = None
        if ppr is not None:
            ps = ppr.find(T_PSTYLE)
            if ps is not None:
                sid = ps.get(VAL)
        if sid is None:
            sid = self.styles.default_pstyle
        return self.styles.resolve(sid)

    def heading_level(self, p: ET.Element, st: Style) -> Optional[int]:
        name = (st.name or "").strip()
        if name.lower() == "title":
            return 0
        m = _HEADING_NAME.match(name) or _HEADING_NAME.match(st.sid or "")
        if m:
            return int(m.group(1))
        ppr = p.find(T_PPR)
        if ppr is not None:
            ol = ppr.find("w:outlineLvl", NS)
            if ol is not None and ol.get(VAL, "").isdigit() and int(ol.get(VAL)) < 9:
                return int(ol.get(VAL)) + 1
        if st.outline is not None and st.outline < 9:
            return st.outline + 1
        return None

    # -- entrée principale -------------------------------------------------
    def run(self) -> Result:
        root = load_xml(self.zf, self.main)
        if root is None:
            raise Unsupported("document.xml illisible")
        body = root.find("w:body", NS)
        if body is None:
            raise Unsupported("document sans corps")
        blocks = self.blocks_of(body)
        self._infer_headings(blocks)
        md = self.assemble(blocks)
        tail = self.render_notes()
        if tail:
            md = md.rstrip() + "\n\n" + tail
        if self.opts.headers_footers:
            hf = self._headers_footers()
            if hf:
                md = md.rstrip() + "\n\n---\n\n*En-têtes et pieds de page :* " + " · ".join(esc_inline(t) for t in hf)
        props = core_props(self.zf)
        if self.headings_seen == 0 and not any(b.kind == "h" for b in blocks):
            pass
        title = props.get("title", "")
        if not title:
            for b in blocks:
                if b.kind == "h":
                    title = re.sub(r"[*_`\\]", "", b.text)
                    break
        res = Result(markdown=md, fmt="docx", engine="native", title=title, meta=dict(props))
        res.source_text = "\n".join(self._raw_text(body))
        if self.tracked:
            self.ctx.warn(f"{self.tracked} modification(s) suivie(s) : {'texte supprimé conservé barré' if self.opts.track_changes == 'mark' else 'acceptées (texte supprimé ignoré)'}")
        if self.ctx.skipped_images:
            self.ctx.warn(f"{self.ctx.skipped_images} image(s) décorative(s) ignorée(s) (trop petites)")
        return res

    def _headers_footers(self) -> List[str]:
        """Textes uniques des en-têtes et pieds de page (hors simples numéros de page)."""
        seen: List[str] = []
        for typ in ("header", "footer"):
            for _rid, part in self.rels.of_type(typ):
                root = load_xml(self.zf, part)
                if root is None:
                    continue
                text = " ".join(t.strip() for t in ("".join(x.text or "" for x in p.iter(T_T)) for p in root.iter(T_P)) if t.strip())
                text = re.sub(r"\s+", " ", text).strip()
                if text and not re.fullmatch(r"(page\s*)?\d+(\s*(/|sur|of)\s*\d+)?", text, re.I) and text not in seen:
                    seen.append(text)
        return seen

    # -- texte brut indépendant (contrôle de rappel) -----------------------
    def _raw_text(self, root: ET.Element) -> List[str]:
        out: List[str] = []
        skip_tags = {W("del"), W("moveFrom"), W("instrText"), W("delText"), M("oMath"), M("oMathPara"),
                     "{%s}Fallback" % NS["mc"], W("pict")}

        def walk(el: ET.Element, buf: List[str]) -> None:
            for c in el:
                tag = c.tag
                if tag in skip_tags:
                    continue
                if tag == T_P:
                    ppr = c.find(T_PPR)
                    if not self.opts.keep_toc and ppr is not None:
                        ps = ppr.find(T_PSTYLE)
                        if ps is not None and TOC_STYLE.match(self.styles.resolve(ps.get(VAL)).name or ""):
                            continue
                    parts: List[str] = []
                    walk(c, parts)
                    out.append("".join(parts))
                elif tag == T_T:
                    buf.append(c.text or "")
                elif tag in (W("br"), W("cr"), W("tab"), W("ptab")):
                    buf.append(" ")
                elif tag == W("noBreakHyphen"):
                    buf.append("-")
                else:
                    walk(c, buf)

        walk(root, [])
        return out

    # -- blocs -------------------------------------------------------------
    def blocks_of(self, parent: ET.Element) -> List[Block]:
        blocks: List[Block] = []
        for child in parent:
            tag = child.tag
            if tag == T_P:
                blocks.extend(self.paragraph(child))
            elif tag == T_TBL:
                blocks.extend(self.table(child))
            elif tag == W("sdt"):
                pr = child.find("w:sdtPr", NS)
                gal = pr.find("w:docPartObj/w:docPartGallery", NS) if pr is not None else None
                if gal is not None and "table of contents" in gal.get(VAL, "").lower() and not self.opts.keep_toc:
                    continue
                content = child.find("w:sdtContent", NS)
                if content is not None:
                    blocks.extend(self.blocks_of(content))
            elif tag == "{%s}AlternateContent" % NS["mc"]:
                choice = child.find("mc:Choice", NS)
                pick = choice if choice is not None else child.find("mc:Fallback", NS)
                if pick is not None:
                    blocks.extend(self.blocks_of(pick))
            elif tag in (W("sectPr"), W("bookmarkStart"), W("bookmarkEnd"), W("proofErr"), W("permStart"),
                         W("permEnd"), W("commentRangeStart"), W("commentRangeEnd")):
                continue
            elif tag in (W("del"), W("moveFrom")):
                self.tracked += 1
                continue
            elif len(child):
                blocks.extend(self.blocks_of(child))  # ins, customXml, smartTag, txbxContent, …
        return blocks

    def paragraph(self, p: ET.Element) -> List[Block]:
        st = self.pstyle_of(p)
        ppr = p.find(T_PPR)
        # numérotation : toujours avancée, même si le paragraphe est ensuite ignoré
        num_id, ilvl = None, 0
        if ppr is not None:
            npr = ppr.find(T_NUMPR)
            if npr is not None:
                ni, il = npr.find("w:numId", NS), npr.find("w:ilvl", NS)
                if ni is not None and ni.get(VAL, "").lstrip("-").isdigit():
                    num_id = int(ni.get(VAL))
                if il is not None and il.get(VAL, "").isdigit():
                    ilvl = int(il.get(VAL))
        if num_id is None and st.num_id is not None:
            num_id, ilvl = st.num_id, (st.ilvl or 0)
        numinfo: Optional[Tuple[Lvl, str, int]] = None
        if num_id:
            numinfo = self.numbering.next(num_id, ilvl)

        name = (st.name or "")
        in_toc_field = self.skip_toc_depth > 0
        toc_para = bool(TOC_STYLE.match(name)) and not name.lower().startswith("index")
        spans = self.inline_children(p, st)
        for cid in self._open_ranges:  # une plage de commentaire à cheval sur plusieurs paragraphes
            self.cm_anchor.setdefault(cid, []).append(" ")
        if (toc_para or in_toc_field) and not self.opts.keep_toc:
            return []
        # scinde à chaque bloc inséré (graphique, SmartArt, zone de texte…)
        out: List[Block] = []
        segment: List[Span] = []
        pieces: List[Tuple[str, object]] = []
        for s in spans:
            if s.kind == "block":
                pieces.append(("spans", segment))
                pieces.append(("block", s.text))
                segment = []
            else:
                segment.append(s)
        pieces.append(("spans", segment))
        first_text_done = False
        for kind, payload in pieces:
            if kind == "block":
                out.append(Block("raw", text=payload))  # type: ignore[arg-type]
                continue
            seg: List[Span] = payload  # type: ignore[assignment]
            blk = self._classify(seg, st, p, numinfo, ilvl, name, first_text_done)
            if blk is not None:
                out.extend(blk)
                first_text_done = True
        return out

    def _classify(self, spans: List[Span], st: Style, p: ET.Element, numinfo, ilvl: int, name: str,
                  already: bool) -> Optional[List[Block]]:
        text_present = any((s.kind in ("t", "raw", "math", "fn", "cm") and (s.text.strip() or s.kind != "t")) for s in spans)
        if not text_present:
            return None
        lvl = self.heading_level(p, st)
        lname = name.lower()
        # code
        if _CODE_PSTYLES.match(name) or (
                st.mono and all(s.fmt.code or s.kind == "br" or not s.text.strip() for s in spans if s.kind in ("t", "br"))
                and any(s.kind == "t" and s.text.strip() for s in spans)):
            raw = "".join(s.text if s.kind == "t" else ("\n" if s.kind == "br" else "") for s in spans)
            return [Block("code", lines=raw.split("\n"))]
        all_code = all(s.fmt.code for s in spans if s.kind == "t" and s.text.strip()) and any(
            s.kind == "t" and s.text.strip() for s in spans) and not any(s.kind != "t" and s.kind != "br" for s in spans)
        if all_code and numinfo is None and lvl is None:
            raw = "".join(s.text if s.kind == "t" else "\n" for s in spans)
            return [Block("code", lines=raw.split("\n"))]
        if lvl is not None:
            self.headings_seen += 1
            for s in spans:
                s.fmt.bold = False
                s.fmt.italic = False
            text = self.render_spans(spans, inline_only=True)
            if numinfo and numinfo[0].fmt not in ("bullet", "none") and numinfo[1].strip():
                text = f"{numinfo[1].strip()} {text}"
            if not text.strip():
                return None
            return [Block("h", text=text, level=lvl if lvl > 0 else 1, marker="title" if lvl == 0 else "")]
        if lname == "subtitle":
            for s in spans:
                s.fmt.italic = True
                s.fmt.bold = False
            return [Block("p", text=self.render_spans(spans))]
        text = self.render_spans(spans)
        if not text.strip():
            return None
        if lname in ("quote", "intense quote", "block text", "blockquote", "citation", "citation intense"):
            return [Block("quote", text=text)]
        if lname == "caption" or lname == "légende":
            return [Block("p", text=text if text.startswith("*") else f"*{text}*")]
        if numinfo is not None and numinfo[0].fmt != "none":
            lv, label, number = numinfo
            if lv.fmt == "bullet":
                return [Block("li", text=text, level=ilvl, marker="bullet")]
            simple = re.fullmatch(r"%%%d[.)]?" % (ilvl + 1), lv.text) is not None and lv.fmt == "decimal"
            if simple:
                return [Block("li", text=text, level=ilvl, marker="ord", label=str(number))]
            return [Block("li", text=text, level=ilvl, marker="label", label=label.strip())]
        m = _MANUAL_BULLET.match(text) if not already else None
        raw_first = next((s.text for s in spans if s.kind == "t" and s.text), "")
        if m and _MANUAL_BULLET.match(raw_first):
            return [Block("li", text=text[m.end():], level=0, marker="bullet")]
        if lname.startswith("list bullet") or lname.startswith("liste à puces"):
            return [Block("li", text=text, level=self._suffix_level(lname), marker="bullet")]
        if lname.startswith("list number") or lname.startswith("liste numérotée"):
            return [Block("li", text=text, level=self._suffix_level(lname), marker="ord", label="1")]
        blk = Block("p", text=text)
        chars: Dict[float, int] = {}
        bold_chars = tot = 0
        for sp in spans:
            if sp.kind == "t" and sp.text.strip():
                n_ = len(sp.text.strip())
                chars[sp.size] = chars.get(sp.size, 0) + n_
                tot += n_
                if sp.fmt.bold:
                    bold_chars += n_
        if chars:
            blk.size = max(chars.items(), key=lambda kv: kv[1])[0]
            blk.bold = tot > 0 and bold_chars >= 0.98 * tot
        return [blk]

    @staticmethod
    def _suffix_level(name: str) -> int:
        m = re.search(r"(\d)\s*$", name)
        return int(m.group(1)) - 1 if m else 0

    # -- inline ------------------------------------------------------------
    def inline_children(self, parent: ET.Element, pst: Style, fmt: Optional[Fmt] = None) -> List[Span]:
        spans: List[Span] = []
        base = fmt or Fmt()
        for c in parent:
            tag = c.tag
            if tag == T_R:
                spans.extend(self.text_run(c, pst, base))
            elif tag == W("hyperlink"):
                url = None
                rid = c.get(R("id"))
                if rid and self.rels.is_external(rid):
                    url = self.rels.target(rid)
                elif c.get(W("anchor")):
                    url = None
                f2 = base.copy(link=url or base.link)
                spans.extend(self.inline_children(c, pst, f2))
            elif tag == W("fldSimple"):
                instr = c.get(W("instr"), "")
                inner = self.inline_children(c, pst, base)
                spans.extend(self._apply_field(instr, inner, base))
            elif tag == W("ins"):
                self.tracked += 1
                f2 = base.copy(ins=self.opts.track_changes == "mark")
                spans.extend(self.inline_children(c, pst, f2))
            elif tag in (W("del"), W("moveFrom")):
                self.tracked += 1
                if self.opts.track_changes == "mark":
                    f2 = base.copy(dele=True)
                    spans.extend(self.inline_children(c, pst, f2))
            elif tag == W("moveTo"):
                self.tracked += 1
                spans.extend(self.inline_children(c, pst, base))
            elif tag in (M("oMath"), M("oMathPara")):
                latex = omml_to_latex(c)
                if latex:
                    self.math_count += 1
                    spans.append(Span("math", latex, display=(tag == M("oMathPara"))))
            elif tag == W("commentRangeStart"):
                cid = c.get(W("id"), "")
                self._open_ranges.append(cid)
            elif tag == W("commentRangeEnd"):
                cid = c.get(W("id"), "")
                if cid in self._open_ranges:
                    self._open_ranges.remove(cid)
            elif tag == W("sdt"):
                spans.extend(self._sdt_inline(c, pst, base))
            elif tag == "{%s}AlternateContent" % NS["mc"]:
                choice = c.find("mc:Choice", NS)
                pick = choice if choice is not None else c.find("mc:Fallback", NS)
                if pick is not None:
                    spans.extend(self.inline_children(pick, pst, base))
            elif tag in (T_PPR, W("bookmarkStart"), W("bookmarkEnd"), W("proofErr"), W("permStart"), W("permEnd")):
                continue
            elif len(c):
                spans.extend(self.inline_children(c, pst, base))  # smartTag, customXml, dir, bdo…
        return spans

    def _sdt_inline(self, sdt: ET.Element, pst: Style, base: Fmt) -> List[Span]:
        pr = sdt.find("w:sdtPr", NS)
        if pr is not None:
            cb = pr.find("w14:checkbox", NS)
            if cb is not None:
                chk = cb.find("w14:checked", NS)
                on = chk is not None and chk.get("{%s}val" % NS["w14"], "0") in ("1", "true")
                return [Span("raw", "☑" if on else "☐")]
            if pr.find("w:showingPlcHdr", NS) is not None:
                return []
        content = sdt.find("w:sdtContent", NS)
        return self.inline_children(content, pst, base) if content is not None else []

    def text_run(self, r: ET.Element, pst: Style, base: Fmt) -> List[Span]:
        rpr = r.find(T_RPR)
        f = base.copy()
        vanish = False
        if rpr is not None:
            props = _rpr_props(rpr)
            rs = rpr.find("w:rStyle", NS)
            cst = self.styles.resolve(rs.get(VAL)) if rs is not None else None
            b = props.get("bold")
            i = props.get("italic")
            s = props.get("strike")
            mono = props.get("mono")
            if b is None and cst is not None:
                b = cst.bold
            if i is None and cst is not None:
                i = cst.italic
            if mono is None and cst is not None and cst.mono:
                mono = True
            if cst is not None and _CODE_RSTYLES.search(cst.name or ""):
                mono = True
            if b is None:
                b = pst.bold
            if i is None:
                i = pst.italic
            f.bold = f.bold or bool(b)
            f.italic = f.italic or bool(i)
            f.strike = f.strike or bool(s if s is not None else False)
            f.code = f.code or bool(mono)
            va = rpr.find("w:vertAlign", NS)
            if va is not None:
                f.sup = va.get(VAL) == "superscript"
                f.sub = va.get(VAL) == "subscript"
            v = rpr.find("w:vanish", NS)
            vanish = _is_on(v) is True
        else:
            f.bold = f.bold or bool(pst.bold)
            f.italic = f.italic or bool(pst.italic)
            f.code = f.code or bool(pst.mono)
        if base.dele:
            f.dele = True
        out: List[Span] = []
        run_size = float(_rpr_props(rpr).get("size", 0) or 0) if rpr is not None else 0.0
        if not run_size and rpr is not None:
            rs2 = rpr.find("w:rStyle", NS)
            if rs2 is not None:
                run_size = float(self.styles.resolve(rs2.get(VAL)).size or 0)
        run_size = run_size or float(pst.size or 0) or self.styles.default_size

        def text_span(txt: str) -> None:
            if txt:
                out.append(Span("t", txt, f.copy(), size=run_size))
                for cid in self._open_ranges:
                    self.cm_anchor.setdefault(cid, []).append(txt)

        for c in r:
            tag = c.tag
            if tag == T_T or (tag == W("delText") and f.dele):
                if not vanish:
                    text_span(c.text or "")
            elif tag == W("tab") or tag == W("ptab"):
                text_span(" ")
            elif tag in (W("br"), W("cr")):
                if c.get(W("type"), "textWrapping") == "textWrapping":
                    out.append(Span("br"))
            elif tag == W("noBreakHyphen"):
                text_span("-")
            elif tag == W("sym"):
                ch = (c.get(W("char"), "") or "").upper()
                text_span(_SYM.get(ch, ""))
            elif tag == W("footnoteReference") or tag == W("endnoteReference"):
                kind = "fn" if tag == W("footnoteReference") else "en"
                out.append(Span("fn", c.get(W("id"), ""), Fmt(), display=(kind == "en")))
            elif tag == W("commentReference"):
                out.append(Span("cm", c.get(W("id"), "")))
            elif tag == W("fldChar"):
                out.extend(self._fld_char(c.get(W("fldCharType"), ""), f))
            elif tag == W("instrText"):
                if self.field_stack and self.field_stack[-1]["phase"] == "instr":
                    self.field_stack[-1]["instr"] += c.text or ""  # type: ignore[operator]
            elif tag in (W("drawing"), W("pict"), W("object")):
                out.extend(self._drawing(c, f))
            elif tag == "{%s}AlternateContent" % NS["mc"]:
                choice = c.find("mc:Choice", NS)
                pick = choice if choice is not None else c.find("mc:Fallback", NS)
                if pick is not None:
                    wrapper = ET.Element(T_R)
                    wrapper.extend(list(pick))
                    if rpr is not None:
                        wrapper.insert(0, rpr)
                    out.extend(self.text_run(wrapper, pst, base))
            elif tag == W("footnoteRef") or tag == W("endnoteRef") or tag == W("annotationRef"):
                continue
            elif tag == W("separator") or tag == W("continuationSeparator"):
                continue
        # champs : les segments produits pendant la phase « instruction » sont ignorés
        if self.field_stack:
            top = self.field_stack[-1]
            if top["phase"] == "instr":
                return [s for s in out if s.kind == "fld-marker"]
            top["spans"].extend(out)  # type: ignore[union-attr]
            return []
        return out

    # -- champs ------------------------------------------------------------
    def _fld_char(self, kind: str, f: Fmt) -> List[Span]:
        if kind == "begin":
            self.field_stack.append({"instr": "", "phase": "instr", "spans": [], "toc": False})
            return []
        if kind == "separate" and self.field_stack:
            top = self.field_stack[-1]
            top["phase"] = "result"
            instr = str(top["instr"]).strip()
            if re.match(r"(?i)^(TOC|INDEX|TOA)\b", instr) and not self.opts.keep_toc:
                top["toc"] = True
                self.skip_toc_depth += 1
            return []
        if kind == "end" and self.field_stack:
            top = self.field_stack.pop()
            if top.get("toc"):
                self.skip_toc_depth = max(0, self.skip_toc_depth - 1)
                return []
            spans = self._apply_field(str(top["instr"]), top["spans"], f)  # type: ignore[arg-type]
            if self.field_stack:  # champ imbriqué : le résultat remonte dans le champ parent
                if self.field_stack[-1]["phase"] == "result":
                    self.field_stack[-1]["spans"].extend(spans)  # type: ignore[union-attr]
                return []
            return spans
        return []

    def _apply_field(self, instr: str, spans: List[Span], f: Fmt) -> List[Span]:
        instr = instr.strip()
        m = re.match(r'(?i)^HYPERLINK\s+(?:\\l\s+)?"?([^"\s]+)"?', instr)
        if m and "\\l" not in instr.lower().split(m.group(1))[0]:
            url = m.group(1)
            return [Span(s.kind, s.text, s.fmt.copy(link=url), s.display) if s.kind == "t" else s for s in spans]
        if re.match(r"(?i)^(PAGE|NUMPAGES|SECTIONPAGES|PAGEREF|NOTEREF)\b", instr):
            return [] if re.match(r"(?i)^(PAGE|NUMPAGES|SECTIONPAGES)\b", instr) else spans
        if re.match(r"(?i)^(FORMCHECKBOX)\b", instr):
            return [Span("raw", "☐")]
        return spans

    # -- images, graphiques, zones de texte -------------------------------
    def _ole(self, el: ET.Element) -> List[Span]:
        """Objet incorporé (feuille Excel, document…) : fichier extrait en annexe, à convertir à part."""
        out: List[Span] = []
        for ole in el.iter():
            if local(ole.tag) != "OLEObject":
                continue
            tgt = self.rels.target(ole.get(R("id")))
            data = self.zf.read_opt(tgt) if tgt else None
            if not data:
                continue
            name = tgt.rsplit("/", 1)[-1]
            link = self.ctx.add_file(name, data)
            out.append(Span("raw", f"[objet incorporé : {name}]({link})"))
            self.ctx.warn(f"objet incorporé « {name} » extrait dans les annexes (non converti : relancer to-markdown dessus s'il compte)")
        return out

    def _drawing(self, el: ET.Element, f: Fmt) -> List[Span]:
        out: List[Span] = []
        if el.tag == W("object"):
            out.extend(self._ole(el))
        for blip in el.iter(A("blip")):
            rid = blip.get(R("embed")) or blip.get(R("link"))
            alt = ""
            for anc_tag in ("docPr",):
                d = el.find(".//{%s}docPr" % NS["wp"])
                if d is not None:
                    alt = d.get("descr") or d.get("title") or ""
                    if not alt:
                        nm = d.get("name", "")
                        alt = "" if re.match(r"(?i)^(picture|image|graphic|figure|objet|zone de texte|text box)\s*\d*$", nm) else nm
            out.append(self._image(rid, alt))
            break
        else:
            for im in el.iter("{%s}imagedata" % NS["v"]):
                rid = im.get(R("id"))
                alt = im.get("title") or ""
                out.append(self._image(rid, alt))
        for ch in el.iter(C("chart")):
            rid = ch.get(R("id"))
            tgt = self.rels.target(rid)
            croot = load_xml(self.zf, tgt) if tgt else None
            if croot is not None:
                info = parse_chart(croot)
                self.src_parts.append(chart_source_text(info))
                out.append(Span("block", chart_markdown(info, self.opts.table_rows)))
        for rel in el.iter("{%s}relIds" % NS["dgm"]):
            tgt = self.rels.target(rel.get(R("dm")))
            if tgt:
                lines = smartart_outline(self.zf, tgt)
                if lines:
                    out.append(Span("block", "\n".join(lines)))
        for tb in el.iter(W("txbxContent")):
            blocks = self.blocks_of(tb)
            if blocks:
                inner = self.assemble(blocks)
                out.append(Span("block", "\n".join(("> " + ln) if ln.strip() else ">" for ln in inner.split("\n"))))
        return [s for s in out if s is not None]

    def _image(self, rid: Optional[str], alt: str) -> Span:
        alt = alt_clean(alt)
        if rid is None:
            return Span("raw", "")
        if self.rels.is_external(rid):
            url = self.rels.target(rid) or ""
            return Span("raw", f"![{alt}]({md_url(url)})" if url else "")
        tgt = self.rels.target(rid)
        data = self.zf.read_opt(tgt) if tgt else None
        if data is None:
            return Span("raw", "")
        ext = (tgt or "").rsplit(".", 1)[-1] if tgt and "." in tgt else ""
        link = self.ctx.add_asset(data, ext, stem="img", alt=alt)
        if link is None:
            return Span("raw", f"*[image : {alt}]*" if alt and self.opts.images == "skip" else "")
        if ext.lower() in ("emf", "wmf"):
            self.ctx.warn(f"image {ext.upper()} non affichable telle quelle ({link})")
        return Span("raw", f"![{alt}]({link})")

    # -- rendu inline -----------------------------------------------------
    def render_spans(self, spans: List[Span], inline_only: bool = False) -> str:
        return render_spans(spans, inline_only, self._note_ref, self._comment_ref)

    # -- notes et commentaires ---------------------------------------------
    def _note_ref(self, nid: str, endnote: bool) -> str:
        store, order, prefix = (self.endnote_defs, self.en_order, "e") if endnote else (self.footnote_defs, self.fn_order, "")
        if nid not in store:
            return ""
        if nid not in order:
            order.append(nid)
        return f"[^{prefix}{order.index(nid) + 1}]"

    def _comment_ref(self, cid: str) -> str:
        if not self.opts.comments or cid not in self.comments:
            return ""
        if self.comments[cid].get("parent"):  # une réponse est rattachée à son commentaire parent
            return ""
        if cid not in self.cm_order:
            self.cm_order.append(cid)
        return f"[^c{self.cm_order.index(cid) + 1}]"

    def _note_text(self, el: ET.Element) -> str:
        saved = (self.in_note, self._open_ranges, self.field_stack)
        self.in_note, self._open_ranges, self.field_stack = True, [], []
        try:
            blocks = self.blocks_of(el)
        finally:
            self.in_note, self._open_ranges, self.field_stack = saved
        texts = []
        for b in blocks:
            if b.kind in ("p", "li", "quote", "h"):
                texts.append(b.text)
            elif b.kind == "code":
                texts.append("`" + " ".join(b.lines).strip() + "`")
            elif b.kind == "raw":
                texts.append(b.text.replace("\n", " "))
        return " ".join(t.strip() for t in texts if t.strip())

    def render_notes(self) -> str:
        lines: List[str] = []
        # les notes peuvent en référencer d'autres : boucle jusqu'à stabilité
        done_fn, done_en = 0, 0
        while done_fn < len(self.fn_order) or done_en < len(self.en_order):
            while done_fn < len(self.fn_order):
                nid = self.fn_order[done_fn]
                lines.append(f"[^{done_fn + 1}]: " + (self._note_text(self.footnote_defs[nid]) or "…"))
                done_fn += 1
            while done_en < len(self.en_order):
                nid = self.en_order[done_en]
                lines.append(f"[^e{done_en + 1}]: " + (self._note_text(self.endnote_defs[nid]) or "…"))
                done_en += 1
        if self.opts.comments and self.cm_order:
            replies: Dict[str, List[str]] = {}
            for cid, info in self.comments.items():
                parent = info.get("parent")
                if parent:
                    replies.setdefault(str(parent), []).append(cid)
            for k, cid in enumerate(self.cm_order, 1):
                info = self.comments[cid]
                anchor = re.sub(r"\s+", " ", "".join(self.cm_anchor.get(cid, []))).strip()
                if len(anchor) > 120:
                    anchor = anchor[:117] + "…"
                text = self._note_text(info["el"])  # type: ignore[arg-type]
                who = " ".join(x for x in (str(info["author"]), f"({info['date']})" if info["date"] else "") if x)
                head = f"**{esc_inline(who)}**" if who else "**Commentaire**"
                on = f" sur « {esc_inline(anchor)} »" if anchor else ""
                line = f"[^c{k}]: {head}{on} : {text}"
                for rid in replies.get(cid, []):
                    r = self.comments[rid]
                    line += f" — *réponse de {esc_inline(str(r['author']))}* : {self._note_text(r['el'])}"  # type: ignore[arg-type]
                lines.append(line)
        return "\n".join(lines)

    # -- tableaux ---------------------------------------------------------
    def table(self, tbl: ET.Element) -> List[Block]:
        grid: List[List[Optional[Tuple[str, bool]]]] = []
        vspans: Dict[int, str] = {}
        rows_xml = self._collect(tbl, T_TR)
        for tr in rows_xml:
            if self.opts.track_changes == "accept" and tr.find("w:trPr/w:del", NS) is not None:
                continue
            row: List[str] = []
            col = 0
            for tc in self._collect(tr, T_TC):
                tcpr = tc.find("w:tcPr", NS)
                span = 1
                vm = None
                if tcpr is not None:
                    gs = tcpr.find("w:gridSpan", NS)
                    if gs is not None and gs.get(VAL, "").isdigit():
                        span = max(1, int(gs.get(VAL)))
                    v = tcpr.find("w:vMerge", NS)
                    if v is not None:
                        vm = v.get(VAL, "continue")
                content = self._cell_text(tc)
                if vm == "continue":
                    content = vspans.get(col, content)
                elif vm == "restart":
                    vspans[col] = content
                else:
                    vspans.pop(col, None)
                row.append(content)
                row.extend([""] * (span - 1))
                col += span
            grid.append(row)  # type: ignore[arg-type]
        grid_s = [[c if isinstance(c, str) else "" for c in r] for r in grid]  # type: ignore[union-attr]
        if not grid_s:
            return []
        if len(grid_s) == 1 and len(grid_s[0]) == 1:  # encadré : tableau 1×1 → citation
            inner = grid_s[0][0].replace("<br>", "\n").strip()
            return [Block("raw", text="\n".join(("> " + ln) if ln.strip() else ">" for ln in inner.split("\n")))] if inner else []
        if len(grid_s) > 1 and self._two_level_header(grid_s):
            top, second = grid_s[0], grid_s[1]
            filled, last = [], ""
            for c in top:
                last = c or last
                filled.append(last)
            head = [(f"{a} {b}".strip() if b and a != b else (b or a)) for a, b in zip(filled, second)]
            grid_s = [head] + grid_s[2:]
        cap = self.opts.table_rows
        if cap and len(grid_s) - 1 > cap:
            extra = len(grid_s) - 1 - cap
            width = max(len(r) for r in grid_s)
            grid_s = grid_s[: cap + 1] + [[f"… ({extra} lignes de plus)"] + [""] * (width - 1)]
        return [Block("raw", text=md_table(grid_s))]

    @staticmethod
    def _two_level_header(grid: List[List[str]]) -> bool:
        top, second = grid[0], grid[1]
        if len(top) != len(second) or len(top) < 3:
            return False
        empties = sum(1 for c in top if not c.strip())
        return empties >= 1 and all(c.strip() for c in second) and any(c.strip() for c in top)

    def _collect(self, parent: ET.Element, wanted: str) -> List[ET.Element]:
        """Lignes (ou cellules) enfants, y compris celles enveloppées par sdt/customXml/ins."""
        out: List[ET.Element] = []
        for c in parent:
            if c.tag == wanted:
                out.append(c)
            elif c.tag == W("sdt"):
                content = c.find("w:sdtContent", NS)
                if content is not None:
                    out.extend(self._collect(content, wanted))
            elif c.tag in (W("customXml"), W("ins"), W("moveTo"), W("smartTag")):
                out.extend(self._collect(c, wanted))
        return out

    def _cell_text(self, tc: ET.Element) -> str:
        parts: List[str] = []
        for b in self.blocks_of(tc):
            if b.kind in ("p", "h", "quote"):
                parts.append(b.text)
            elif b.kind == "li":
                lab = "•" if b.marker == "bullet" else (b.label + "." if b.marker == "ord" else b.label)
                parts.append(f"{lab} {b.text}")
            elif b.kind == "code":
                parts.append("`" + " ".join(l.strip() for l in b.lines) + "`")
            elif b.kind == "raw":
                t = b.text
                if t.startswith("|"):  # tableau imbriqué : ses cellules, à la suite
                    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in t.split("\n")
                            if not re.match(r"^\|\s*-{3}", ln)]
                    parts.append("; ".join(" / ".join(c for c in r if c) for r in rows))
                else:
                    parts.append(t.replace("\n", "<br>"))
        return "<br>".join(p for p in parts if p and p.strip())

    # -- titres déduits de la mise en forme --------------------------------
    def _infer_headings(self, blocks: List[Block]) -> None:
        """Documents sans styles de titre : repère les lignes courtes plus grosses / en gras."""
        if not self.opts.infer_headings or self.headings_seen or any(b.kind == "h" for b in blocks):
            return
        paras = [b for b in blocks if b.kind == "p" and b.size]
        if len(paras) < 5:
            return
        weight: Dict[float, int] = {}
        for b in paras:
            weight[b.size] = weight.get(b.size, 0) + len(b.text)
        body = max(weight.items(), key=lambda kv: kv[1])[0]
        numbered = re.compile(r"^(\*\*|_)?(\d+(\.\d+)*[.)]?|[IVXLC]+[.)]|[A-Z][.)])\s+\S")

        def is_cand(b: Block) -> bool:
            plain = re.sub(r"[*_`\\]", "", b.text).strip()
            if not plain or len(plain) > 120 or "\n" in b.text:
                return False
            if plain.endswith((".", ";", ",")) and len(plain) > 40:
                return False
            if b.size >= body + 2:
                return True
            if b.bold and b.size >= body:
                return len(plain) <= 70 and (bool(numbered.match(b.text)) or not plain.endswith(":") or plain.isupper())
            return False

        cands = [b for b in paras if is_cand(b)]
        if not cands or len(cands) > 0.35 * len(paras):
            return
        sigs = sorted({(b.size, b.bold) for b in cands}, key=lambda t: (-t[0], not t[1]))
        level = {sig: min(i + 1, 4) for i, sig in enumerate(sigs)}
        for b in cands:
            b.kind, b.level = "h", level[(b.size, b.bold)]
            b.text = re.sub(r"^(\*\*|_|\*)+(.*?)(\*\*|_|\*)+$", r"\2", b.text.strip())
        self.ctx.warn(f"{len(cands)} titre(s) déduit(s) de la mise en forme (le document n'utilise pas de styles de titre)")

    # -- assemblage -------------------------------------------------------
    def assemble(self, blocks: List[Block]) -> str:
        shift = 1 if any(b.kind == "h" and b.marker == "title" for b in blocks) and any(
            b.kind == "h" and b.marker != "title" for b in blocks) else 0
        out: List[str] = []
        i = 0
        n = len(blocks)
        while i < n:
            b = blocks[i]
            if b.kind == "h":
                lvl = min(6, (b.level + shift) if b.marker != "title" else 1)
                out.append("#" * lvl + " " + b.text)
                i += 1
            elif b.kind == "li":
                lines: List[str] = []
                stack: List[int] = []
                while i < n and blocks[i].kind == "li":
                    it = blocks[i]
                    lvl = it.level
                    del stack[lvl:]
                    while len(stack) < lvl:
                        stack.append(2)
                    marker = {"bullet": "-", "ord": f"{it.label}.", "label": "-"}[it.marker]
                    body = f"{it.label} {it.text}" if it.marker == "label" else it.text
                    lines.append(" " * sum(stack) + f"{marker} {body}")
                    stack.append(len(marker) + 1)
                    i += 1
                out.append("\n".join(lines))
            elif b.kind == "code":
                code: List[str] = []
                while i < n and blocks[i].kind == "code":
                    code.extend(blocks[i].lines)
                    i += 1
                out.append(fence("\n".join(code)))
            elif b.kind == "quote":
                q: List[str] = []
                while i < n and blocks[i].kind == "quote":
                    q.extend(("> " + ln) if ln else ">" for ln in blocks[i].text.split("\n"))
                    i += 1
                out.append("\n".join(q))
            elif b.kind in ("p", "raw"):
                out.append(b.text)
                i += 1
            else:
                i += 1
        return "\n\n".join(x for x in out if x and x.strip())


def _main_part(zf: SafeZip) -> str:
    rels = Rels(zf, "")
    for _rid, tgt in rels.of_type("officeDocument"):
        if zf.has(tgt):
            return zf.resolve(tgt) or tgt
    if zf.has("word/document.xml"):
        return "word/document.xml"
    raise Unsupported("aucune partie principale Word trouvée")


@engine("docx", name="native", prio=10)
def docx_native(path, ctx: Ctx) -> Result:
    with SafeZip(path) as zf:
        conv = DocxConverter(zf, ctx, _main_part(zf))
        res = conv.run()
        if "word/vbaProject.bin" in [n.lower() for n in zf.names()]:
            ctx.warn("le document contient des macros VBA (ignorées, jamais exécutées)")
        return res
