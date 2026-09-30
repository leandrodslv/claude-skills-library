"""XLSX → Markdown, en bibliothèque standard, lecture en flux (mémoire bornée).

Une section par feuille ; les blocs de données séparés par des lignes vides
deviennent des tableaux distincts ; dates, pourcentages et booléens sont
rendus lisiblement ; cellules fusionnées, liens, commentaires et graphiques
sont repris ; une grande feuille est tronquée dans le Markdown mais fournie
en entier dans un CSV annexe.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from .core import Ctx, Result, Unsupported, engine
from .grid import grid_blocks
from .inline import md_url
from .ooxml import (NS, C, chart_markdown, chart_source_text, core_props, load_xml, parse_chart)
from .util import Rels, SafeZip, UnsafeXML, clean_text, esc_inline, local, slugify

SS = NS["x"]
T = lambda tag: "{%s}%s" % (SS, tag)  # noqa: E731
_STRICT_SS = b"http://purl.oclc.org/ooxml/spreadsheetml/main"
MAX_CELLS = 3_000_000

_BUILTIN_FMT = {
    0: "General", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00", 9: "0%", 10: "0.00%", 11: "0.00E+00",
    12: "# ?/?", 13: "# ??/??", 14: "yyyy-mm-dd", 15: "d-mmm-yy", 16: "d-mmm", 17: "mmm-yy", 18: "h:mm AM/PM",
    19: "h:mm:ss AM/PM", 20: "h:mm", 21: "h:mm:ss", 22: "yyyy-mm-dd h:mm", 37: "#,##0 ;(#,##0)",
    38: "#,##0 ;[Red](#,##0)", 39: "#,##0.00;(#,##0.00)", 40: "#,##0.00;[Red](#,##0.00)", 45: "mm:ss",
    46: "[h]:mm:ss", 47: "mmss.0", 48: "##0.0E+0", 49: "@",
}
_DATE_IDS = set(range(14, 18)) | set(range(27, 37)) | set(range(50, 59)) | {22}
_TIME_IDS = {18, 19, 20, 21, 45, 46, 47}


def col_index(ref: str) -> Tuple[int, int]:
    """« AB12 » → (ligne 12, colonne 28), indices à partir de 1."""
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    if not m:
        return 0, 0
    col = 0
    for ch in m.group(1).upper():
        col = col * 26 + (ord(ch) - 64)
    return int(m.group(2)), col


def col_letters(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def classify_format(code: str, fid: int) -> Tuple[str, int]:
    """(catégorie, décimales) d'un format : date | time | datetime | percent | number | text."""
    if fid in _DATE_IDS and fid not in _BUILTIN_FMT:
        return "date", 0
    if fid in _TIME_IDS and code == "":
        return "time", 0
    c = code or _BUILTIN_FMT.get(fid, "General")
    if c in ("General", "@"):
        return ("text" if c == "@" else "number"), 0
    stripped = re.sub(r'"[^"]*"|\\.|_.|\*.|\[(?![hms]+\])[^\]]*\]', "", c.split(";")[0])
    low = stripped.lower()
    has_date = "y" in low or "d" in low or ("m" in low and "h" not in low and "s" not in low and "[" not in low)
    has_time = "h" in low or "s" in low or bool(re.search(r"\[h+\]|\[m+\]|\[s+\]", low))
    if has_date and has_time:
        return "datetime", 0
    if has_date:
        return "date", 0
    if has_time:
        return "time", 0
    if "%" in stripped:
        m = re.search(r"\.(0+)", stripped)
        return "percent", len(m.group(1)) if m else 0
    return "number", 0


def excel_date(serial: float, date1904: bool) -> Optional[dt.datetime]:
    try:
        if date1904:
            return dt.datetime(1904, 1, 1) + dt.timedelta(days=serial)
        base = dt.datetime(1899, 12, 30) if serial >= 61 else dt.datetime(1899, 12, 31)
        return base + dt.timedelta(days=serial)
    except (OverflowError, ValueError):
        return None


