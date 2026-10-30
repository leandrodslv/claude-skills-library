"""Mode secours pour Word / PowerPoint / Excel, OpenDocument (texte, tableur, présentation) et EPUB abîmés ou tronqués (téléchargement interrompu, XML cassé).

Dernier recours (priorité 90) : il ne travaille que si les lecteurs normaux ont échoué. Il ne cherche pas la
fidélité mais à **sauver le texte** : les membres du ZIP sont retrouvés en lisant les en-têtes locaux (l'annuaire
final peut manquer), chaque flux est décompressé aussi loin qu'il est lisible, puis le texte est extrait par
expressions régulières, sans analyse XML (qui échouerait sur un fichier coupé). Mise en forme, images et parties
manquantes sont perdues ; le résultat est toujours signalé « abîmé ».
"""
from __future__ import annotations

import html
import re
import struct
import zipfile
import zlib
from typing import Dict, List

from .core import Ctx, Result, Unsupported, engine
from .util import md_table, parse_xml

_MEMBER_CAP = 64 << 20      # octets décompressés par membre (garde-fou contre les bombes)
_MAX_MEMBERS = 5000
_LOCAL = b"PK\x03\x04"


def salvage_members(data: bytes) -> Dict[str, bytes]:
    """Membres d'un ZIP lisible en partie : nom → contenu (éventuellement coupé)."""
    out: Dict[str, bytes] = {}
    view = memoryview(data)
    pos = 0
    while len(out) < _MAX_MEMBERS:
        pos = data.find(_LOCAL, pos)
        if pos < 0 or pos + 30 > len(data):
            break
        _sig, _ver, flags, method, _t, _d, _crc, csize, _usize, nlen, xlen = struct.unpack("<4sHHHHHIIIHH", data[pos:pos + 30])
        name_end = pos + 30 + nlen
        start = name_end + xlen
        raw_name = data[pos + 30:name_end]
        try:
            name = raw_name.decode("utf-8" if flags & 0x800 else "cp437")
        except UnicodeDecodeError:
            name = raw_name.decode("latin-1")
        body = b""
        if method == 8:
            d = zlib.decompressobj(-15)
            parts: List[bytes] = []
            fed = total = 0
            try:
                while start + fed < len(data) and not d.eof and total < _MEMBER_CAP:     # par morceaux : pas de recopie de la fin du fichier
                    piece = d.decompress(view[start + fed:start + fed + 65536])
                    fed += 65536
                    total += len(piece)
                    parts.append(piece)
                body = b"".join(parts)
                consumed = min(fed, len(data) - start) - (len(d.unused_data) if d.eof else 0)
            except zlib.error:
                body = b"".join(parts)
                consumed = 0
        elif method == 0:
            size = csize if csize and not flags & 8 else len(data) - start
            body = data[start:start + size]
            consumed = len(body)
        else:
            consumed = 0
        if body and not name.endswith("/"):
            out.setdefault(name.replace("\\", "/"), body[:_MEMBER_CAP])
        pos = max(start + consumed, pos + 4)
    return out


def _intact(path, main: str) -> bool:
    """Le fichier s'ouvre normalement et sa partie principale est du XML valide (ou démesurée : une bombe n'est pas un fichier abîmé)."""
    try:
        with zipfile.ZipFile(path) as zf:
            info = zf.getinfo(main)
            if info.file_size > _MEMBER_CAP:
                return True
            parse_xml(zf.read(info))
        return True
    except Exception:
        return False


