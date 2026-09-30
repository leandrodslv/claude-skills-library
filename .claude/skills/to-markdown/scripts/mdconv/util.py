"""Utilitaires partagés : texte/Markdown, XML et ZIP sûrs, métadonnées d'images.

Tout ici est en bibliothèque standard uniquement : le noyau du skill doit
fonctionner sur une machine où rien n'a été installé.
"""
from __future__ import annotations

import hashlib
import posixpath
import re
import struct
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .encodings import guess_legacy_codepage, refine_western

# --------------------------------------------------------------------------
# Texte
# --------------------------------------------------------------------------

# Caractères invisibles sans valeur sémantique : espace de largeur nulle,
# word joiner, BOM, trait d'union conditionnel. ZWJ/ZWNJ sont conservés
# (nécessaires au persan, aux écritures indiennes et aux emojis composés).
_INVISIBLE = dict.fromkeys(map(ord, "​⁠﻿­"), None)
# Espaces typographiques ramenés à l'espace simple (l'espace insécable
# français avant « : » ou « ? » produirait des jetons parasites pour une IA).
_SPACES = {ord(c): " " for c in "          　"}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CJK = "぀-ヿ㐀-䶿一-鿿가-힯"
_CJK_RE = re.compile("([" + _CJK + "])")
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)  # « _ » sert de marqueur d'italique : pas un caractère de mot


def clean_text(s: str) -> str:
    """Normalise un texte extrait : invisibles retirés, espaces uniformisés, NFC."""
    if not s:
        return ""
    s = s.translate(_INVISIBLE).translate(_SPACES)
    s = _CONTROL.sub("", s)
    return unicodedata.normalize("NFC", s)


def collapse_ws(s: str) -> str:
    """Remplace toute suite d'espaces/retours par une seule espace."""
    return re.sub(r"\s+", " ", s).strip()


def words(text: str) -> List[str]:
    """Découpe en « mots » comparables ; chaque caractère CJK compte comme un mot."""
    text = _CJK_RE.sub(r" \1 ", unicodedata.normalize("NFKC", text).lower())
    return _WORD_RE.findall(text)


_MD_MARKUP = re.compile(r"`|\*|~~|\\(?=[\\`*_{}\[\]()#+\-.!|<>~&])|<br\s*/?>|</?(?:sup|sub|ins|del|u|mark)>")


def md_plain(md: str) -> str:
    """Retire les marqueurs de mise en forme pour comparer le texte seul (`m`² → m²)."""
    return _MD_MARKUP.sub(lambda m: " " if m.group(0).startswith("<br") else "", md)


def word_recall(src_text: str, md_text: str) -> float:
    """Part (0-1) des mots de la source retrouvés dans le Markdown, multiplicité respectée."""
    src = Counter(words(src_text))
    total = sum(src.values())
    if not total:
        return 1.0
    out = Counter(words(md_plain(md_text)))
    hit = sum(min(c, out.get(w, 0)) for w, c in src.items())
    return hit / total


def est_tokens(text: str) -> int:
    """Estimation grossière du nombre de jetons (≈ 3,7 caractères/jeton, CJK ≈ 1/caractère)."""
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    return int(cjk + (len(text) - cjk) / 3.7) + 1


def sha256_file(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def human_bytes(n: float) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} Go"


