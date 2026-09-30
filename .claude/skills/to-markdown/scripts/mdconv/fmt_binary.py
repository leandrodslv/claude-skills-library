"""Formats Office binaires (.doc, .xls, .ppt) lus SANS LibreOffice, en bibliothèque standard.

Lecteurs volontairement « texte fidèle » : tout le contenu textuel et les valeurs de cellules, mais pas la mise en
forme fine (le .doc perd titres et listes, le .ppt perd les notes et les images). Quand LibreOffice est disponible,
il passe en premier (fmt_legacy.py) et donne un résultat complet.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .cfb import CFB, CFBError
from .core import Ctx, Protected, Result, Unsupported, engine
from .fmt_xlsx import classify_format, clean_number, excel_date
from .grid import grid_blocks
from .util import clean_text, esc_inline, md_table

WARN_LITE = "lecture minimale sans LibreOffice : {}"


def _open(path) -> CFB:
    try:
        return CFB(Path(path).read_bytes())
    except CFBError as exc:
        raise Unsupported(str(exc))


# --------------------------------------------------------------------------
# .doc (Word 97-2003)
# --------------------------------------------------------------------------

@engine("doc", name="native", prio=20)
def doc_lite(path, ctx: Ctx) -> Result:
    cfb = _open(path)
    wd = cfb.read_opt("WordDocument")
    if not wd or len(wd) < 0x1A8 or struct.unpack_from("<H", wd, 0)[0] != 0xA5EC:
        raise Unsupported("flux WordDocument absent : pas un .doc Word 97-2003")
    flags = struct.unpack_from("<H", wd, 0x0A)[0]
    if flags & 0x0100:
        raise Protected("document Word chiffré (mot de passe requis)")
    table = cfb.read_opt("1Table" if flags & 0x0200 else "0Table") or b""
    ccp_text, ccp_ftn = struct.unpack_from("<ii", wd, 0x4C)[0], struct.unpack_from("<i", wd, 0x50)[0]
    fc_clx, lcb_clx = struct.unpack_from("<II", wd, 0x1A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    pos = 0
    while pos < len(clx) and clx[pos] == 0x01:
        pos += 3 + struct.unpack_from("<H", clx, pos + 1)[0]
    if pos >= len(clx) or clx[pos] != 0x02:
        raise Unsupported("table des morceaux (Clx) illisible")
    lcb = struct.unpack_from("<I", clx, pos + 1)[0]
    plc = clx[pos + 5:pos + 5 + lcb]
    n = (lcb - 4) // 12
    cps = struct.unpack_from("<%dI" % (n + 1), plc, 0)
    pcds = plc[(n + 1) * 4:]
    parts: List[str] = []
    for i in range(n):
        fc = struct.unpack_from("<I", pcds, i * 8 + 2)[0]
        ncp = cps[i + 1] - cps[i]
        if fc & 0x40000000:
            off = (fc & 0x3FFFFFFF) // 2
            parts.append(wd[off:off + ncp].decode("cp1252", "replace"))
        else:
            off = fc & 0x3FFFFFFF
            parts.append(wd[off:off + 2 * ncp].decode("utf-16-le", "replace"))
    full = "".join(parts)
    main, foot = full[:ccp_text], full[ccp_text:ccp_text + max(ccp_ftn, 0)]
    md, src = _doc_text_to_md(main)
    notes = [t.strip().lstrip("\x02").strip() for t in foot.split("\r") if t.strip().lstrip("\x02").strip()]
    if notes:
        md += "\n\n" + "\n".join(f"[^{i}]: {esc_inline(clean_text(t))}" for i, t in enumerate(notes, 1))
    if not md.strip():
        raise Unsupported("aucun texte extrait")
    ctx.warn(WARN_LITE.format("titres et listes non reconnus (texte et tableaux conservés) ; installer LibreOffice pour la mise en forme"))
    res = Result(markdown=md, fmt="doc", engine="native", title="")
    res.source_text = src
    res.stats["partial_source"] = True
    return res


def _doc_text_to_md(text: str) -> Tuple[str, str]:
    out: List[str] = []
    rows: List[List[str]] = []
    cells: List[str] = []
    buf: List[str] = []
    depth = 0          # champs imbriqués
    in_result: List[bool] = []
    url_stack: List[Optional[str]] = []
    instr_buf: List[str] = []
    src: List[str] = []
    fn_n = 0

    def flush_rows() -> None:
        nonlocal rows
        if rows:
            grid = [r for r in rows if any(c.strip() for c in r)]
            if grid:
                out.append(md_table(grid))
            rows = []

    for ch in text:
        if ch == "\x13":
            depth += 1
            in_result.append(False)
            url_stack.append(None)
            instr_buf.append("")
            continue
        if ch == "\x14" and in_result:
            in_result[-1] = True
            m = re.search(r'HYPERLINK\s+"([^"]+)"', instr_buf[-1])
            url_stack[-1] = m.group(1) if m else None
            if url_stack[-1]:
                buf.append("[")
            continue
        if ch == "\x15" and in_result:
            was_result = in_result.pop()
            url = url_stack.pop()
            instr_buf.pop()
            if was_result and url:
                buf.append(f"]({url})")
            depth -= 1
            continue
        if in_result and not in_result[-1]:
            instr_buf[-1] += ch  # instruction de champ : ignorée (sauf HYPERLINK)
            continue
        if ch == "\x07":
            if not buf and cells:
                rows.append(cells)
                cells = []
            else:
                cells.append("".join(buf).strip())
                buf = []
        elif ch in ("\r", "\x0c"):
            flush_rows() if not cells else None
            para = "".join(buf).strip()
            buf = []
            if para:
                out.append(esc_inline(clean_text(para)) if "](" not in para else clean_text(para))
                src.append(para)
        elif ch == "\x0b":
            buf.append("\\\n")
        elif ch == "\x02":
            fn_n += 1
            buf.append(f"[^{fn_n}]")
        elif ch == "\x1e":
            buf.append("-")
        elif ch in "\x01\x08\x1f\x00\x05\x0e":
            continue
        else:
            buf.append(ch)
    flush_rows()
    tail = "".join(buf).strip()
    if tail:
        out.append(esc_inline(clean_text(tail)))
    # les tableaux ont été émis à part : on les replace en fin de bloc contigu (ordre approximatif)
    return "\n\n".join(out), "\n".join(src)


# --------------------------------------------------------------------------
# .xls (BIFF8)
# --------------------------------------------------------------------------

def _biff_records(data: bytes):
    pos, n = 0, len(data)
    while pos + 4 <= n:
        op, ln = struct.unpack_from("<HH", data, pos)
        yield op, data[pos + 4:pos + 4 + ln], pos
        pos += 4 + ln


def _rk(v: int) -> float:
    """Nombre « RK » compact d'Excel : entier signé sur 30 bits ou double tronqué, éventuellement ÷ 100."""
    if v & 2:
        n = v >> 2
        f = float(n - 0x40000000 if n & 0x20000000 else n)
    else:
        f = struct.unpack("<d", struct.pack("<Q", (v & 0xFFFFFFFC) << 32))[0]
    return f / 100.0 if v & 1 else f


