"""Extraction de texte PDF en bibliothèque standard — dernier recours quand aucun outil PDF n'est installé.

Couvre les PDF « à texte » courants (Word, LibreOffice, reportlab, pdfTeX, navigateurs) : objets et flux
compressés (Flate, ASCII85, ASCIIHex, RunLength), flux d'objets (ObjStm), polices simples ou composites avec
table ToUnicode, codages WinAnsi/MacRoman/Differences, formulaires XObject, position des fragments (lignes,
espaces, colonnes). Ne lit PAS : PDF scannés (→ OCR / lecture visuelle), polices sans table Unicode, chiffrement AES.
"""
from __future__ import annotations

import base64
import html.entities
import re
import zlib
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .core import Protected, Unsupported

MAX_PAGES = 400
MAX_STREAM = 256 << 20


class Name(str):
    pass


class Ref:
    __slots__ = ("num", "gen")

    def __init__(self, num: int, gen: int):
        self.num, self.gen = num, gen


class Stream:
    __slots__ = ("d", "raw")

    def __init__(self, d: Dict[str, Any], raw: bytes):
        self.d, self.raw = d, raw


_WS = b" \t\r\n\f\x00"
_DELIM = b"()<>[]{}/%"
_NUM = re.compile(rb"[+-]?(?:\d+\.?\d*|\.\d+)")


# --------------------------------------------------------------------------
# Analyse des objets
# --------------------------------------------------------------------------

class Lexer:
    def __init__(self, data: bytes, pos: int = 0):
        self.d, self.p = data, pos

    def skip(self) -> None:
        d, n = self.d, len(self.d)
        while self.p < n:
            c = d[self.p]
            if c in _WS:
                self.p += 1
            elif c == 0x25:  # %
                while self.p < n and d[self.p] not in b"\r\n":
                    self.p += 1
            else:
                break

    def parse(self) -> Any:
        self.skip()
        d, n = self.d, len(self.d)
        if self.p >= n:
            return None
        c = d[self.p]
        if c == 0x2F:  # /Name
            self.p += 1
            s = self.p
            while self.p < n and d[self.p] not in _WS and d[self.p] not in _DELIM:
                self.p += 1
            raw = d[s:self.p]
            if b"#" in raw:
                raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
            return Name(raw.decode("latin-1"))
        if c == 0x28:  # (string)
            return self._string()
        if c == 0x3C:
            if d[self.p:self.p + 2] == b"<<":
                self.p += 2
                out: Dict[str, Any] = {}
                while True:
                    self.skip()
                    if self.p >= n:
                        break
                    if d[self.p:self.p + 2] == b">>":
                        self.p += 2
                        break
                    k = self.parse()
                    if not isinstance(k, Name):
                        continue
                    out[str(k)] = self.parse()
                return out
            end = d.find(b">", self.p)
            end = n if end < 0 else end
            hexs = re.sub(rb"[^0-9A-Fa-f]", b"", d[self.p + 1:end])
            if len(hexs) % 2:
                hexs += b"0"
            self.p = end + 1
            return bytes.fromhex(hexs.decode())
        if c == 0x5B:  # [array]
            self.p += 1
            arr: List[Any] = []
            while True:
                self.skip()
                if self.p >= n:
                    break
                if d[self.p] == 0x5D:
                    self.p += 1
                    break
                arr.append(self.parse())
            return arr
        m = _NUM.match(d, self.p)
        if m:
            self.p = m.end()
            text = m.group(0)
            val: Any = float(text) if b"." in text else int(text)
            if isinstance(val, int) and val >= 0:  # référence « n g R » ?
                save = self.p
                m2 = re.compile(rb"\s+(\d+)\s+R(?![A-Za-z])").match(d, self.p)
                if m2:
                    self.p = m2.end()
                    return Ref(val, int(m2.group(1)))
                self.p = save
            return val
        s = self.p
        while self.p < n and d[self.p] not in _WS and d[self.p] not in _DELIM:
            self.p += 1
        if self.p == s:
            self.p += 1
            return None
        word = d[s:self.p]
        return {b"true": True, b"false": False, b"null": None}.get(word, ("op", word.decode("latin-1")))

    def _string(self) -> bytes:
        d, n = self.d, len(self.d)
        self.p += 1
        depth = 1
        out = bytearray()
        while self.p < n and depth:
            c = d[self.p]
            self.p += 1
            if c == 0x5C:  # backslash
                if self.p >= n:
                    break
                e = d[self.p]
                self.p += 1
                if e in b"nrtbf":
                    out.append({ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}[e])
                elif 0x30 <= e <= 0x37:
                    v = e - 0x30
                    for _ in range(2):
                        if self.p < n and 0x30 <= d[self.p] <= 0x37:
                            v = v * 8 + d[self.p] - 0x30
                            self.p += 1
                        else:
                            break
                    out.append(v & 0xFF)
                elif e in b"\r\n":
                    if e == 0x0D and self.p < n and d[self.p] == 0x0A:
                        self.p += 1
                else:
                    out.append(e)
            elif c == 0x28:
                depth += 1
                out.append(c)
            elif c == 0x29:
                depth -= 1
                if depth:
                    out.append(c)
            else:
                out.append(c)
        return bytes(out)