def clean_number(v: str) -> str:
    try:
        f = float(v)
    except ValueError:
        return v
    if f != f or f in (float("inf"), float("-inf")):
        return v
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return format(f, ".15g")


class XlsxConverter:
    def __init__(self, zf: SafeZip, ctx: Ctx):
        self.zf, self.ctx, self.opts = zf, ctx, ctx.opts
        self.main = "xl/workbook.xml"
        self.strings: List[str] = []
        self.kinds: List[Tuple[str, int]] = []
        self.date1904 = False
        self.string_src: List[str] = []
        self.truncated = False
        self.formulas_missing = 0
        self.sheet_parts: Dict[str, str] = {}

    # -- chargement --------------------------------------------------------
    def _root(self, name: str) -> Optional[ET.Element]:
        return load_xml(self.zf, name)

    def _iter(self, part: str):
        """iterparse sur une partie (fin de balise), sans construire l'arbre complet."""
        data = self.zf.read(part)
        if b"<!ENTITY" in data:
            raise UnsafeXML("entité XML refusée")
        if _STRICT_SS in data[:2048]:
            data = data.replace(_STRICT_SS, SS.encode())
        return ET.iterparse(io.BytesIO(data), events=("end",))

    def load_strings(self) -> None:
        part = "xl/sharedStrings.xml"
        if not self.zf.has(part):
            return
        for _ev, el in self._iter(part):
            if el.tag == T("si"):
                parts = []
                for t in el.iter(T("t")):
                    # ignore les annotations phonétiques <rPh>
                    parts.append(t.text or "")
                # <rPh> imbriqués : on retire leur texte
                ph = "".join((t.text or "") for rph in el.iter(T("rPh")) for t in rph.iter(T("t")))
                txt = "".join(parts)
                if ph and txt.endswith(ph):
                    txt = txt[: -len(ph)]
                self.strings.append(clean_text(txt))
                el.clear()

    def load_styles(self) -> None:
        root = self._root("xl/styles.xml")
        if root is None:
            return
        custom: Dict[int, str] = {}
        for nf in root.iter(T("numFmt")):
            try:
                custom[int(nf.get("numFmtId", "-1"))] = nf.get("formatCode", "")
            except ValueError:
                pass
        cx = root.find("x:cellXfs", NS)
        if cx is None:
            return
        for xf in cx.findall("x:xf", NS):
            try:
                fid = int(xf.get("numFmtId", "0"))
            except ValueError:
                fid = 0
            self.kinds.append(classify_format(custom.get(fid, ""), fid))

    # -- classeur -----------------------------------------------------------
    def run(self) -> Result:
        wb = self._root(self.main)
        if wb is None:
            raise Unsupported("workbook.xml illisible")
        pr = wb.find("x:workbookPr", NS)
        self.date1904 = pr is not None and pr.get("date1904") in ("1", "true")
        rels = Rels(self.zf, self.main)
        self.load_strings()
        self.load_styles()
        sheets = []
        for sh in wb.findall("x:sheets/x:sheet", NS):
            rid = sh.get("{%s}id" % NS["r"])
            part = rels.target(rid)
            if part and self.zf.has(part):
                sheets.append((sh.get("name", "Feuille"), part, sh.get("state", "visible"), rels.type(rid)))
                self.sheet_parts[sh.get("name", "Feuille")] = part
        blocks: List[str] = []
        rendered = hidden = 0
        for name, part, state, typ in sheets:
            if state != "visible":
                hidden += 1
                if not self.opts.hidden:
                    continue
            if typ == "chartsheet":
                md = self.chartsheet(name, part, state)
            else:
                md = self.sheet(name, part, state)
            blocks.append(md)
            rendered += 1
        props = core_props(self.zf)
        md = "\n\n".join(b for b in blocks if b.strip())
        res = Result(markdown=md, fmt="xlsx", engine="native", title=props.get("title", ""), meta=dict(props))
        res.units, res.unit_name = len(sheets) if self.opts.hidden else len(sheets) - hidden, "feuille"
        res.units_found = len(re.findall(r"(?m)^## ", md))
        res.source_text = None if self.truncated else "\n".join(self.string_src)
        res.stats["partial_source"] = True  # seules les cellules texte sont comptées, pas les nombres
        if hidden:
            self.ctx.warn(f"{hidden} feuille(s) masquée(s)" + (" (incluses, signalées)" if self.opts.hidden else " (ignorées)"))
        if self.formulas_missing:
            self.ctx.warn(f"{self.formulas_missing} formule(s) sans valeur en cache (classeur jamais recalculé) : formule affichée")
        return res

    # -- feuille -----------------------------------------------------------
    def sheet(self, name: str, part: str, state: str) -> str:
        rels = Rels(self.zf, part)
        rows: Dict[int, Dict[int, str]] = {}
        merges: List[Tuple[int, int, int, int]] = []
        links: Dict[Tuple[int, int], str] = {}
        drawing_rid = None
        n_cells = 0
        total_rows = 0
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf, lineterminator="\n")
        keep_csv = True
        last_csv_row = 0
        for _ev, el in self._iter(part):
            tag = el.tag
            if tag == T("row"):
                r_idx = int(el.get("r", "0") or 0) or (max(rows) + 1 if rows else 1)
                cells: Dict[int, str] = {}
                for c in el.findall("x:c", NS):
                    ref = c.get("r", "")
                    r_i, c_i = col_index(ref) if ref else (r_idx, len(cells) + 1)
                    text = self.cell_value(c)
                    if text != "":
                        cells[c_i or (len(cells) + 1)] = text
                if cells:
                    total_rows += 1
                    n_cells += len(cells)
                    if n_cells <= MAX_CELLS:
                        rows[r_idx] = cells
                    else:
                        self.truncated = True
                    if keep_csv:
                        while last_csv_row + 1 < r_idx and r_idx - last_csv_row < 5000:
                            writer.writerow([])
                            last_csv_row += 1
                        width = max(cells)
                        writer.writerow([cells.get(i, "") for i in range(1, width + 1)])
                        last_csv_row = r_idx
                        if csv_buf.tell() > 200 << 20:
                            keep_csv = False
                el.clear()
            elif tag == T("mergeCell"):
                a, _, b = (el.get("ref") or "").partition(":")
                if b:
                    (r0, c0), (r1, c1) = col_index(a), col_index(b)
                    merges.append((r0, c0, r1, c1))
            elif tag == T("hyperlink"):
                ref, rid = el.get("ref", ""), el.get("{%s}id" % NS["r"])
                if rid and rels.is_external(rid):
                    url = rels.target(rid) or ""
                    a, _, b = ref.partition(":")
                    (r0, c0), (r1, c1) = col_index(a), col_index(b or a)
                    if (r1 - r0 + 1) * (c1 - c0 + 1) <= 2000:
                        for rr in range(r0, r1 + 1):
                            for cc in range(c0, c1 + 1):
                                links[(rr, cc)] = url
            elif tag == T("drawing"):
                drawing_rid = el.get("{%s}id" % NS["r"])
        if merges:
            self.apply_merges(rows, merges)
        for (rr, cc), url in links.items():
            v = rows.get(rr, {}).get(cc)
            if v and url:
                rows[rr][cc] = f"[{v}]({md_url(url)})" if not v.startswith("[") else v
        head = f"## {esc_inline(name)}" + (" *(masquée)*" if state != "visible" else "")
        parts = [head]
        if not rows:
            parts.append("_(feuille vide)_")
        else:
            parts.extend(self.blocks(rows, name, csv_buf.getvalue() if keep_csv else "", total_rows))
        # graphiques, images, commentaires
        if drawing_rid and rels.target(drawing_rid):
            parts.extend(self.drawing(rels.target(drawing_rid), name))
        if self.opts.comments:
            cm = self.comments(rels)
            if cm:
                parts.append("**Commentaires :**\n\n" + "\n".join(f"- {c}" for c in cm))
        return "\n\n".join(p for p in parts if p.strip())

    def apply_merges(self, rows: Dict[int, Dict[int, str]], merges: List[Tuple[int, int, int, int]]) -> None:
        for r0, c0, r1, c1 in merges:
            if (r1 - r0 + 1) * (c1 - c0 + 1) > 20000:
                continue
            val = rows.get(r0, {}).get(c0)
            if val is None:
                continue
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if (r, c) == (r0, c0):
                        continue
                    if c == c0 and r > r0:  # fusion verticale : la valeur est répétée vers le bas
                        rows.setdefault(r, {})[c] = val

    def cell_value(self, c: ET.Element) -> str:
        t = c.get("t", "n")
        v = c.find("x:v", NS)
        f = c.find("x:f", NS)
        raw = v.text if v is not None and v.text is not None else None
        if t == "inlineStr":
            is_ = c.find("x:is", NS)
            txt = clean_text("".join((x.text or "") for x in is_.iter(T("t")))) if is_ is not None else ""
            if txt:
                self.string_src.append(txt)
            return txt
        if raw is None:
            if f is not None and (f.text or "").strip():
                self.formulas_missing += 1
                return "=" + f.text.strip()
            return ""
        if t == "s":
            try:
                txt = self.strings[int(raw)]
            except (ValueError, IndexError):
                return ""
            if txt:
                self.string_src.append(txt)
            out = txt
        elif t == "str":
            out = clean_text(raw)
            if out:
                self.string_src.append(out)
        elif t == "b":
            out = "TRUE" if raw.strip() in ("1", "true") else "FALSE"
        elif t == "e":
            out = raw
        elif t == "d":
            out = raw
        else:
            out = self.number(raw, int(c.get("s", "0") or 0))
        if f is not None and self.opts.formulas and (f.text or "").strip():
            out = f"{out} (={f.text.strip()})"
        return esc_cell_text(out) if t in ("s", "str", "inlineStr") else out

    def number(self, raw: str, style: int) -> str:
        kind, dec = self.kinds[style] if 0 <= style < len(self.kinds) else ("number", 0)
        try:
            f = float(raw)
        except ValueError:
            return raw
        if kind in ("date", "time", "datetime"):
            d = excel_date(f, self.date1904)
            if d is not None:
                d = (d + dt.timedelta(milliseconds=500)).replace(microsecond=0)  # bruit de virgule flottante
            if d is not None and 0 <= f < 2958466:
                if kind == "time" or (kind == "datetime" and f < 1):
                    return d.strftime("%H:%M:%S") if d.second else d.strftime("%H:%M")
                if kind == "date":
                    return d.strftime("%Y-%m-%d")
                return d.strftime("%Y-%m-%d %H:%M:%S") if d.second else d.strftime("%Y-%m-%d %H:%M")
        if kind == "percent":
            return f"{f * 100:.{dec}f}%"
        return clean_number(raw)

    # -- blocs de données -------------------------------------------------
    def blocks(self, rows: Dict[int, Dict[int, str]], sheet: str, csv_text: str, total_rows: int) -> List[str]:
        out = grid_blocks(self.ctx, rows, sheet, csv_text, total_rows)
        if any(o.startswith("_Tableau tronqué") for o in out):
            self.truncated = True
        return out

    # -- dessins, graphiques, commentaires ------------------------------------
    def drawing(self, part: str, sheet: str) -> List[str]:
        root = load_xml(self.zf, part)
        if root is None:
            return []
        rels = Rels(self.zf, part)
        out: List[str] = []
        for ch in root.iter(C("chart")):
            tgt = rels.target(ch.get("{%s}id" % NS["r"]))
            croot = load_xml(self.zf, tgt) if tgt else None
            if croot is not None:
                info = parse_chart(croot, self.range_values)
                self.string_src.append(chart_source_text(info))
                out.append(chart_markdown(info, self.opts.table_rows))
        n = 0
        for blip in root.iter("{%s}blip" % NS["a"]):
            tgt = rels.target(blip.get("{%s}embed" % NS["r"]))
            data = self.zf.read_opt(tgt) if tgt else None
            if data:
                n += 1
                link = self.ctx.add_asset(data, tgt.rsplit(".", 1)[-1], stem=f"{slugify(sheet)}-img")
                if link:
                    out.append(f"![]({link})")
        for sp in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}sp"):
            txt = " ".join("".join(t.text or "" for t in p.iter("{%s}t" % NS["a"])) for p in sp.iter("{%s}p" % NS["a"])).strip()
            if txt:
                self.string_src.append(txt)
                out.append(f"> {esc_inline(clean_text(txt))}")
        return out

    def range_values(self, formula: str) -> Optional[List[str]]:
        """Valeurs d'une plage « 'Feuille 1'!$B$2:$B$9 » (graphiques sans cache de données)."""
        m = re.match(r"^\(?(?:'((?:[^']|'')+)'|([^'!]+))!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?\)?$", formula.strip())
        if not m:
            return None
        sheet = (m.group(1) or m.group(2)).replace("''", "'")
        part = self.sheet_parts.get(sheet)
        if not part:
            return None
        (r0, c0) = col_index(m.group(3) + m.group(4))
        (r1, c1) = col_index((m.group(5) or m.group(3)) + (m.group(6) or m.group(4)))
        out: List[str] = []
        for _ev, el in self._iter(part):
            if el.tag == T("row"):
                r = int(el.get("r", "0") or 0)
                if r > r1:
                    break
                if r0 <= r <= r1:
                    for c in el.findall("x:c", NS):
                        _r, ci = col_index(c.get("r", ""))
                        if c0 <= ci <= c1:
                            out.append(self.cell_value(c))
                el.clear()
        return out

    def chartsheet(self, name: str, part: str, state: str) -> str:
        rels = Rels(self.zf, part)
        parts = [f"## {esc_inline(name)}" + (" *(masquée)*" if state != "visible" else "")]
        for _rid, tgt in rels.of_type("drawing"):
            parts.extend(self.drawing(tgt, name))
        return "\n\n".join(parts)

    def comments(self, rels: Rels) -> List[str]:
        out: List[str] = []
        for _rid, tgt in rels.of_type("comments"):
            root = load_xml(self.zf, tgt)
            if root is None:
                continue
            authors = [a.text or "" for a in root.findall("x:authors/x:author", NS)]
            for cm in root.findall("x:commentList/x:comment", NS):
                txt = clean_text("".join((t.text or "") for t in cm.iter(T("t")))).strip()
                if not txt:
                    continue
                aid = cm.get("authorId", "")
                who = authors[int(aid)] if aid.isdigit() and int(aid) < len(authors) else ""
                txt = re.sub(r"^" + re.escape(who) + r":\s*", "", txt) if who else txt
                out.append(f"`{cm.get('ref', '')}`" + (f" ({esc_inline(who)})" if who else "") + f" : {esc_inline(txt)}")
                self.string_src.append(txt)
        for _rid, tgt in rels.of_type("threadedComment"):
            root = load_xml(self.zf, tgt)
            if root is None:
                continue
            for tc in root:
                if local(tc.tag) != "threadedComment":
                    continue
                t = next((c for c in tc if local(c.tag) == "text"), None)
                txt = clean_text(t.text or "").strip() if t is not None else ""
                if txt:
                    out.append(f"`{tc.get('ref', '')}` : {esc_inline(txt)}")
        return out


def esc_cell_text(s: str) -> str:
    """Texte de cellule → Markdown inline (les retours à la ligne et « | » sont traités par md_table)."""
    return esc_inline(s)


@engine(["xlsx"], name="native", prio=10)
def xlsx_native(path, ctx: Ctx) -> Result:
    with SafeZip(path) as zf:
        if not zf.has("xl/workbook.xml"):
            raise Unsupported("xl/workbook.xml introuvable")
        res = XlsxConverter(zf, ctx).run()
        if any(n.lower().endswith("vbaproject.bin") for n in zf.names()):
            ctx.warn("le classeur contient des macros VBA (ignorées, jamais exécutées)")
        return res