def _txt(frag: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", frag))


_INCOMPLETE = "⚠ [fin du fichier : paragraphe possiblement incomplet]"
_INCOMPLETE_ROW = "dernière ligne possiblement incomplète (fichier tronqué)"
_P_SPLIT = re.compile(r"(?s)<w:p[ >/].*?(?:</w:p>|$)")
_RUN_TOKENS = re.compile(r"(?s)<w:t(?:\s[^>]*)?>(.*?)(?:</w:t>|$)|(<w:tab\s*/>)|(<w:br\s*/>)")
_HEADING = re.compile(r'<w:pStyle w:val="(?:Heading|Titre|heading)\s*(\d)"')
_TBL = re.compile(r"(?s)<w:tbl>.*?(?:</w:tbl>|$)")
_TR = re.compile(r"(?s)<w:tr[ >].*?(?:</w:tr>|$)")
_TC = re.compile(r"(?s)<w:tc[ >].*?(?:</w:tc>|$)")


def _word_par(frag: str) -> str:
    parts = []
    for m in _RUN_TOKENS.finditer(frag):
        if m.group(1) is not None:
            parts.append(html.unescape(m.group(1)))
        else:
            parts.append("\t" if m.group(2) else " ")
    return "".join(parts).strip()


def _docx(members: Dict[str, bytes]) -> str:
    raw = members.get("word/document.xml")
    if not raw:
        return ""
    xml = raw.decode("utf-8", "replace")
    lines: List[str] = []
    pos = 0

    cut = not xml.rstrip().endswith("</w:document>")       # le fichier s'arrête avant sa fin : le dernier élément lu peut être coupé

    def paragraphs(chunk: str, last: bool = False) -> None:
        found = list(_P_SPLIT.finditer(chunk))
        for k, pm in enumerate(found):
            t = _word_par(pm.group(0))
            if t:
                if last and cut and k == len(found) - 1 and not pm.group(0).rstrip().endswith("</w:p>"):
                    t += " " + _INCOMPLETE
                h = _HEADING.search(pm.group(0))
                lines.append(("#" * min(int(h.group(1)), 6) + " " + t) if h else t)
                lines.append("")

    for tm in _TBL.finditer(xml):
        paragraphs(xml[pos:tm.start()])
        rows = [[" ".join(filter(None, (_word_par(p.group(0)) for p in _P_SPLIT.finditer(c.group(0))))) for c in _TC.finditer(r.group(0))]
                for r in _TR.finditer(tm.group(0))]
        rows = [r for r in rows if any(r)]
        if rows:
            lines.append(md_table(rows))
            if cut and not tm.group(0).rstrip().endswith("</w:tbl>"):
                lines.append(f"_{_INCOMPLETE_ROW}_")
            lines.append("")
        pos = tm.end()
    paragraphs(xml[pos:], last=True)
    return "\n".join(lines).strip()


def _pptx(members: Dict[str, bytes]) -> str:
    slides = sorted((n for n in members if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)))
    out: List[str] = []
    for i, n in enumerate(slides, 1):
        xml = members[n].decode("utf-8", "replace")
        paras = [t.strip() for t in (_txt("".join(re.findall(r"(?s)<a:t>(.*?)(?:</a:t>|$)", p))) for p in re.findall(r"(?s)<a:p[ >/].*?(?:</a:p>|$)", xml)) if t.strip()]
        if paras:
            tail = "\n\n_" + "diapositive coupée : texte possiblement incomplet" + "_" if not xml.rstrip().endswith("</p:sld>") else ""
            out.append(f"## Slide {i} — {paras[0]}\n\n" + "\n".join(f"- {p}" for p in paras[1:]) + tail)
        elif xml.strip():
            out.append(f"## Slide {i}\n\n_(aucun texte récupérable)_")
    return "\n\n".join(out).strip()


def _col_index(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


_BUILTIN_DATE_FORMATS = set(range(14, 23)) | set(range(27, 37)) | {45, 46, 47} | set(range(50, 59))


def _is_date_format(code: str) -> bool:
    code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code)            # textes entre guillemets, [Rouge], [$-40C], caractères échappés
    return bool(re.search(r"(?i)[ymdhs]", code)) and not re.search(r"(?i)general", code)


def _date_styles(members: Dict[str, bytes]) -> set:
    """Index de style (attribut s=) dont le format est une date ou une heure."""
    raw = members.get("xl/styles.xml")
    if not raw:
        return set()
    xml = raw.decode("utf-8", "replace")
    custom = {}
    for tag in re.findall(r"<numFmt\b[^>]*>", xml):
        i, code = re.search(r'numFmtId="(\d+)"', tag), re.search(r'formatCode="([^"]*)"', tag)
        if i and code:
            custom[int(i.group(1))] = html.unescape(code.group(1))
    block = re.search(r"(?s)<cellXfs\b[^>]*>(.*?)(?:</cellXfs>|$)", xml)
    out = set()
    for idx, attrs in enumerate(re.findall(r"<xf\b([^>]*?)/?>", block.group(1)) if block else []):
        m = re.search(r'numFmtId="(\d+)"', attrs)
        fid = int(m.group(1)) if m else 0
        if fid in _BUILTIN_DATE_FORMATS or (fid in custom and _is_date_format(custom[fid])):
            out.add(idx)
    return out