def _ascii85(data: bytes) -> bytes:
    data = data.strip()
    if data.startswith(b"<~"):
        data = data[2:]
    end = data.find(b"~>")
    if end >= 0:
        data = data[:end]
    return base64.a85decode(re.sub(rb"\s+", b"", data), adobe=False)


def _runlength(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        n = data[i]
        i += 1
        if n == 128:
            break
        if n < 128:
            out += data[i:i + n + 1]
            i += n + 1
        else:
            out += data[i:i + 1] * (257 - n)
            i += 1
    return bytes(out)


def _lzw(data: bytes, early: int = 1) -> bytes:
    out = bytearray()
    table = {i: bytes([i]) for i in range(256)}
    nxt, bits, buf, nb = 258, 9, 0, 0
    prev = b""
    for byte in data:
        buf = (buf << 8) | byte
        nb += 8
        while nb >= bits:
            code = (buf >> (nb - bits)) & ((1 << bits) - 1)
            nb -= bits
            if code == 256:
                table = {i: bytes([i]) for i in range(256)}
                nxt, bits, prev = 258, 9, b""
                continue
            if code == 257:
                return bytes(out)
            entry = table.get(code, prev + prev[:1]) if prev else table.get(code, b"")
            out += entry
            if prev:
                table[nxt] = prev + entry[:1]
                nxt += 1
                if nxt + early >= (1 << bits) and bits < 12:
                    bits += 1
            prev = entry
    return bytes(out)


def _png_predictor(data: bytes, columns: int, colors: int = 1, bpc: int = 8) -> bytes:
    bpp = max(1, colors * bpc // 8)
    row = columns * colors * bpc // 8
    out = bytearray()
    prev = bytearray(row)
    i = 0
    while i + row + 1 <= len(data):
        ft = data[i]
        cur = bytearray(data[i + 1:i + 1 + row])
        i += row + 1
        for x in range(row):
            a = cur[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if ft == 1:
                cur[x] = (cur[x] + a) & 255
            elif ft == 2:
                cur[x] = (cur[x] + b) & 255
            elif ft == 3:
                cur[x] = (cur[x] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                cur[x] = (cur[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        out += cur
        prev = cur
    return bytes(out)


# --------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------

class PdfDoc:
    def __init__(self, data: bytes):
        self.data = data
        self.offsets: Dict[int, int] = {}
        self.cache: Dict[int, Any] = {}
        self.compressed: Dict[int, Any] = {}
        self.unreadable = 0
        self.notes: List[str] = []
        for m in re.finditer(rb"(?<![\d.])(\d{1,7})\s+(\d{1,5})\s+obj\b", data):
            self.offsets[int(m.group(1))] = m.end()  # la dernière définition l'emporte (mises à jour incrémentales)
        self.trailer: Dict[str, Any] = {}
        for m in re.finditer(rb"trailer\s*", data):
            try:
                t = Lexer(data, m.end()).parse()
                if isinstance(t, dict):
                    self.trailer.update(t)
            except Exception:
                pass
        self._load_objstm()
        if not self.trailer.get("Root"):
            for num in list(self.offsets):
                o = self.get(num)
                if isinstance(o, Stream) and o.d.get("Type") == "XRef":
                    self.trailer.update(o.d)
        if "Encrypt" in self.trailer:
            raise Protected("PDF chiffré (déchiffrement non pris en charge par le lecteur intégré)")

    # -- accès ----------------------------------------------------------
    def get(self, ref: Any) -> Any:
        if isinstance(ref, Ref):
            num = ref.num
        elif isinstance(ref, int) and not isinstance(ref, bool):
            num = ref
        else:
            return ref
        if num in self.cache:
            return self.cache[num]
        if num in self.compressed:
            return self.compressed[num]
        off = self.offsets.get(num)
        if off is None:
            return None
        lx = Lexer(self.data, off)
        try:
            obj = lx.parse()
            lx.skip()
            if isinstance(obj, dict) and self.data[lx.p:lx.p + 6] == b"stream":
                p = lx.p + 6
                if self.data[p:p + 2] == b"\r\n":
                    p += 2
                elif self.data[p:p + 1] in (b"\n", b"\r"):
                    p += 1
                length = self.get(obj.get("Length"))
                raw = b""
                if isinstance(length, int) and length >= 0 and self.data[p + length:p + length + 20].lstrip(_WS).startswith(b"endstream"):
                    raw = self.data[p:p + length]
                else:
                    end = self.data.find(b"endstream", p)
                    raw = self.data[p:end if end >= 0 else len(self.data)].rstrip(b"\r\n")
                obj = Stream(obj, raw)
        except Exception:
            obj = None
        self.cache[num] = obj
        return obj

    def decode(self, st: Stream) -> bytes:
        d = st.d
        filters = self.get(d.get("Filter"))
        parms = self.get(d.get("DecodeParms") or d.get("DP"))
        if filters is None:
            return st.raw
        fl = filters if isinstance(filters, list) else [filters]
        pl = parms if isinstance(parms, list) else [parms] * len(fl)
        data = st.raw
        for f, p in zip(fl, pl + [None] * (len(fl) - len(pl))):
            f = str(self.get(f))
            p = self.get(p) if isinstance(p, (dict, Ref)) else p
            try:
                if f in ("FlateDecode", "Fl"):
                    do = zlib.decompressobj()
                    try:
                        data = do.decompress(data, MAX_STREAM)
                    except zlib.error:
                        data = zlib.decompressobj(-15).decompress(data[2:], MAX_STREAM)
                    if isinstance(p, dict) and (self.get(p.get("Predictor")) or 1) >= 10:
                        data = _png_predictor(data, int(self.get(p.get("Columns")) or 1), int(self.get(p.get("Colors")) or 1),
                                              int(self.get(p.get("BitsPerComponent")) or 8))
                elif f in ("ASCII85Decode", "A85"):
                    data = _ascii85(data)
                elif f in ("ASCIIHexDecode", "AHx"):
                    hx = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
                    data = bytes.fromhex((hx + (b"0" if len(hx) % 2 else b"")).decode())
                elif f in ("RunLengthDecode", "RL"):
                    data = _runlength(data)
                elif f in ("LZWDecode", "LZW"):
                    data = _lzw(data, int(self.get((p or {}).get("EarlyChange", 1)) if isinstance(p, dict) else 1))
                else:
                    return b""  # DCT, JPX, CCITT… : images, pas du texte
            except Exception:
                return b""
        return data

    def _load_objstm(self) -> None:
        for num, off in list(self.offsets.items()):
            head = self.data[off:off + 400]
            if b"/ObjStm" not in head:
                continue
            st = self.get(num)
            if not isinstance(st, Stream) or st.d.get("Type") != "ObjStm":
                continue
            body = self.decode(st)
            n = int(self.get(st.d.get("N")) or 0)
            first = int(self.get(st.d.get("First")) or 0)
            lx = Lexer(body, 0)
            pairs = []
            for _ in range(n):
                a, b = lx.parse(), lx.parse()
                if isinstance(a, int) and isinstance(b, int):
                    pairs.append((a, b))
            for onum, ooff in pairs:
                try:
                    self.compressed[onum] = Lexer(body, first + ooff).parse()
                except Exception:
                    pass

    # -- pages ----------------------------------------------------------------
    def pages(self) -> List[Dict[str, Any]]:
        root = self.get(self.trailer.get("Root"))
        if not isinstance(root, dict):
            root = next((o for n in list(self.offsets) + list(self.compressed) for o in [self.get(n)]
                         if isinstance(o, dict) and o.get("Type") == "Catalog"), None)
        out: List[Dict[str, Any]] = []
        if isinstance(root, dict) and root.get("Pages"):
            self._walk(self.get(root["Pages"]), {}, out, set())
        if not out:  # arbre cassé : toutes les pages, par numéro d'objet
            for num in sorted(set(self.offsets) | set(self.compressed)):
                o = self.get(num)
                if isinstance(o, dict) and o.get("Type") == "Page":
                    out.append(dict(o))
        return out[:MAX_PAGES]

    def _walk(self, node: Any, inherited: Dict[str, Any], out: List[Dict[str, Any]], seen: set) -> None:
        if not isinstance(node, dict) or id(node) in seen:
            return
        seen.add(id(node))
        inh = dict(inherited)
        for k in ("Resources", "MediaBox", "Rotate"):
            if k in node:
                inh[k] = node[k]
        if node.get("Type") == "Pages" or "Kids" in node:
            for kid in self.get(node.get("Kids")) or []:
                self._walk(self.get(kid), inh, out, seen)
        else:
            page = dict(node)
            for k, v in inh.items():
                page.setdefault(k, v)
            out.append(page)

    # -- polices -------------------------------------------------------------
    def font(self, fd: Any) -> "Font":
        fd = self.get(fd)
        key = id(fd)
        if key in _FONT_CACHE and _FONT_CACHE[key][0] is fd:
            return _FONT_CACHE[key][1]
        f = Font(self, fd if isinstance(fd, dict) else {})
        _FONT_CACHE[key] = (fd, f)
        return f

    # -- texte d'une page --------------------------------------------------------
    def page_interp(self, page: Dict[str, Any]) -> "Interp":
        contents = self.get(page.get("Contents"))
        streams: List[bytes] = []
        for c in (contents if isinstance(contents, list) else [contents]):
            st = self.get(c)
            if isinstance(st, Stream):
                streams.append(self.decode(st))
        interp = Interp(self, self.get(page.get("Resources")) or {})
        interp.run(b"\n".join(streams))
        self.unreadable += interp.unreadable
        return interp

    def page_text(self, page: Dict[str, Any]) -> str:
        return self.page_interp(page).render()


_FONT_CACHE: Dict[int, Tuple[Any, "Font"]] = {}

_ENC_PUNCT = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%", "ampersand": "&",
    "quotesingle": "'", "parenleft": "(", "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-",
    "period": ".", "slash": "/", "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">",
    "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\", "bracketright": "]", "asciicircum": "^",
    "underscore": "_", "grave": "`", "braceleft": "{", "bar": "|", "braceright": "}", "asciitilde": "~",
    "endash": "–", "emdash": "—", "quoteleft": "‘", "quoteright": "’", "quotedblleft": "“", "quotedblright": "”",
    "bullet": "•", "ellipsis": "…", "fi": "fi", "fl": "fl", "ff": "ff", "ffi": "ffi", "ffl": "ffl", "Euro": "€",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "minus": "−", "multiply": "×", "divide": "÷", "degree": "°", "guillemotleft": "«",
    "guillemotright": "»", "quotesinglbase": "‚", "quotedblbase": "„", "dagger": "†", "section": "§",
    "paragraph": "¶", "copyright": "©", "registered": "®", "trademark": "™", "nbspace": " ", "sfthyphen": "",
    "oe": "œ", "OE": "Œ", "ae": "æ", "AE": "Æ", "germandbls": "ß", "florin": "ƒ", "fraction": "⁄",
}


def glyph_to_unicode(name: str) -> Optional[str]:
    if name in _ENC_PUNCT:
        return _ENC_PUNCT[name]
    if len(name) == 1:
        return name
    m = re.match(r"^uni([0-9A-Fa-f]{4})", name) or re.match(r"^u([0-9A-Fa-f]{4,6})$", name)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return None
    cp = html.entities.name2codepoint.get(name)
    if cp:
        return chr(cp)
    base = name.split(".")[0]
    if base != name:
        return glyph_to_unicode(base)
    return None


class Font:
    def __init__(self, doc: PdfDoc, fd: Dict[str, Any]):
        self.doc = doc
        self.subtype = str(doc.get(fd.get("Subtype")) or "")
        self.composite = self.subtype == "Type0"
        self.cmap: Dict[int, str] = {}
        self.code_len = 2 if self.composite else 1
        self.differences: Dict[int, str] = {}
        self.base_enc = "cp1252"
        self.widths: Dict[int, float] = {}
        self.default_width = 500.0
        self.identity_unicode = False
        self.bold = bool(re.search(r"(?i)bold|black|heavy|demi", str(doc.get(fd.get("BaseFont")) or "")))
        tu = doc.get(fd.get("ToUnicode"))
        if isinstance(tu, Stream):
            self._parse_cmap(doc.decode(tu))
        enc = doc.get(fd.get("Encoding"))
        if isinstance(enc, Name) or isinstance(enc, str):
            self._base_enc(str(enc))
        elif isinstance(enc, dict):
            be = doc.get(enc.get("BaseEncoding"))
            if be:
                self._base_enc(str(be))
            code = 0
            for it in doc.get(enc.get("Differences")) or []:
                it = doc.get(it)
                if isinstance(it, int):
                    code = it
                elif isinstance(it, Name):
                    u = glyph_to_unicode(str(it))
                    if u is not None:
                        self.differences[code] = u
                    code += 1
        if self.composite:
            desc = doc.get(fd.get("DescendantFonts"))
            df = doc.get(desc[0]) if isinstance(desc, list) and desc else {}
            if isinstance(df, dict):
                self.default_width = float(doc.get(df.get("DW")) or 1000)
                self._parse_cid_widths(doc.get(df.get("W")) or [])
            if not self.cmap and str(enc or "") in ("Identity-H", "Identity-V"):
                self.identity_unicode = True  # à défaut de ToUnicode, on tente code = Unicode
        else:
            first = int(doc.get(fd.get("FirstChar")) or 0)
            for i, w in enumerate(doc.get(fd.get("Widths")) or []):
                w = doc.get(w)
                if isinstance(w, (int, float)):
                    self.widths[first + i] = float(w)
            mw = doc.get(fd.get("FontDescriptor"))
            if isinstance(mw, dict):
                self.default_width = float(doc.get(mw.get("MissingWidth")) or 500)

    def _base_enc(self, name: str) -> None:
        if "MacRoman" in name:
            self.base_enc = "mac_roman"
        elif "WinAnsi" in name:
            self.base_enc = "cp1252"
        elif "Standard" in name:
            self.base_enc = "latin-1"

    def _parse_cid_widths(self, arr: List[Any]) -> None:
        i = 0
        arr = [self.doc.get(a) for a in arr]
        while i < len(arr):
            c = arr[i]
            if i + 1 < len(arr) and isinstance(arr[i + 1], list):
                for k, w in enumerate(arr[i + 1]):
                    w = self.doc.get(w)
                    if isinstance(w, (int, float)):
                        self.widths[int(c) + k] = float(w)
                i += 2
            elif i + 2 < len(arr) and isinstance(arr[i + 1], int):
                for cc in range(int(c), min(int(arr[i + 1]), int(c) + 5000) + 1):
                    self.widths[cc] = float(arr[i + 2])
                i += 3
            else:
                i += 1

    def _parse_cmap(self, data: bytes) -> None:
        text = data.decode("latin-1")
        for blk in re.findall(r"begincodespacerange(.*?)endcodespacerange", text, re.S):
            m = re.search(r"<([0-9A-Fa-f]+)>", blk)
            if m:
                self.code_len = max(1, len(m.group(1)) // 2)

        def u16(h: str) -> str:
            b = bytes.fromhex(h if len(h) % 2 == 0 else "0" + h)
            return b.decode("utf-16-be", "ignore") if len(b) >= 2 else (b.decode("latin-1"))

        for blk in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
            for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk):
                self.cmap[int(a, 16)] = u16(b)
        for blk in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
            for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]*)>|\[(.*?)\])", blk, re.S):
                lo, hi = int(m.group(1), 16), int(m.group(2), 16)
                if hi - lo > 65535:
                    continue
                if m.group(3) is not None:
                    base = u16(m.group(3))
                    for k in range(hi - lo + 1):
                        self.cmap[lo + k] = (base[:-1] + chr(ord(base[-1]) + k)) if base else ""
                elif m.group(4) is not None:
                    for k, h in enumerate(re.findall(r"<([0-9A-Fa-f]*)>", m.group(4))):
                        self.cmap[lo + k] = u16(h)

    def decode(self, s: bytes) -> Tuple[str, float, int]:
        """Texte, largeur (millièmes d'em) et nombre de caractères non décodables d'une chaîne montrée."""
        out: List[str] = []
        width = 0.0
        bad = 0
        step = self.code_len if self.composite else 1
        for i in range(0, len(s) - step + 1, step):
            code = int.from_bytes(s[i:i + step], "big")
            width += self.widths.get(code, self.default_width)
            ch = self.cmap.get(code)
            if ch is None:
                if code in self.differences:
                    ch = self.differences[code]
                elif self.composite:
                    ch = chr(code) if self.identity_unicode and code >= 32 else None
                else:
                    try:
                        ch = bytes([code]).decode(self.base_enc)
                    except (UnicodeDecodeError, LookupError):
                        ch = None
            if ch is None:
                bad += 1
            else:
                out.append(ch)
        return "".join(out), width, bad


# --------------------------------------------------------------------------
# Interpréteur de flux de contenu
# --------------------------------------------------------------------------

_IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mul(a, b):
    return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])