def slugify(name: str, keep_dots: bool = False) -> str:
    """Nom de fichier sûr, lisible, sans accents ni séparateurs de chemin."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    pattern = r"[^A-Za-z0-9._-]+" if keep_dots else r"[^A-Za-z0-9_-]+"
    s = re.sub(pattern, "-", s).strip("-._")
    return s[:80] or "fichier"


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

_BLOCK_START = re.compile(r"^(\s{0,3})(#{1,6}(\s|$)|>|[-+*](\s|$)|\d{1,9}[.)](\s|$)|={3,}\s*$|-{3,}\s*$|`{3,}|~{3,})")


def esc_inline(s: str) -> str:
    """Échappe le strict nécessaire pour qu'un texte brut ne crée pas de Markdown involontaire.

    On évite l'échappement systématique (« \\[1\\] » alourdit la lecture par une
    IA) : seuls les caractères réellement ambigus sont traités.
    """
    if not s:
        return s
    s = s.replace("\\", "\\\\")
    s = s.replace("`", "\\`")
    s = s.replace("*", "\\*")
    s = re.sub(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])", r"\\_", s)
    s = s.replace("](", "]\\(").replace("][", "]\\[")
    s = re.sub(r"<(?=[A-Za-z/!?])", r"\\<", s)
    s = s.replace("~~", "\\~\\~")
    s = re.sub(r"&(?=#?\w+;)", r"\\&", s)
    return s


def esc_block_start(s: str) -> str:
    """Neutralise un début de ligne qui serait pris pour un titre, une liste, une citation…"""
    m = _BLOCK_START.match(s)
    if not m:
        return s
    lead, rest = s[: m.end(1)], s[m.end(1):]
    if rest[:1].isdigit():
        return lead + re.sub(r"^(\d+)([.)])", r"\1\\\2", rest, count=1)
    return lead + "\\" + rest


def cell(md: str) -> str:
    """Prépare du Markdown inline pour une cellule de tableau GFM."""
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    md = re.sub(r"\n{2,}", "\n", md.strip())
    md = md.replace("\n", "<br>")
    md = md.replace("|", "\\|")
    return md.strip()


def md_table(rows: Sequence[Sequence[str]], header: bool = True) -> str:
    """Rend une matrice de cellules (déjà en Markdown inline) en tableau GFM.

    La première ligne sert d'en-tête (GFM l'exige) ; si ``header`` est faux,
    un en-tête vide est ajouté pour rester valide.
    """
    rows = [list(r) for r in rows if r is not None]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    if width == 0:
        return ""
    rows = [[cell(c) for c in r] + [""] * (width - len(r)) for r in rows]
    if not header:
        rows.insert(0, [""] * width)
    head, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def fence(code: str, lang: str = "") -> str:
    """Bloc de code clôturé ; la clôture s'allonge si le code contient déjà des ```."""
    longest = max((len(m) for m in re.findall(r"`{3,}", code)), default=2)
    bar = "`" * max(3, longest + 1)
    return f"{bar}{lang}\n{code.rstrip(chr(10))}\n{bar}"


def indent(text: str, prefix: str) -> str:
    return "\n".join((prefix + ln) if ln.strip() else ln for ln in text.split("\n"))


def wrap_emphasis(text: str, bold: bool, italic: bool, strike: bool = False, code: bool = False,
                  intraword: bool = False) -> str:
    """Applique gras/italique/barré/code sans casser CommonMark.

    Les espaces de bord sont sortis des marqueurs (« ** a ** » n'est pas du
    gras valide) et un texte vide/blanc reste tel quel. L'italique s'écrit
    « _x_ » (jamais collé à « ** » du gras voisin) sauf au milieu d'un mot,
    où seul « *x* » est valide.
    """
    if not text or not text.strip():
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    core = text.strip()
    if code:
        ticks = "`" * (max((len(m) for m in re.findall(r"`+", core)), default=0) + 1)
        pad = " " if core.startswith("`") or core.endswith("`") else ""
        core = f"{ticks}{pad}{core}{pad}{ticks}"
    else:
        if italic:
            m = "*" if intraword else "_"
            core = f"{m}{core}{m}"
        if bold:
            core = f"**{core}**"
        if strike:
            core = f"~~{core}~~"
    return lead + core + trail


def normalize_markdown(md: str) -> str:
    """Nettoyage final : fins de ligne, espaces de fin, lignes vides multiples."""
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    in_fence = False
    fence_mark = ""
    blank = 0
    for line in md.split("\n"):
        stripped = line.strip()
        m = re.match(r"^(`{3,}|~{3,})", stripped)
        if m:
            if not in_fence:
                in_fence, fence_mark = True, m.group(1)[0] * 3
            elif stripped.startswith(fence_mark) and set(stripped) <= {fence_mark[0]}:
                in_fence = False
        if in_fence:
            out.append(line.rstrip("\n"))
            blank = 0
            continue
        line = line.rstrip()
        if not line:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(line)
    return "\n".join(out).strip("\n") + "\n"