def _from_serial(text: str, base1904: bool) -> str:
    """Numéro de série Excel → date ISO (heure ajoutée s'il y en a une) ; la valeur brute si elle n'a pas de sens."""
    from datetime import datetime, timedelta

    try:
        v = float(text)
        dt = (datetime(1904, 1, 1) if base1904 else datetime(1899, 12, 30)) + timedelta(days=v)
    except (ValueError, OverflowError):
        return text
    if 0 <= v < 1:
        return dt.strftime("%H:%M:%S")
    return dt.strftime("%Y-%m-%d") if v == int(v) else dt.strftime("%Y-%m-%d %H:%M:%S")


def _xlsx(members: Dict[str, bytes]) -> str:
    shared: List[str] = []
    if "xl/sharedStrings.xml" in members:
        sx = members["xl/sharedStrings.xml"].decode("utf-8", "replace")
        shared = [_txt("".join(re.findall(r"(?s)<t(?:\s[^>]*)?>(.*?)(?:</t>|$)", si))) for si in re.findall(r"(?s)<si>.*?(?:</si>|$)", sx)]
    names: List[str] = []
    base1904 = False
    if "xl/workbook.xml" in members:
        wb = members["xl/workbook.xml"].decode("utf-8", "replace")
        names = [html.unescape(x) for x in re.findall(r'<sheet\s[^>]*name="([^"]*)"', wb)]
        base1904 = bool(re.search(r'date1904="(?:1|true)"', wb))
    dates = _date_styles(members)
    sheets = sorted((n for n in members if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)), key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)))
    out: List[str] = []
    for i, n in enumerate(sheets):
        xml = members[n].decode("utf-8", "replace")
        rows: List[List[str]] = []
        incomplete = False
        for rm in re.finditer(r"(?s)<row\b.*?(?:</row>|$)", xml):
            row: Dict[int, str] = {}
            if not rm.group(0).rstrip().endswith("</row>"):
                incomplete = True          # c'est la dernière ligne lue : le fichier s'arrête dedans
            for cm in re.finditer(r'(?s)<c\s([^>]*?)(?:/>|>(.*?)</c>)', rm.group(0)):      # une cellule dont la balise n'est pas fermée est coupée : écartée
                attrs, inner = cm.group(1), cm.group(2) or ""
                ref = re.search(r'\br="([A-Z]+\d+)"', attrs)
                if not ref:
                    continue
                kind = (re.search(r'\bt="(\w+)"', attrs) or [None, ""])[1]
                style = re.search(r'\bs="(\d+)"', attrs)
                v = re.search(r"(?s)<v>(.*?)(?:</v>|$)", inner)
                if kind == "s" and v and v.group(1).strip().isdigit():
                    idx = int(v.group(1))
                    val = shared[idx] if idx < len(shared) else ""
                elif kind == "inlineStr":
                    val = _txt("".join(re.findall(r"(?s)<t(?:\s[^>]*)?>(.*?)(?:</t>|$)", inner)))
                else:
                    val = html.unescape(v.group(1)) if v else ""
                    if kind == "b" and val in ("0", "1"):
                        val = "TRUE" if val == "1" else "FALSE"
                    elif kind in ("", "n") and val and style and int(style.group(1)) in dates:
                        val = _from_serial(val, base1904)
                if val == "":
                    f = re.search(r"(?s)<f\b[^>]*>(.*?)</f>", inner)           # pas de valeur mémorisée : la formule elle-même
                    if f and f.group(1).strip():
                        val = "=" + html.unescape(f.group(1).strip())
                if val != "":
                    row[_col_index(ref.group(1))] = val
            if row:
                rows.append([row.get(c, "") for c in range(max(row) + 1)])
        if rows:
            title = names[i] if i < len(names) else f"Feuille {i + 1}"
            note = f"\n\n_{_INCOMPLETE_ROW}_" if incomplete else ""
            out.append(f"## {title}\n\n" + md_table(rows) + note)
    return "\n\n".join(out).strip()


# ---- OpenDocument ------------------------------------------------------------------------------------------------

def _odf_text(frag: str) -> str:
    frag = re.sub(r"<text:tab\s*/>", "\t", frag)
    frag = re.sub(r"<text:(?:line-break|s)\b[^>]*/>", " ", frag)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "", frag))).strip()


_ODF_BLOCK = re.compile(r"(?s)<text:(h|p)\b([^>]*)>(.*?)(</text:\1>|$)")
_ODF_TABLE = re.compile(r"(?s)<table:table\b.*?(?:</table:table>|$)")
_ODF_ROW = re.compile(r"(?s)<table:table-row\b.*?(?:</table:table-row>|$)")
_ODF_CELL = re.compile(r"(?s)<table:table-cell\b([^>]*?)(?:/>|>(.*?)</table:table-cell>)")


