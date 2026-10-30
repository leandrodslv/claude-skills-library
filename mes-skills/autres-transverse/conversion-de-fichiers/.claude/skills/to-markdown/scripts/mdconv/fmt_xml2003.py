"""Formats XML d'Office 2003 : « Feuille de calcul XML » (SpreadsheetML) et « Document Word XML » (WordprocessingML 2003).

Encore produits par d'anciens outils de reporting sous l'extension .xml ou .xls. Le tableur est lu directement ; le
document Word est converti en DOCX en mémoire (mêmes noms d'éléments, autre espace de noms) puis confié au convertisseur DOCX.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

from .core import Ctx, Result, Unsupported, engine
from .grid import grid_blocks
from .util import clean_text, esc_inline, local, parse_xml

SS = "urn:schemas-microsoft-com:office:spreadsheet"
W03 = "http://schemas.microsoft.com/office/word/2003/wordml"
W06 = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MAX_CELLS = 1_000_000


def _ss(tag: str) -> str:
    return "{%s}%s" % (SS, tag)


def _value(kind: str, text: str) -> str:
    text = text.strip()
    if kind == "DateTime":
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:T(\d{2}:\d{2})(?::\d{2})?)?", text)
        if m:
            return m.group(1) if not m.group(2) or m.group(2) == "00:00" else f"{m.group(1)} {m.group(2)}"
    if kind == "Boolean":
        return "TRUE" if text in ("1", "true", "TRUE") else "FALSE"
    if kind == "Number":
        try:
            f = float(text)
            return str(int(f)) if f == int(f) and abs(f) < 1e15 else format(f, ".15g")
        except ValueError:
            return text
    return esc_inline(clean_text(text))


@engine("xml2003-sheet", name="native", prio=10)
def spreadsheetml(path, ctx: Ctx) -> Result:
    root = parse_xml(Path(path).read_bytes())
    sheets = [w for w in root.iter(_ss("Worksheet"))]
    if not sheets:
        raise Unsupported("aucune feuille SpreadsheetML")
    blocks: List[str] = []
    strings: List[str] = []
    n_cells = 0
    for ws in sheets:
        name = ws.get(_ss("Name"), "Feuille")
        opts = next((c for c in ws if local(c.tag) == "WorksheetOptions"), None)
        hidden = opts is not None and any(local(v.tag) == "Visible" and (v.text or "").strip() in ("SheetHidden", "SheetVeryHidden") for v in opts.iter())
        if hidden and not ctx.opts.hidden:
            continue
        table = next((c for c in ws if local(c.tag) == "Table"), None)
        rows: Dict[int, Dict[int, str]] = {}
        fill_down: Dict[int, Dict[int, int]] = {}      # ligne → {colonne: lignes restantes à remplir}
        r_idx = 0
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        total = 0
        for row in (table if table is not None else []):
            if local(row.tag) != "Row":
                continue
            r_idx = int(row.get(_ss("Index"), 0) or 0) or r_idx + 1
            cells: Dict[int, str] = {}
            c_idx = 0
            for cell in row:
                if local(cell.tag) != "Cell":
                    continue
                c_idx = int(cell.get(_ss("Index"), 0) or 0) or c_idx + 1
                data = next((d for d in cell if local(d.tag) == "Data"), None)
                if data is not None:
                    text = _value(data.get(_ss("Type"), "String"), "".join(data.itertext()))
                    if text:
                        cells[c_idx] = text
                        if data.get(_ss("Type"), "String") == "String":
                            strings.append(text)
                        href = cell.get(_ss("HRef"))
                        if href and not href.startswith("#"):
                            cells[c_idx] = f"[{text}]({href})"
                down = int(cell.get(_ss("MergeDown"), 0) or 0)
                if down and c_idx in cells:
                    fill_down.setdefault(r_idx, {})[c_idx] = down
                c_idx += int(cell.get(_ss("MergeAcross"), 0) or 0)
            for prev_row, cols in list(fill_down.items()):
                if prev_row < r_idx:
                    for c, left in list(cols.items()):
                        if left > 0 and c not in cells and c in rows.get(prev_row, {}):
                            cells[c] = rows[prev_row][c]
                            cols[c] = left - 1
            if cells:
                total += 1
                n_cells += len(cells)
                if n_cells <= MAX_CELLS:
                    rows[r_idx] = cells
                writer.writerow([cells.get(i, "") for i in range(1, max(cells) + 1)])
        head = f"## {esc_inline(name)}" + (" *(masquée)*" if hidden else "")
        blocks.append("\n\n".join([head] + (grid_blocks(ctx, rows, name, buf.getvalue(), total) if rows else ["_(feuille vide)_"])))
    if not blocks:
        raise Unsupported("aucune feuille visible")
    md = "\n\n".join(blocks)
    res = Result(markdown=md, fmt="xml2003-sheet", engine="native", title=Path(path).stem)
    res.units, res.unit_name, res.units_found = len(blocks), "feuille", len(re.findall(r"(?m)^## ", md))
    res.source_text = "\n".join(strings)
    res.stats["partial_source"] = True
    return res


def _unwrap(el: ET.Element) -> None:
    """Remonte les enfants des conteneurs propres à WordML 2003 (« wx:sect », « wx:sub-section »…) dans leur parent."""
    i = 0
    while i < len(el):
        ch = el[i]
        _unwrap(ch)
        if ch.tag.startswith("{") and ch.tag[1:].split("}")[0] != W03 and any(g.tag.startswith("{%s}" % W03) for g in ch):
            kids = list(ch)
            el.remove(ch)
            for j, k in enumerate(kids):
                el.insert(i + j, k)
            i += len(kids)
        else:
            i += 1


@engine("xml2003-word", name="native", prio=10)
def wordml2003(path, ctx: Ctx) -> Result:
    from .fmt_docx import docx_native

    raw = Path(path).read_bytes()
    root = parse_xml(raw)
    if local(root.tag) != "wordDocument":
        raise Unsupported("racine WordML 2003 attendue")
    body = next((c for c in root if local(c.tag) == "body"), None)
    if body is None:
        raise Unsupported("corps WordML introuvable")
    _unwrap(body)
    styles = next((c for c in root if local(c.tag) == "styles"), None)

    def dump_styles(el: ET.Element) -> bytes:
        wrapper = ET.Element("{%s}styles" % W06)
        wrapper.extend(list(el))
        return ('<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(wrapper, encoding="unicode").replace(W03, W06)).encode("utf-8")

    document = ET.Element("{%s}document" % W06)
    document.append(_body_copy(body))
    doc_xml = ET.tostring(document, encoding="unicode").replace(W03, W06)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("word/document.xml", ('<?xml version="1.0" encoding="UTF-8"?>' + doc_xml).encode("utf-8"))
        if styles is not None:
            z.writestr("word/styles.xml", dump_styles(styles))
    tmp = Path(ctx.tmp) / (Path(path).stem + ".docx")
    tmp.write_bytes(mem.getvalue())
    res = docx_native(tmp, ctx)
    res.fmt = "xml2003-word"
    return res


def _body_copy(body: ET.Element) -> ET.Element:
    b = ET.Element("{%s}body" % W06)
    b.extend(list(body))
    return b