class _SstReader:
    """Lecture des chaînes partagées, qui peuvent se prolonger sur plusieurs enregistrements CONTINUE."""

    def __init__(self, chunks: List[bytes]):
        self.chunks, self.ci, self.pos = chunks, 0, 0

    def _avail(self) -> int:
        return len(self.chunks[self.ci]) - self.pos if self.ci < len(self.chunks) else 0

    def _next_chunk(self) -> bool:
        self.ci += 1
        self.pos = 0
        return self.ci < len(self.chunks)

    def read(self, n: int) -> bytes:
        out = b""
        while n > 0:
            if self._avail() == 0 and not self._next_chunk():
                break
            take = min(n, self._avail())
            out += self.chunks[self.ci][self.pos:self.pos + take]
            self.pos += take
            n -= take
        return out

    def string(self) -> str:
        head = self.read(3)
        if len(head) < 3:
            return ""
        cch, flags = struct.unpack_from("<HB", head)
        rich = struct.unpack("<H", self.read(2))[0] if flags & 0x08 else 0
        ext = struct.unpack("<I", self.read(4))[0] if flags & 0x04 else 0
        wide = bool(flags & 0x01)
        chars: List[str] = []
        remaining = cch
        while remaining > 0:
            if self._avail() == 0:
                if not self._next_chunk():
                    break
                wide = bool(self.chunks[self.ci][0] & 0x01)  # nouvel octet d'options en tête de bloc
                self.pos = 1
            width = 2 if wide else 1
            take = min(remaining, self._avail() // width)
            if take == 0:
                self.pos += 1
                continue
            raw = self.chunks[self.ci][self.pos:self.pos + take * width]
            self.pos += take * width
            chars.append(raw.decode("utf-16-le" if wide else "cp1252", "replace"))
            remaining -= take
        self.read(4 * rich + ext)
        return "".join(chars)


@engine("xls", name="native", prio=20)
def xls_lite(path, ctx: Ctx) -> Result:
    cfb = _open(path)
    wb = cfb.read_opt("Workbook") or cfb.read_opt("Book")
    if not wb:
        raise Unsupported("flux Workbook absent")
    if len(wb) < 8 or struct.unpack_from("<H", wb, 0)[0] != 0x0809:
        raise Unsupported("BOF absent")
    if struct.unpack_from("<H", wb, 4)[0] < 0x0600:
        raise Unsupported("BIFF antérieur à Excel 97 non pris en charge")
    formats: Dict[int, str] = {}
    xf_fmt: List[int] = []
    sheets: List[Tuple[str, int, int]] = []
    sst_chunks: List[bytes] = []
    date1904 = False
    sst_active = False
    for op, body, off in _biff_records(wb):
        if op == 0x00FC:  # SST
            sst_chunks = [body[8:]]
            sst_active = True
            continue
        if op == 0x003C and sst_active:
            sst_chunks.append(body)
            continue
        sst_active = False if op != 0x003C else sst_active
        if op == 0x0085 and len(body) >= 8:  # BOUNDSHEET
            pos, state, kind, cch, fl = struct.unpack_from("<IBBBB", body, 0)
            name = body[8:8 + (cch * 2 if fl & 1 else cch)].decode("utf-16-le" if fl & 1 else "cp1252", "replace")
            if kind == 0:
                sheets.append((clean_text(name), pos, state))
        elif op == 0x041E and len(body) >= 5:  # FORMAT
            idx, cch = struct.unpack_from("<HH", body, 0)
            fl = body[4]
            formats[idx] = body[5:5 + (cch * 2 if fl & 1 else cch)].decode("utf-16-le" if fl & 1 else "cp1252", "replace")
        elif op == 0x00E0 and len(body) >= 4:  # XF
            xf_fmt.append(struct.unpack_from("<H", body, 2)[0])
        elif op == 0x0022 and len(body) >= 2:
            date1904 = bool(struct.unpack_from("<H", body, 0)[0])
    strings = []
    if sst_chunks:
        rd = _SstReader(sst_chunks)
        total = struct.unpack_from("<I", wb, [o for op, b, o in _biff_records(wb) if op == 0x00FC][0] + 4 + 4)[0]
        for _ in range(total):
            strings.append(clean_text(rd.string()))

    def render(v: float, xf: int) -> str:
        fid = xf_fmt[xf] if 0 <= xf < len(xf_fmt) else 0
        kind, dec = classify_format(formats.get(fid, ""), fid)
        if kind in ("date", "time", "datetime"):
            import datetime as dt

            d = excel_date(v, date1904)
            if d is not None:
                d = (d + dt.timedelta(milliseconds=500)).replace(microsecond=0)
                if kind == "time" or (kind == "datetime" and v < 1):
                    return d.strftime("%H:%M:%S") if d.second else d.strftime("%H:%M")
                if kind == "date":
                    return d.strftime("%Y-%m-%d")
                return d.strftime("%Y-%m-%d %H:%M:%S") if d.second else d.strftime("%Y-%m-%d %H:%M")
        if kind == "percent":
            return f"{v * 100:.{dec}f}%"
        return clean_number(repr(v))

    parts: List[str] = []
    sheet_texts: List[str] = []
    hidden = 0
    for name, pos, state in sheets:
        if state != 0:
            hidden += 1
            if not ctx.opts.hidden:
                continue
        rows: Dict[int, Dict[int, str]] = {}
        last_formula: Optional[Tuple[int, int]] = None
        for op, body, _o in _biff_records(wb[pos:]):
            if op == 0x000A:
                break
            if op == 0x00FD and len(body) >= 10:
                r, c, _xf, i = struct.unpack_from("<HHHI", body, 0)
                if i < len(strings) and strings[i]:
                    rows.setdefault(r + 1, {})[c + 1] = esc_inline(strings[i])
                    sheet_texts.append(strings[i])
            elif op == 0x0203 and len(body) >= 14:
                r, c, xf, v = struct.unpack_from("<HHHd", body, 0)
                rows.setdefault(r + 1, {})[c + 1] = render(v, xf)
            elif op == 0x027E and len(body) >= 10:
                r, c, xf, rk = struct.unpack_from("<HHHI", body, 0)
                rows.setdefault(r + 1, {})[c + 1] = render(_rk(rk), xf)
            elif op == 0x00BD and len(body) >= 6:
                r, c0 = struct.unpack_from("<HH", body, 0)
                for k in range((len(body) - 6) // 6):
                    xf, rk = struct.unpack_from("<HI", body, 4 + k * 6)
                    rows.setdefault(r + 1, {})[c0 + k + 1] = render(_rk(rk), xf)
            elif op == 0x0204 and len(body) >= 8:
                r, c, _xf, cch = struct.unpack_from("<HHHH", body, 0)
                fl = body[8] if len(body) > 8 else 0
                txt = body[9:9 + (cch * 2 if fl & 1 else cch)].decode("utf-16-le" if fl & 1 else "cp1252", "replace")
                if txt.strip():
                    rows.setdefault(r + 1, {})[c + 1] = esc_inline(clean_text(txt))
                    sheet_texts.append(txt)
            elif op == 0x0205 and len(body) >= 8:
                r, c, _xf, val, err = struct.unpack_from("<HHHBB", body, 0)
                rows.setdefault(r + 1, {})[c + 1] = ("#ERR" if err else ("TRUE" if val else "FALSE"))
            elif op == 0x0006 and len(body) >= 14:
                r, c, xf = struct.unpack_from("<HHH", body, 0)
                res8 = body[6:14]
                if res8[6:8] == b"\xff\xff":
                    t = res8[0]
                    if t == 1:
                        rows.setdefault(r + 1, {})[c + 1] = "TRUE" if res8[2] else "FALSE"
                    elif t == 2:
                        rows.setdefault(r + 1, {})[c + 1] = "#ERR"
                    else:
                        last_formula = (r + 1, c + 1)
                else:
                    rows.setdefault(r + 1, {})[c + 1] = render(struct.unpack("<d", res8)[0], xf)
            elif op == 0x0207 and last_formula and len(body) >= 3:
                cch, fl = struct.unpack_from("<HB", body, 0)
                txt = body[3:3 + (cch * 2 if fl & 1 else cch)].decode("utf-16-le" if fl & 1 else "cp1252", "replace")
                if txt.strip():
                    rows.setdefault(last_formula[0], {})[last_formula[1]] = esc_inline(clean_text(txt))
                last_formula = None
        head = f"## {esc_inline(name)}" + (" *(masquée)*" if state != 0 else "")
        if not rows:
            parts.append(f"{head}\n\n_(feuille vide)_")
        else:
            parts.append("\n\n".join([head] + grid_blocks(ctx, rows, name, "", len(rows))))
    md = "\n\n".join(parts)
    if not sheets:
        raise Unsupported("aucune feuille de calcul")
    ctx.warn(WARN_LITE.format("valeurs de cellules uniquement (pas de formules, graphiques, commentaires ni fusions)"))
    if hidden:
        ctx.warn(f"{hidden} feuille(s) masquée(s)" + (" (incluses, signalées)" if ctx.opts.hidden else " (ignorées)"))
    res = Result(markdown=md, fmt="xls", engine="native", title="")
    res.units, res.unit_name, res.units_found = len(sheets), "feuille", len(re.findall(r"(?m)^## ", md))
    res.source_text = None if "_Tableau tronqué" in md else "\n".join(sheet_texts)
    res.stats["partial_source"] = True
    return res


# --------------------------------------------------------------------------
# .ppt (PowerPoint 97-2003)
# --------------------------------------------------------------------------

def _ppt_records(data: bytes, start: int, end: int):
    pos = start
    while pos + 8 <= end:
        verinst, typ, ln = struct.unpack_from("<HHI", data, pos)
        yield verinst & 0xF, verinst >> 4, typ, ln, pos + 8, pos
        pos += 8 + ln


def _ppt_texts(data: bytes, start: int, end: int, out: List[Tuple[int, str]], kind: int = 4) -> None:
    """Collecte (type de texte, contenu) de tous les atomes de texte d'un sous-arbre, dans l'ordre."""
    for ver, inst, typ, ln, body, pos in _ppt_records(data, start, end):
        if ver == 0xF:
            _ppt_texts(data, body, min(body + ln, end), out, kind)
            continue
        if typ == 0x0F9F and ln >= 4:  # TextHeaderAtom
            kind = struct.unpack_from("<I", data, body)[0]
        elif typ == 0x0FA0:  # TextCharsAtom (UTF-16)
            out.append((kind, data[body:body + ln].decode("utf-16-le", "replace")))
        elif typ == 0x0FA8:  # TextBytesAtom (latin-1)
            out.append((kind, data[body:body + ln].decode("cp1252", "replace")))


@engine("ppt", name="native", prio=20)
def ppt_lite(path, ctx: Ctx) -> Result:
    cfb = _open(path)
    doc = cfb.read_opt("PowerPoint Document")
    cur = cfb.read_opt("Current User")
    if not doc or not cur or len(cur) < 20:
        raise Unsupported("flux PowerPoint Document absent")
    edit = struct.unpack_from("<I", cur, 16)[0]
    persist: Dict[int, int] = {}
    doc_ref = 0
    seen = set()
    first = True
    while edit and edit not in seen and edit + 8 <= len(doc):
        seen.add(edit)
        verinst, typ, ln = struct.unpack_from("<HHI", doc, edit)
        if typ != 0x0FF5:
            break
        last_edit, dir_off, ref = struct.unpack_from("<III", doc, edit + 8 + 8)
        if first:
            doc_ref, first = ref, False
        if dir_off + 8 <= len(doc):
            dtyp, dln = struct.unpack_from("<HI", doc, dir_off + 2)
            if dtyp == 0x1772:
                p, end = dir_off + 8, dir_off + 8 + dln
                while p + 4 <= end:
                    info = struct.unpack_from("<I", doc, p)[0]
                    pid, cnt = info & 0xFFFFF, info >> 20
                    p += 4
                    for k in range(cnt):
                        if p + 4 > end:
                            break
                        persist.setdefault(pid + k, struct.unpack_from("<I", doc, p)[0])
                        p += 4
        edit = last_edit
    doc_off = persist.get(doc_ref)
    if doc_off is None:
        raise Unsupported("annuaire des objets illisible")
    dtyp, dln = struct.unpack_from("<HI", doc, doc_off + 2)
    slide_refs: List[int] = []
    for ver, inst, typ, ln, body, pos in _ppt_records(doc, doc_off + 8, doc_off + 8 + dln):
        if typ == 0x0FF0 and inst == 0:  # SlideListWithText : diapositives
            for v2, i2, t2, l2, b2, p2 in _ppt_records(doc, body, body + ln):
                if t2 == 0x03F3 and l2 >= 4:
                    slide_refs.append(struct.unpack_from("<I", doc, b2)[0])
    if not slide_refs:
        raise Unsupported("aucune diapositive trouvée")
    blocks: List[str] = []
    src: List[str] = []
    for n, ref in enumerate(slide_refs, 1):
        off = persist.get(ref)
        texts: List[Tuple[int, str]] = []
        if off is not None and off + 8 <= len(doc):
            ln = struct.unpack_from("<I", doc, off + 4)[0]
            _ppt_texts(doc, off + 8, min(off + 8 + ln, len(doc)), texts)
        title = ""
        pieces: List[str] = []
        for kind, raw in texts:
            paras = [clean_text(p).replace("\x0b", " ").strip() for p in raw.replace("\r", "\n").split("\n")]
            paras = [p for p in paras if p]
            if not paras:
                continue
            src.extend(paras)
            if kind in (0, 6) and not title:
                title = " ".join(paras)
            elif kind in (1, 5, 7, 8):
                pieces.append("\n".join("- " + esc_inline(p) for p in paras))
            else:
                pieces.append("\n\n".join(esc_inline(p) for p in paras))
        head = f"## Slide {n}" + (f" — {esc_inline(title)}" if title else "")
        blocks.append("\n\n".join([head] + pieces))
    md = "\n\n".join(blocks)
    ctx.warn(WARN_LITE.format("texte des diapositives uniquement (pas d'images, de notes ni de tableaux) ; installer LibreOffice pour une conversion complète"))
    res = Result(markdown=md, fmt="ppt", engine="native", title="")
    res.units, res.unit_name, res.units_found = len(slide_refs), "slide", len(re.findall(r"(?m)^## Slide \d+", md))
    res.source_text = "\n".join(src)
    res.stats["partial_source"] = True
    return res