def _odf_cell(attrs: str, inner: str) -> str:
    kind = re.search(r'office:value-type="(\w+)"', attrs)
    kind = kind.group(1) if kind else ""
    for key in ("office:date-value", "office:time-value", "office:value", "office:boolean-value"):
        m = re.search(rf'{key}="([^"]*)"', attrs)
        if m and kind in ("date", "time", "float", "percentage", "currency", "boolean"):
            return html.unescape(m.group(1))
    text = " ".join(t for t in (_odf_text(p) for p in re.findall(r"(?s)<text:p\b[^>]*>(.*?)</text:p>", inner or "")) if t)
    if not text:
        f = re.search(r'table:formula="([^"]*)"', attrs)
        if f:
            return "=" + html.unescape(f.group(1)).split(":=", 1)[-1].lstrip("=")
    return text


def _odt(members: Dict[str, bytes]) -> str:
    raw = members.get("content.xml")
    if not raw:
        return ""
    xml = raw.decode("utf-8", "replace")
    cut = not xml.rstrip().endswith("</office:document-content>")
    lines: List[str] = []

    def blocks(chunk: str, last: bool = False) -> None:
        found = list(_ODF_BLOCK.finditer(chunk))
        for k, m in enumerate(found):
            t = _odf_text(m.group(3))
            if not t:
                continue
            if last and cut and k == len(found) - 1 and not m.group(4):
                t += " " + _INCOMPLETE
            lvl = re.search(r'text:outline-level="(\d+)"', m.group(2))
            lines.append(("#" * min(int(lvl.group(1)), 6) + " " + t) if m.group(1) == "h" and lvl else t)
            lines.append("")

    pos = 0
    for tm in _ODF_TABLE.finditer(xml):
        blocks(xml[pos:tm.start()])
        rows = [[_odf_cell(c.group(1), c.group(2)) for c in _ODF_CELL.finditer(r.group(0))] for r in _ODF_ROW.finditer(tm.group(0))]
        rows = [r for r in rows if any(r)]
        if rows:
            lines.append(md_table(rows))
            if cut and not tm.group(0).rstrip().endswith("</table:table>"):
                lines.append(f"_{_INCOMPLETE_ROW}_")
            lines.append("")
        pos = tm.end()
    blocks(xml[pos:], last=True)
    return "\n".join(lines).strip()


def _ods(members: Dict[str, bytes]) -> str:
    raw = members.get("content.xml")
    if not raw:
        return ""
    xml = raw.decode("utf-8", "replace")
    out: List[str] = []
    for k, tm in enumerate(_ODF_TABLE.finditer(xml), 1):
        name = re.search(r'table:name="([^"]*)"', tm.group(0)[:600])
        rows: List[List[str]] = []
        incomplete = False
        for r in _ODF_ROW.finditer(tm.group(0)):
            if not r.group(0).rstrip().endswith("</table:table-row>"):
                incomplete = True
            row: List[str] = []
            for c in _ODF_CELL.finditer(r.group(0)):
                rep = re.search(r'table:number-columns-repeated="(\d+)"', c.group(1))
                val = _odf_cell(c.group(1), c.group(2))
                row.extend([val] * (min(int(rep.group(1)), 50) if rep and val else (int(rep.group(1)) if rep and int(rep.group(1)) <= 50 else 1)))
            while row and row[-1] == "":
                row.pop()
            if row:
                rows.append(row)
        if rows:
            out.append(f"## {html.unescape(name.group(1)) if name else f'Feuille {k}'}\n\n" + md_table(rows) + (f"\n\n_{_INCOMPLETE_ROW}_" if incomplete else ""))
    return "\n\n".join(out).strip()


def _odp(members: Dict[str, bytes]) -> str:
    raw = members.get("content.xml")
    if not raw:
        return ""
    xml = raw.decode("utf-8", "replace")
    out: List[str] = []
    for k, pm in enumerate(re.finditer(r"(?s)<draw:page\b.*?(?:</draw:page>|$)", xml), 1):
        paras = [t for t in (_odf_text(p) for p in re.findall(r"(?s)<text:p\b[^>]*>(.*?)(?:</text:p>|$)", pm.group(0))) if t]
        if paras:
            tail = "" if pm.group(0).rstrip().endswith("</draw:page>") else "\n\n_diapositive coupée : texte possiblement incomplet_"
            out.append(f"## Slide {k} — {paras[0]}\n\n" + "\n".join(f"- {p}" for p in paras[1:]) + tail)
    return "\n\n".join(out).strip()