class Frag:
    __slots__ = ("x", "y", "w", "size", "text", "bold")

    def __init__(self, x: float, y: float, w: float, size: float, text: str, bold: bool = False):
        self.x, self.y, self.w, self.size, self.text, self.bold = x, y, w, size, text, bold


class Interp:
    def __init__(self, doc: PdfDoc, resources: Dict[str, Any], depth: int = 0, ctm=_IDENT):
        self.doc, self.res, self.depth = doc, resources if isinstance(resources, dict) else {}, depth
        self.frags: List[Frag] = []
        self.unreadable = 0
        self.ctm = ctm
        self.stack: List[Tuple] = []
        self.tm = _IDENT
        self.tlm = _IDENT
        self.font: Optional[Font] = None
        self.size = 10.0
        self.leading = 0.0
        self.tc = 0.0
        self.tw = 0.0
        self.tz = 1.0
        self.rise = 0.0

    def run(self, data: bytes) -> None:
        lx = Lexer(data)
        ops: List[Any] = []
        n = len(data)
        while True:
            lx.skip()
            if lx.p >= n:
                break
            tok = lx.parse()
            if isinstance(tok, tuple) and tok and tok[0] == "op":
                op = tok[1]
                if op == "BI":  # image en ligne : on saute jusqu'à EI
                    m = re.compile(rb"\sEI(?=[\s\x00]|$)").search(data, lx.p)
                    lx.p = m.end() if m else n
                    ops = []
                    continue
                try:
                    self.op(op, ops)
                except Exception:
                    pass
                ops = []
            elif tok is not None or ops:
                ops.append(tok)
                if len(ops) > 512:
                    ops = ops[-64:]

    def font_of(self, name: str) -> Optional[Font]:
        fonts = self.doc.get(self.res.get("Font")) or {}
        fd = fonts.get(name) if isinstance(fonts, dict) else None
        return self.doc.font(fd) if fd is not None else None

    def op(self, op: str, a: List[Any]) -> None:
        f = lambda i: float(a[i]) if i < len(a) and isinstance(a[i], (int, float)) else 0.0  # noqa: E731
        if op == "q":
            self.stack.append((self.ctm, self.tm, self.tlm, self.font, self.size, self.leading, self.tc, self.tw, self.tz, self.rise))
        elif op == "Q":
            if self.stack:
                (self.ctm, self.tm, self.tlm, self.font, self.size, self.leading, self.tc, self.tw, self.tz, self.rise) = self.stack.pop()
        elif op == "cm" and len(a) >= 6:
            self.ctm = _mul((f(0), f(1), f(2), f(3), f(4), f(5)), self.ctm)
        elif op == "BT":
            self.tm = self.tlm = _IDENT
        elif op == "Tf" and len(a) >= 2:
            self.font = self.font_of(str(a[0]))
            self.size = f(1) or self.size
        elif op == "TL":
            self.leading = f(0)
        elif op == "Tc":
            self.tc = f(0)
        elif op == "Tw":
            self.tw = f(0)
        elif op == "Tz":
            self.tz = f(0) / 100.0 or 1.0
        elif op == "Ts":
            self.rise = f(0)
        elif op in ("Td", "TD"):
            if op == "TD":
                self.leading = -f(1)
            self.tlm = _mul((1, 0, 0, 1, f(0), f(1)), self.tlm)
            self.tm = self.tlm
        elif op == "Tm" and len(a) >= 6:
            self.tlm = self.tm = (f(0), f(1), f(2), f(3), f(4), f(5))
        elif op == "T*":
            self.tlm = _mul((1, 0, 0, 1, 0, -self.leading), self.tlm)
            self.tm = self.tlm
        elif op == "Tj" and a:
            self.show(a[0])
        elif op == "TJ" and a and isinstance(a[0], list):
            for it in a[0]:
                if isinstance(it, bytes):
                    self.show(it)
                elif isinstance(it, (int, float)):
                    adj = -float(it) / 1000.0 * self.size * self.tz
                    if it < -180:  # grand écart = espace entre mots
                        self.frags.append(Frag(*self._pos(), 0.0, self.size, " "))
                    self.tm = _mul((1, 0, 0, 1, adj, 0), self.tm)
        elif op == "'" and a:
            self.tlm = _mul((1, 0, 0, 1, 0, -self.leading), self.tlm)
            self.tm = self.tlm
            self.show(a[0])
        elif op == '"' and len(a) >= 3:
            self.tw, self.tc = f(0), f(1)
            self.tlm = _mul((1, 0, 0, 1, 0, -self.leading), self.tlm)
            self.tm = self.tlm
            self.show(a[2])
        elif op == "Do" and a and self.depth < 6:
            xo = self.doc.get(self.res.get("XObject")) or {}
            st = self.doc.get(xo.get(str(a[0]))) if isinstance(xo, dict) else None
            if isinstance(st, Stream) and st.d.get("Subtype") == "Form":
                sub = Interp(self.doc, self.doc.get(st.d.get("Resources")) or self.res, self.depth + 1, self.ctm)
                mat = self.doc.get(st.d.get("Matrix"))
                if isinstance(mat, list) and len(mat) == 6:
                    sub.ctm = _mul(tuple(float(self.doc.get(x)) for x in mat), self.ctm)
                sub.run(self.doc.decode(st))
                self.frags.extend(sub.frags)
                self.unreadable += sub.unreadable

    def _pos(self) -> Tuple[float, float]:
        m = _mul(self.tm, self.ctm)
        return m[4], m[5] + self.rise * m[3]

    def show(self, s: Any) -> None:
        if not isinstance(s, bytes) or self.font is None:
            return
        text, width, bad = self.font.decode(s)
        self.unreadable += bad
        m = _mul(self.tm, self.ctm)
        scale = (m[0] ** 2 + m[1] ** 2) ** 0.5 or 1.0
        adv = width / 1000.0 * self.size * self.tz + (self.tc + (self.tw if b" " in s else 0.0)) * len(text) * self.tz
        if text:
            x, y = m[4], m[5] + self.rise * m[3]
            self.frags.append(Frag(x, y, adv * scale, self.size * (abs(m[3]) if m[3] else 1.0), text, self.font.bold))
        self.tm = _mul((1, 0, 0, 1, adv, 0), self.tm)

    # -- mise en lignes ------------------------------------------------------------
    def render(self, body: float = 0.0, levels: Optional[List[Tuple[float, int]]] = None) -> str:
        """Texte de la page : une ligne par ligne visuelle, ligne vide entre paragraphes, titres balisés ⟪Hn⟫.

        ``body`` (corps de texte du document) et ``levels`` (tailles de titres → niveau) viennent de l'ensemble du document
        afin que les niveaux restent cohérents d'une page à l'autre.
        """
        frags = [f for f in self.frags if f.text]
        if not frags:
            return ""
        sizes = sorted(f.size for f in frags if f.size)
        med = sizes[len(sizes) // 2] if sizes else 10.0
        ordered = sorted(frags, key=lambda f: (-round(f.y / max(med * 0.35, 1.0)), f.x))
        lines: List[List[Frag]] = []
        for f in ordered:
            if lines and abs(lines[-1][0].y - f.y) <= max(med * 0.45, 1.5):
                lines[-1].append(f)
            else:
                lines.append([f])
        cols = _split_columns(lines, med)
        out_lines: List[str] = []
        for group in cols:
            ys = [ln[0].y for ln in group]
            pitch = _line_pitch(ys, med)
            prev_y: Optional[float] = None
            prev_head = 0
            for ln, y in zip(group, ys):
                ln.sort(key=lambda f: f.x)
                buf = ""
                end_x: Optional[float] = None
                widest = 0.0
                for f in ln:
                    if buf and end_x is not None:
                        gap = f.x - end_x
                        widest = max(widest, gap)
                        if gap > med * 0.18 and not buf.endswith(" ") and not f.text.startswith(" "):
                            buf += " "
                    buf += f.text
                    end_x = max(end_x or f.x, f.x + f.w)
                text = re.sub(r"[ \t]{2,}", " ", buf).strip()
                para_gap = prev_y is None or (pitch and prev_y - y > pitch + max(med * 0.3, pitch * 0.2))
                head = _heading_level(ln, text, body, levels or [], widest, med, bool(para_gap))
                if prev_y is not None and para_gap and not (head and head == prev_head and prev_y - y <= pitch * 1.3):
                    out_lines.append("")
                if head and head == prev_head and out_lines and out_lines[-1].startswith("⟪H"):
                    out_lines[-1] += " " + text               # titre sur plusieurs lignes
                else:
                    out_lines.append((_HEAD % head if head else "") + text)
                prev_y, prev_head = y, head
            out_lines.append("")
        return "\n".join(out_lines)


_HEAD = "⟪H%d⟫"


def _line_pitch(ys: List[float], med: float) -> float:
    """Interligne habituel : médiane des écarts entre lignes voisines (les grands écarts sont des sauts de paragraphe)."""
    gaps = sorted(a - b for a, b in zip(ys, ys[1:]) if 0 < a - b <= med * 2.6)
    return gaps[len(gaps) // 2] if gaps else 0.0


def _heading_level(ln: List[Frag], text: str, body: float, levels: List[Tuple[float, int]], widest_gap: float,
                   med: float, after_gap: bool) -> int:
    """0 si la ligne n'est pas un titre ; sinon niveau 1-5 déduit de la taille (ou du gras) de la police."""
    words = len(text.split())
    if not text or words > 16 or len(text) > 140 or text[-1] in ".,;" or widest_gap > med * 2.2 or not body:
        return 0
    visible = [f for f in ln if f.text.strip()]
    chars = sum(len(f.text.strip()) for f in visible) or 1
    big = sum(len(f.text.strip()) for f in visible if f.size >= body * 1.15)
    if big / chars >= 0.6:
        size = max(f.size for f in visible)
        for top, level in levels:
            if size >= top * 0.94:
                return level
    if after_gap and words <= 12 and all(f.bold for f in visible) and not re.fullmatch(r"[\d\W]+", text):
        return min((max((lv for _s, lv in levels), default=1) + 1) if levels else 2, 5)
    return 0


def doc_heading_levels(interps: List["Interp"]) -> Tuple[float, List[Tuple[float, int]]]:
    """Taille du corps de texte du document et paliers de taille des titres [(taille, niveau)], du plus grand au plus petit."""
    chars: Counter = Counter()
    for it in interps:
        for f in it.frags:
            if f.text.strip() and f.size:
                chars[round(f.size * 2) / 2] += len(f.text.strip())
    if not chars:
        return 0.0, []
    body = chars.most_common(1)[0][0]
    total = sum(chars.values())
    bigger = sorted((sz for sz, c in chars.items() if sz >= body * 1.15 and c <= total * 0.2), reverse=True)
    steps: List[float] = []
    for sz in bigger:
        if not steps or sz < steps[-1] * 0.94:      # tailles voisines (≤ 6 %) = même niveau
            steps.append(sz)
    return body, [(sz, i + 1) for i, sz in enumerate(steps[:4])]


def _split_columns(lines: List[List[Frag]], med: float) -> List[List[List[Frag]]]:
    """Détecte deux colonnes d'après la distribution des abscisses de départ et lit colonne par colonne."""
    if len(lines) < 12:
        return [lines]
    lo = min(f.x for ln in lines for f in ln)
    hi = max(f.x + f.w for ln in lines for f in ln)
    span = hi - lo
    if span < med * 20:
        return [lines]
    bin_w = span * 0.02
    from collections import Counter

    starts = Counter(int((f.x - lo) / bin_w) for ln in lines for f in ln)
    left_bin = starts.most_common(1)[0][0]
    if left_bin > 3:  # la marge gauche doit dominer
        return [lines]
    cand = [(c, b) for b, c in starts.items() if 0.35 * span < b * bin_w < 0.65 * span]
    if not cand:
        return [lines]
    cnt, mid_bin = max(cand)
    if cnt < len(lines) * 0.4:
        return [lines]
    mid = lo + mid_bin * bin_w - bin_w  # marge de tolérance à gauche de la seconde colonne
    left: List[List[Frag]] = []
    right: List[List[Frag]] = []
    for ln in lines:
        l = [f for f in ln if f.x < mid]
        r = [f for f in ln if f.x >= mid]
        if l and not r and max(f.x + f.w for f in l) > mid + bin_w * 3:  # ligne pleine largeur : sépare les blocs
            left.append(ln)
            continue
        if l:
            left.append(l)
        if r:
            right.append(r)
    return [left, right]


def extract_pages(data: bytes) -> Tuple[List[str], List[str]]:
    if not data.lstrip(b"\x00 \r\n\t").startswith(b"%PDF") and b"%PDF-" not in data[:1024]:
        raise Unsupported("signature PDF absente")
    doc = PdfDoc(data)
    pages = doc.pages()
    if not pages:
        raise Unsupported("aucune page trouvée")
    interps = [doc.page_interp(p) for p in pages]
    body, levels = doc_heading_levels(interps)
    texts = [it.render(body, levels) for it in interps]
    notes: List[str] = []
    if doc.unreadable:
        notes.append(f"{doc.unreadable} caractère(s) non décodable(s) (police sans table Unicode) — texte possiblement incomplet")
    if len(pages) >= MAX_PAGES:
        notes.append(f"lecteur intégré limité à {MAX_PAGES} pages")
    return texts, notes
