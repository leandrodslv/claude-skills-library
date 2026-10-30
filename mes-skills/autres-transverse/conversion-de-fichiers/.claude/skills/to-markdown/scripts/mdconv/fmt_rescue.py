"""Mode secours pour Word / PowerPoint / Excel abîmés ou tronqués (téléchargement interrompu, XML cassé).

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


def _xlsx(members: Dict[str, bytes]) -> str:
    shared: List[str] = []
    if "xl/sharedStrings.xml" in members:
        sx = members["xl/sharedStrings.xml"].decode("utf-8", "replace")
        shared = [_txt("".join(re.findall(r"(?s)<t(?:\s[^>]*)?>(.*?)(?:</t>|$)", si))) for si in re.findall(r"(?s)<si>.*?(?:</si>|$)", sx)]
    names: List[str] = []
    if "xl/workbook.xml" in members:
        names = [html.unescape(x) for x in re.findall(r'<sheet\s[^>]*name="([^"]*)"', members["xl/workbook.xml"].decode("utf-8", "replace"))]
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
                kind = re.search(r'\bt="(\w+)"', attrs)
                v = re.search(r"(?s)<v>(.*?)(?:</v>|$)", inner)
                if kind and kind.group(1) == "s" and v and v.group(1).strip().isdigit():
                    idx = int(v.group(1))
                    val = shared[idx] if idx < len(shared) else ""
                elif kind and kind.group(1) == "inlineStr":
                    val = _txt("".join(re.findall(r"(?s)<t(?:\s[^>]*)?>(.*?)(?:</t>|$)", inner)))
                else:
                    val = html.unescape(v.group(1)) if v else ""
                if val != "":
                    row[_col_index(ref.group(1))] = val
            if row:
                rows.append([row.get(c, "") for c in range(max(row) + 1)])
        if rows:
            title = names[i] if i < len(names) else f"Feuille {i + 1}"
            note = f"\n\n_{_INCOMPLETE_ROW}_" if incomplete else ""
            out.append(f"## {title}\n\n" + md_table(rows) + note)
    return "\n\n".join(out).strip()


_MAIN = {"docx": "word/document.xml", "pptx": "ppt/presentation.xml", "xlsx": "xl/workbook.xml"}
_EXTRACT = {"docx": _docx, "pptx": _pptx, "xlsx": _xlsx}


def _rescue(fmt: str, path, ctx: Ctx) -> Result:
    if _intact(path, _MAIN[fmt]):
        raise Unsupported("fichier intact : pas de mode secours")
    with open(path, "rb") as f:
        data = f.read(ctx.opts.max_size_mb * (1 << 20) + 1)
    members = salvage_members(data)
    if any(re.search(rb"<!(?:DOCTYPE|ENTITY)", body[:4096], re.I) for name, body in members.items() if name.endswith(".xml")):
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