# ---- EPUB --------------------------------------------------------------------------------------------------------

def _epub(members: Dict[str, bytes]) -> str:
    order: List[str] = []
    opf_name = next((n for n in members if n.lower().endswith(".opf")), "")
    if opf_name:
        opf = members[opf_name].decode("utf-8", "replace")
        base = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
        manifest = {}
        for tag in re.findall(r"<item\b[^>]*>", opf):
            i, h = re.search(r'\bid="([^"]*)"', tag), re.search(r'\bhref="([^"]*)"', tag)
            if i and h:
                manifest[i.group(1)] = base + html.unescape(h.group(1))
        order = [manifest[r] for r in re.findall(r'<itemref\b[^>]*idref="([^"]*)"', opf) if r in manifest]
    chapters = [n for n in order if n in members] or sorted(n for n in members if n.lower().endswith((".xhtml", ".html", ".htm")))
    out: List[str] = []
    title = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", members[opf_name].decode("utf-8", "replace"), re.S) if opf_name else None
    if title:
        out.append("# " + _txt(title.group(1)).strip())
    for n in chapters:
        x = members[n].decode("utf-8", "replace")
        x = re.sub(r"(?is)<(script|style)\b.*?(?:</\1>|$)", "", x)
        x = re.sub(r"(?is)<h([1-6])\b[^>]*>(.*?)(?:</h\1>|$)", lambda m: "\n\n" + "#" * (int(m.group(1)) + (1 if title else 0)) + " " + _txt(m.group(2)).strip() + "\n\n", x)
        x = re.sub(r"(?i)</?(?:p|div|li|tr|br|blockquote|section)\b[^>]*>", "\n", x)
        text = "\n".join(ln.strip() for ln in _txt(x).splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            out.append(text)
    return "\n\n".join(out).strip()


_MAIN = {"docx": "word/document.xml", "pptx": "ppt/presentation.xml", "xlsx": "xl/workbook.xml",
         "odt": "content.xml", "ods": "content.xml", "odp": "content.xml", "epub": "META-INF/container.xml"}
_EXTRACT = {"docx": _docx, "pptx": _pptx, "xlsx": _xlsx, "odt": _odt, "ods": _ods, "odp": _odp, "epub": _epub}


def _rescue(fmt: str, path, ctx: Ctx) -> Result:
    if _intact(path, _MAIN[fmt]):
        raise Unsupported("fichier intact : pas de mode secours")
    with open(path, "rb") as f:
        data = f.read(ctx.opts.max_size_mb * (1 << 20) + 1)
    members = salvage_members(data)
    if any(re.search(rb"<!(?:DOCTYPE|ENTITY)", body[:4096], re.I) for name, body in members.items() if name.endswith((".xml", ".opf"))):
        raise Unsupported("déclaration DOCTYPE/ENTITY dans une partie XML : refusé (fichier hostile, pas abîmé)")
    md = _EXTRACT[fmt](members)
    if len(md.split()) < 1:
        raise Unsupported("rien de récupérable")
    ctx.warn("fichier abîmé ou tronqué : texte récupéré en mode secours (mise en forme, images et parties manquantes perdues) — "
             "redemander ou réexporter le fichier d'origine si l'intégralité compte")
    return Result(markdown=md, fmt=fmt, meta={"_rescue": True})


@engine("docx", name="rescue", prio=90)
def docx_rescue(path, ctx: Ctx) -> Result:
    return _rescue("docx", path, ctx)


@engine("pptx", name="rescue", prio=90)
def pptx_rescue(path, ctx: Ctx) -> Result:
    return _rescue("pptx", path, ctx)


@engine("xlsx", name="rescue", prio=90)
def xlsx_rescue(path, ctx: Ctx) -> Result:
    return _rescue("xlsx", path, ctx)


@engine("odt", name="rescue", prio=90)
def odt_rescue(path, ctx: Ctx) -> Result:
    return _rescue("odt", path, ctx)


@engine("ods", name="rescue", prio=90)
def ods_rescue(path, ctx: Ctx) -> Result:
    return _rescue("ods", path, ctx)


@engine("odp", name="rescue", prio=90)
def odp_rescue(path, ctx: Ctx) -> Result:
    return _rescue("odp", path, ctx)


@engine("epub", name="rescue", prio=90)
def epub_rescue(path, ctx: Ctx) -> Result:
    return _rescue("epub", path, ctx)