# --------------------------------------------------------------------------
# XML sûr
# --------------------------------------------------------------------------

class UnsafeXML(ValueError):
    """XML refusé : déclarations d'entités (XXE, « billion laughs »)."""


_XML_BAD = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def parse_xml(data: bytes) -> ET.Element:
    """Parse un XML non fiable. Refuse les entités déclarées, tolère les caractères de contrôle."""
    probe = (b"<!ENTITY", "<!ENTITY".encode("utf-16-le"), "<!ENTITY".encode("utf-16-be"))
    if any(p in data for p in probe):
        raise UnsafeXML("déclaration d'entité XML refusée (XXE / billion laughs)")
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        cleaned = _XML_BAD.sub(b"", data)
        if cleaned != data:
            return ET.fromstring(cleaned)
        raise


def local(tag: str) -> str:
    """Nom local d'une balise ElementTree (« {ns}nom » → « nom »)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def q(ns: str, name: str) -> str:
    return "{%s}%s" % (ns, name)


# --------------------------------------------------------------------------
# ZIP sûr et relations OPC
# --------------------------------------------------------------------------

class UnsafeArchive(ValueError):
    """Archive refusée : trop volumineuse, trop de membres ou ratio suspect (zip bomb)."""


class _CappedStream:
    """Enveloppe un flux ZIP : compte les octets lus (le ``file_size`` déclaré peut mentir) et peut rendre des octets déjà lus."""

    def __init__(self, raw, cap: int, name: str):
        self.raw, self.cap, self.name, self.count = raw, cap, name, 0
        self._pending = b""

    def unread(self, data: bytes) -> None:
        self._pending = data + self._pending
        self.count -= len(data)

    def read(self, n: int = -1) -> bytes:
        if self._pending:
            if n < 0 or n >= len(self._pending):
                out, self._pending = self._pending, b""
                if n < 0:
                    return out + self.read(-1)
                return out
            out, self._pending = self._pending[:n], self._pending[n:]
            return out
        data = self.raw.read(n if n >= 0 else 1 << 20)
        self.count += len(data)
        if self.count > self.cap:
            raise UnsafeArchive(f"membre trop volumineux : {self.name}")
        if n < 0 and data:
            return data + self.read(-1)
        return data

    def close(self) -> None:
        self.raw.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


class SafeZip:
    """Accès en lecture à un ZIP avec plafonds de taille et recherche insensible à la casse."""

    def __init__(self, path, max_total: int = 2 << 30, max_member: int = 512 << 20, max_files: int = 100_000):
        self.path = str(path)
        self.max_member = max_member
        self.zf = zipfile.ZipFile(self.path)
        infos = self.zf.infolist()
        if len(infos) > max_files:
            raise UnsafeArchive(f"trop de membres ({len(infos)})")
        if sum(i.file_size for i in infos) > max_total:
            raise UnsafeArchive("taille décompressée totale excessive")
        self._index: Dict[str, zipfile.ZipInfo] = {}
        self._lower: Dict[str, str] = {}
        for i in infos:
            if i.is_dir():
                continue
            name = self.norm(i.filename)
            self._index[name] = i
            self._lower.setdefault(name.lower(), name)

    @staticmethod
    def norm(name: str) -> str:
        name = name.replace("\\", "/")
        while name.startswith("./"):
            name = name[2:]
        return name.lstrip("/")

    def names(self) -> List[str]:
        return list(self._index)

    def has(self, name: str) -> bool:
        return self.resolve(name) is not None

    def resolve(self, name: str) -> Optional[str]:
        name = self.norm(name)
        if name in self._index:
            return name
        return self._lower.get(name.lower())

    def read(self, name: str, limit: Optional[int] = None) -> bytes:
        real = self.resolve(name)
        if real is None:
            raise KeyError(name)
        cap = limit if limit is not None else self.max_member
        info = self._index[real]
        if info.file_size > cap and limit is None:
            raise UnsafeArchive(f"membre trop volumineux : {real} ({info.file_size} o)")
        with self.zf.open(info) as f:
            data = f.read(cap + 1)
        if limit is None and len(data) > cap:
            raise UnsafeArchive(f"membre trop volumineux : {real}")
        return data[:cap] if limit is not None else data

    def read_opt(self, name: str) -> Optional[bytes]:
        try:
            return self.read(name)
        except KeyError:
            return None

    def stream(self, name: str):
        """Flux de lecture d'un membre, sans le charger en mémoire ; lève UnsafeArchive au-delà du plafond de taille."""
        real = self.resolve(name)
        if real is None:
            raise KeyError(name)
        info = self._index[real]
        if info.file_size > self.max_member:
            raise UnsafeArchive(f"membre trop volumineux : {real} ({info.file_size} o)")
        return _CappedStream(self.zf.open(info), self.max_member, real)

    def size(self, name: str) -> int:
        real = self.resolve(name)
        return self._index[real].file_size if real else 0

    def xml(self, name: str) -> Optional[ET.Element]:
        data = self.read_opt(name)
        if data is None:
            return None
        try:
            return parse_xml(data)
        except (ET.ParseError, UnsafeXML):
            return None

    def close(self) -> None:
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class Rels:
    """Relations d'une partie OPC (« word/_rels/document.xml.rels »)."""

    def __init__(self, zf: SafeZip, part: str):
        self.part = part
        self.base = posixpath.dirname(part)
        self.by_id: Dict[str, Tuple[str, str, bool]] = {}
        rels_name = posixpath.join(self.base, "_rels", posixpath.basename(part) + ".rels")
        root = zf.xml(rels_name)
        if root is None:
            return
        for r in root:
            if local(r.tag) != "Relationship":
                continue
            rid, typ, target = r.get("Id"), r.get("Type", ""), r.get("Target", "")
            external = r.get("TargetMode") == "External"
            if not external:
                target = self.resolve(target)
            self.by_id[rid] = (typ.rsplit("/", 1)[-1], target, external)

    def resolve(self, target: str) -> str:
        if target.startswith("/"):
            return target.lstrip("/")
        return posixpath.normpath(posixpath.join(self.base, target))

    def target(self, rid: Optional[str]) -> Optional[str]:
        return self.by_id[rid][1] if rid in self.by_id else None

    def is_external(self, rid: Optional[str]) -> bool:
        return bool(rid in self.by_id and self.by_id[rid][2])

    def type(self, rid: Optional[str]) -> str:
        return self.by_id[rid][0] if rid in self.by_id else ""

    def of_type(self, typ: str) -> List[Tuple[str, str]]:
        return [(rid, t) for rid, (ty, t, _e) in self.by_id.items() if ty == typ]


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------

_MIME = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
    "bmp": "image/bmp", "webp": "image/webp", "tif": "image/tiff", "tiff": "image/tiff",
    "svg": "image/svg+xml", "emf": "image/emf", "wmf": "image/wmf", "ico": "image/x-icon",
}


def image_info(data: bytes) -> Tuple[str, Optional[int], Optional[int]]:
    """(format, largeur, hauteur) lus dans l'en-tête, sans dépendance. Format « ? » si inconnu."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return "png", w, h
        if data[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", data[6:10])
            return "gif", w, h
        if data[:2] == b"BM":
            w, h = struct.unpack("<ii", data[18:26])
            return "bmp", w, abs(h)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            kind = data[12:16]
            if kind == b"VP8X":
                w = 1 + int.from_bytes(data[24:27], "little")
                h = 1 + int.from_bytes(data[27:30], "little")
                return "webp", w, h
            if kind == b"VP8L":
                b = data[21:25]
                bits = int.from_bytes(b, "little")
                return "webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if kind == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return "webp", w & 0x3FFF, h & 0x3FFF
            return "webp", None, None
        if data[:3] == b"\xff\xd8\xff":
            i = 2
            n = len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = struct.unpack(">H", data[i + 2:i + 4])[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return "jpg", w, h
                i += 2 + seg
            return "jpg", None, None
        if data[:4] in (b"II*\x00", b"MM\x00*"):
            return "tiff", None, None
        if data[:4] == b"\x01\x00\x00\x00" and data[40:44] == b" EMF":
            return "emf", None, None
        if data[:4] == b"\xd7\xcd\xc6\x9a":
            return "wmf", None, None
        head = data[:512].lstrip()
        if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048]):
            return "svg", None, None
    except (struct.error, IndexError):
        pass
    return "?", None, None


def mime_for(ext: str) -> str:
    return _MIME.get(ext.lower().lstrip("."), "application/octet-stream")


def ext_from_bytes(data: bytes, fallback: str = "bin") -> str:
    fmt, _w, _h = image_info(data)
    return fmt if fmt != "?" else fallback


# --------------------------------------------------------------------------
# Divers
# --------------------------------------------------------------------------

def decode_text(data: bytes) -> Tuple[str, str]:
    """Décode un texte d'encodage inconnu → (texte, encodage).

    BOM, puis UTF-8 strict. Sinon : un texte occidental (français…) n'a que quelques octets accentués, donc cp1252
    (ou cp1250/cp1254 sur indices nets) si moins de 15 % d'octets ≥ 0x80 ou s'ils sont isolés ; au-delà (cyrillique,
    grec, hébreu, arabe, CJK) une devinette sans dépendance (``encodings``) ; en dernier recours charset_normalizer
    s'il est présent, sinon cp1252/latin-1. Le résultat ne dépend donc pas des modules installés.
    """
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", "replace"), "utf-8-sig"
    if data[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"):
        return data.decode("utf-32", "replace"), "utf-32"
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    sample = data[:200_000]
    high = sum(1 for b in sample if b >= 0x80)
    # en occidental les octets accentués sont isolés (é, à) ; en cyrillique/grec/CJK ils forment de longues suites
    long_runs = sum(len(r) for r in re.findall(rb"[\x80-\xff]{3,}", sample))
    if high / max(len(sample), 1) <= 0.15 or (high and long_runs / high <= 0.15):
        enc = refine_western(data)
        return data.decode(enc, "replace"), enc
    enc = guess_legacy_codepage(sample)          # alphabets non latins et CJK, sans dépendance
    if enc is None:
        enc = refine_western(data)
        if enc == "cp1252":                      # aucun indice net : la bibliothèque tierce, si elle est présente, a peut-être un avis
            try:
                from charset_normalizer import from_bytes  # type: ignore

                best = from_bytes(data).best()
                if best is not None:
                    return str(best), best.encoding
            except Exception:
                pass
    try:
        return data.decode(enc), enc
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def first(items: Iterable, default=None):
    for x in items:
        return x
    return default


def dedupe(seq: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# --------------------------------------------------------------------------
# HTML minimal (libellés de diagrammes, foreignObject…)
# --------------------------------------------------------------------------

def html_to_text(fragment: str) -> str:
    """Texte brut d'un fragment HTML : balises retirées, blocs et <br> → retours à la ligne."""
    from html.parser import HTMLParser

    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out: List[str] = []
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1
            elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
                self.out.append("\n")

        def handle_endtag(self, tag):
            if tag in ("script", "style") and self.skip:
                self.skip -= 1
            elif tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"):
                self.out.append("\n" if tag not in ("td", "th") else " ")

        def handle_data(self, data):
            if not self.skip:
                self.out.append(data)

    p = _P()
    try:
        p.feed(fragment)
        p.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", fragment)
    text = "".join(p.out)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def parse_xml_keep_comments(data: bytes) -> ET.Element:
    """Comme parse_xml, mais conserve les commentaires (sources de texte des SVG matplotlib, charges Excalidraw)."""
    probe = (b"<!ENTITY", "<!ENTITY".encode("utf-16-le"), "<!ENTITY".encode("utf-16-be"))
    if any(p in data for p in probe):
        raise UnsafeXML("déclaration d'entité XML refusée (XXE / billion laughs)")
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        parser.feed(data)
        return parser.close()
    except ET.ParseError:
        cleaned = _XML_BAD.sub(b"", data)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        parser.feed(cleaned)
        return parser.close()
