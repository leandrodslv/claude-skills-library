"""Détection du format par le CONTENU (signatures, structure ZIP/OLE, sniffing texte).

L'extension n'est qu'un indice : les entrants réels contiennent des « .xls » qui
sont du HTML, des « .doc » qui sont du docx renommé, des fichiers sans extension…
"""
from __future__ import annotations

import json
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from .util import decode_text

# extension -> langage pour les blocs de code
CODE_LANGS = {
    "py": "python", "pyw": "python", "js": "javascript", "mjs": "javascript", "cjs": "javascript",
    "jsx": "jsx", "ts": "typescript", "tsx": "tsx", "java": "java", "kt": "kotlin", "kts": "kotlin",
    "scala": "scala", "c": "c", "h": "c", "cc": "cpp", "cpp": "cpp", "cxx": "cpp", "hpp": "cpp",
    "cs": "csharp", "go": "go", "rs": "rust", "rb": "ruby", "php": "php", "swift": "swift",
    "sh": "bash", "bash": "bash", "zsh": "bash", "fish": "fish", "ps1": "powershell", "bat": "batch",
    "cmd": "batch", "sql": "sql", "r": "r", "lua": "lua", "pl": "perl", "dart": "dart", "css": "css",
    "scss": "scss", "sass": "sass", "less": "less", "toml": "toml", "ini": "ini", "cfg": "ini",
    "conf": "conf", "properties": "properties", "gradle": "groovy", "groovy": "groovy", "tf": "hcl",
    "proto": "protobuf", "graphql": "graphql", "gql": "graphql", "vue": "vue", "svelte": "svelte",
    "dockerfile": "dockerfile", "makefile": "makefile", "mk": "makefile", "cmake": "cmake",
    "vb": "vbnet", "vba": "vb", "m": "objectivec", "mm": "objectivec", "hs": "haskell", "ex": "elixir",
    "exs": "elixir", "erl": "erlang", "clj": "clojure", "jl": "julia", "nim": "nim", "zig": "zig",
    "sol": "solidity", "asm": "asm", "s": "asm", "vhd": "vhdl", "v": "verilog", "tex": "latex",
    "bib": "bibtex", "rst": "rst", "adoc": "asciidoc", "org": "org", "diff": "diff", "patch": "diff",
}

# format -> extensions « normales » (sert à signaler une extension trompeuse)
EXPECTED_EXT = {
    "docx": {"docx", "docm", "dotx", "dotm"}, "pptx": {"pptx", "pptm", "potx", "potm", "ppsx", "ppsm"},
    "xlsx": {"xlsx", "xlsm", "xltx", "xltm"}, "xlsb": {"xlsb"}, "doc": {"doc", "dot", "wps"},
    "ppt": {"ppt", "pps", "pot"}, "xls": {"xls", "xlt"}, "odt": {"odt", "ott", "fodt"},
    "odp": {"odp", "otp", "fodp"}, "ods": {"ods", "ots", "fods"}, "odg": {"odg", "otg"},
    "rtf": {"rtf"}, "pdf": {"pdf"}, "epub": {"epub"}, "svg": {"svg", "svgz"}, "html": {"html", "htm", "xhtml", "shtml"},
    "json": {"json", "geojson", "jsonc"}, "csv": {"csv", "tsv", "tab"}, "md": {"md", "markdown", "mdx"},
    "eml": {"eml"}, "msg": {"msg"}, "ipynb": {"ipynb"}, "vsdx": {"vsdx", "vssx", "vstx"},
    "drawio": {"drawio", "dio"}, "excalidraw": {"excalidraw"},
}

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "tif", "tiff", "ico", "heic", "heif", "avif", "jfif"}
AUDIO_EXTS = {"mp3", "wav", "m4a", "flac", "ogg", "oga", "opus", "aac", "wma", "aiff", "amr"}
VIDEO_EXTS = {"mp4", "mov", "mkv", "webm", "avi", "wmv", "flv", "m4v", "mpeg", "mpg", "3gp"}


@dataclass
class Detected:
    fmt: str                      # identifiant canonique (docx, pptx, svg, html, code, …)
    lang: str = ""                # langage, pour fmt == « code »
    note: str = ""                # précision (macros, chiffré…)
    ext_mismatch: bool = False    # l'extension ne correspond pas au contenu
    ext: str = ""

    @property
    def label(self) -> str:
        return f"{self.fmt}:{self.lang}" if self.lang else self.fmt


def detect(path) -> Detected:
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")
    lower = path.name.lower()
    if lower.endswith((".tar.gz", ".tgz")):
        ext = "tgz"
    elif lower.endswith((".tar.bz2", ".tbz2")):
        ext = "tbz2"
    elif lower.endswith((".tar.xz", ".txz")):
        ext = "txz"
    elif path.suffix == "" and lower in ("dockerfile", "makefile"):
        ext = lower
    size = path.stat().st_size
    if size == 0:
        return Detected("empty", ext=ext)
    with open(path, "rb") as f:
        head = f.read(65536)
    d = _sniff_binary(path, head, ext) or _sniff_text(head, ext, size)
    if d is None:
        d = Detected("binary")
    d.ext = ext
    exp = EXPECTED_EXT.get(d.fmt)
    if exp is not None and ext and ext not in exp and (ext in _ALL_KNOWN or ext in IMAGE_EXTS):
        d.ext_mismatch = True
    return d


_ALL_KNOWN: Set[str] = set().union(*EXPECTED_EXT.values())


# --------------------------------------------------------------------------
# Binaire
# --------------------------------------------------------------------------

def _sniff_binary(path: Path, head: bytes, ext: str) -> Optional[Detected]:
    if b"%PDF-" in head[:1024]:
        return Detected("pdf")
    if head[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return _sniff_zip(path, ext)
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return _sniff_ole(path, ext)
    if head[:5] == b"{\\rtf":
        return Detected("rtf")
    if head[:8] == b"fig-kiwi":
        return Detected("fig")
    if head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff" or head[:6] in (b"GIF87a", b"GIF89a") \
            or head[:2] == b"BM" and ext in IMAGE_EXTS or head[:4] in (b"II*\x00", b"MM\x00*") \
            or (head[:4] == b"RIFF" and head[8:12] == b"WEBP") or head[:4] == b"\x00\x00\x01\x00":
        return Detected("image")
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"mif1", b"msf1", b"heim", b"heis", b"avif", b"avis"):
            return Detected("image", note="heic/avif")
        if brand in (b"M4A ", b"M4B ", b"M4P ") or ext in ("m4a", "m4b"):
            return Detected("audio")
        return Detected("video")
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2") or head[:4] in (b"fLaC", b"OggS") \
            or (head[:4] == b"RIFF" and head[8:12] == b"WAVE"):
        return Detected("audio")
    if head[:4] == b"\x1a\x45\xdf\xa3" or (head[:4] == b"RIFF" and head[8:12] == b"AVI "):
        return Detected("video")
    if head[:2] == b"\x1f\x8b":
        return Detected("gz")
    if head[:3] == b"BZh":
        return Detected("bz2")
    if head[:6] == b"\xfd7zXZ\x00":
        return Detected("xz")
    if head[:6] == b"7z\xbc\xaf\x27\x1c":
        return Detected("7z")
    if head[:6] == b"Rar!\x1a\x07":
        return Detected("rar")
    if head[257:262] == b"ustar":
        return Detected("tar")
    if head[:16] == b"SQLite format 3\x00":
        return Detected("sqlite")
    if head[:4] == b"PAR1":
        return Detected("parquet")
    return None


def _sniff_zip(path: Path, ext: str) -> Detected:
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return Detected("zip", note="zip corrompu")
    with zf:
        raw = zf.namelist()
        names = {n.replace("\\", "/").lower() for n in raw}
        macros = "macros" if any(n.endswith("vbaproject.bin") for n in names) else ""
        if "[content_types].xml" in names:
            if "word/document.xml" in names:
                return Detected("docx", note=macros)
            if "ppt/presentation.xml" in names:
                return Detected("pptx", note=macros)
            if "xl/workbook.xml" in names:
                return Detected("xlsx", note=macros)
            if "xl/workbook.bin" in names:
                return Detected("xlsb")
            if "visio/document.xml" in names:
                return Detected("vsdx")
            if any(n.startswith("word/") for n in names):
                return Detected("docx", note=macros or "structure atypique")
            if any(n.startswith("ppt/") for n in names):
                return Detected("pptx", note=macros or "structure atypique")
            if any(n.startswith("xl/") for n in names):
                return Detected("xlsx", note=macros or "structure atypique")
            if "fixeddocumentsequence.fdseq" in names or any(n.endswith(".fdseq") for n in names):
                return Detected("xps")
        if "mimetype" in names:
            try:
                mt = zf.read(next(n for n in raw if n.replace("\\", "/").lower() == "mimetype")).decode("ascii", "ignore").strip()
            except Exception:
                mt = ""
            table = {
                "application/epub+zip": "epub",
                "application/vnd.oasis.opendocument.text": "odt",
                "application/vnd.oasis.opendocument.text-template": "odt",
                "application/vnd.oasis.opendocument.presentation": "odp",
                "application/vnd.oasis.opendocument.presentation-template": "odp",
                "application/vnd.oasis.opendocument.spreadsheet": "ods",
                "application/vnd.oasis.opendocument.spreadsheet-template": "ods",
                "application/vnd.oasis.opendocument.graphics": "odg",
                "application/vnd.oasis.opendocument.graphics-template": "odg",
            }
            if mt in table:
                return Detected(table[mt])
            if mt.startswith("application/vnd.oasis.opendocument."):
                return Detected("odf-other", note=mt.rsplit(".", 1)[-1])
        if "meta-inf/container.xml" in names and ext == "epub":
            return Detected("epub")
        if "canvas.fig" in names and "meta.json" in names:
            return Detected("fig", note="zip")
        if "document.json" in names and "meta.json" in names and any(n.startswith("pages/") for n in names):
            return Detected("sketch")
        if ext in ("pages", "key", "numbers") or "index/document.iwa" in names or "index.zip" in names:
            return Detected("iwork", note=ext)
        if "meta-inf/manifest.mf" in names or "androidmanifest.xml" in names:
            return Detected("zip", note="jar/apk")
    return Detected("zip")


def _sniff_ole(path: Path, ext: str) -> Detected:
    """Identifie un conteneur OLE2 (.doc/.ppt/.xls/.msg…) via les noms de son annuaire."""
    names = ole_directory_names(path)
    low = {n.lower() for n in names}
    if "encryptedpackage" in low or "encryptioninfo" in low:
        return Detected("encrypted", note="Office chiffré (mot de passe requis)")
    if "worddocument" in low:
        return Detected("doc")
    if "powerpoint document" in low:
        return Detected("ppt")
    if "workbook" in low or "book" in low:
        return Detected("xls")
    if any(n.startswith("__substg1.0_") or n == "__properties_version1.0" for n in low):
        return Detected("msg")
    if "visiodocument" in low:
        return Detected("vsd")
    if "quill" in low:
        return Detected("pub")
    by_ext = {"doc": "doc", "dot": "doc", "ppt": "ppt", "pps": "ppt", "xls": "xls", "xlt": "xls", "msg": "msg"}
    if ext in by_ext:
        return Detected(by_ext[ext], note="OLE non reconnu, d'après l'extension")
    return Detected("ole", note="conteneur OLE inconnu")


def ole_directory_names(path, max_sectors: int = 256) -> List[str]:
    """Lit l'annuaire d'un fichier OLE2/CFB (lecture minimale, sans dépendance)."""
    try:
        with open(path, "rb") as f:
            data = f.read(64 << 20)
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return []
        shift = struct.unpack_from("<H", data, 30)[0]
        if shift not in (9, 12):
            return []
        ssz = 1 << shift
        first_dir = struct.unpack_from("<I", data, 48)[0]
        n_difat = struct.unpack_from("<I", data, 72)[0]
        first_difat = struct.unpack_from("<I", data, 68)[0]
        difat = [x for x in struct.unpack_from("<109I", data, 76) if x < 0xFFFFFFF0]
        sec = first_difat
        for _ in range(min(n_difat, 64)):
            if sec >= 0xFFFFFFF0:
                break
            off = (sec + 1) * ssz
            vals = struct.unpack_from("<%dI" % (ssz // 4), data, off)
            difat += [x for x in vals[:-1] if x < 0xFFFFFFF0]
            sec = vals[-1]
        fat: List[int] = []
        for s in difat[:4096]:
            off = (s + 1) * ssz
            if off + ssz > len(data):
                break
            fat += struct.unpack_from("<%dI" % (ssz // 4), data, off)
        names: List[str] = []
        sec, hops = first_dir, 0
        while sec < 0xFFFFFFF0 and hops < max_sectors:
            off = (sec + 1) * ssz
            if off + ssz > len(data):
                break
            for i in range(ssz // 128):
                ent = data[off + i * 128: off + (i + 1) * 128]
                nlen = struct.unpack_from("<H", ent, 64)[0]
                if 2 <= nlen <= 64 and ent[66] in (1, 2, 5):
                    names.append(ent[: nlen - 2].decode("utf-16-le", "replace"))
            sec = fat[sec] if sec < len(fat) else 0xFFFFFFFE
            hops += 1
        return names
    except (OSError, struct.error, IndexError):
        return []


# --------------------------------------------------------------------------
# Texte
# --------------------------------------------------------------------------

_HTML_START = re.compile(
    r"(?is)^\s*(?:<\?xml[^>]*>\s*)?(?:<!--.*?-->\s*)*"
    r"(?:<!doctype\s+html|<html|<head|<body|<meta\s|<title|<div|<p[\s>]|<table|<h[1-6][\s>]|<ul|<ol|<span|<a\s|<center|<font)"
)
_EML_HEAD = re.compile(r"^(?:From|Received|Return-Path|MIME-Version|Date|Subject|To|Message-ID|X-[\w-]+):", re.M)


def _decode_head(head: bytes) -> str:
    for cut in (0, 1, 2, 3):
        try:
            return (head[:-cut] if cut else head).decode("utf-8")
        except UnicodeDecodeError:
            continue
    return decode_text(head)[0]


def _sniff_text(head: bytes, ext: str, size: int) -> Optional[Detected]:
    sample = head[:8192]
    is_utf16 = head[:2] in (b"\xff\xfe", b"\xfe\xff")
    if b"\x00" in sample and not is_utf16:
        return None  # binaire non identifié
    text = (decode_text(head)[0] if is_utf16 else _decode_head(head)).lstrip("﻿")
    t = text.lstrip()
    low = t[:4096].lower()

    if low.startswith(("<mxfile", "<mxgraphmodel")) or (low.startswith("<?xml") and ("<mxfile" in low or "<mxgraphmodel" in low)):
        return Detected("drawio")
    # Un SVG exporté par draw.io porte le graphe dans un attribut (« &lt;mxfile »)
    # et reste un SVG : le convertisseur SVG sait l'y retrouver.
    if re.search(r"<svg[\s>]", low) and (low.startswith(("<svg", "<?xml", "<!doctype svg", "<!--")) or ext == "svg"):
        return Detected("svg")
    if 'progid="excel.sheet"' in low:
        return Detected("xml2003-sheet")
    if 'progid="word.document"' in low:
        return Detected("xml2003-word")
    if t[:200].lower().startswith(("mime-version:", "from:", "content-type:")) and "multipart/related" in low and ext in ("mht", "mhtml"):
        return Detected("mhtml")
    if ext in ("mht", "mhtml"):
        return Detected("mhtml")
    if ext in ("fodt", "fods", "fodp") and "<office:document" in low:
        return Detected({"fodt": "odt", "fods": "ods", "fodp": "odp"}[ext], note="flat-odf")
    if ext in ("html", "htm", "xhtml", "shtml") or _HTML_START.match(t):
        return Detected("html")
    if ext in ("xls", "doc", "xlsx", "docx") and (low.startswith("<") and ("<table" in low or "<html" in low or "<body" in low)):
        return Detected("html", note="HTML déguisé en " + ext)
    if low.startswith("<?xml") or (low.startswith("<") and re.match(r"<[A-Za-z_][\w:.-]*[\s>/]", t)):
        if re.search(r"<(rss|feed)[\s>]", low):
            return Detected("feed")
        return Detected("xml")
    if ext == "ipynb" or ('"nbformat"' in text[:4096] and t.startswith("{")):
        return Detected("ipynb")
    if ext == "excalidraw" or ('"type": "excalidraw"' in text[:2048] or '"type":"excalidraw"' in text[:2048]):
        return Detected("excalidraw")
    if ext in ("jsonl", "ndjson"):
        return Detected("jsonl")
    if t[:1] in "{[" and (ext in ("json", "geojson", "jsonc", "") or _looks_json(text, size)):
        return Detected("json")
    if ext in ("json", "geojson", "jsonc"):
        return Detected("json")
    if ext == "eml" or (_EML_HEAD.match(t) and len(_EML_HEAD.findall(t[:2000])) >= 3):
        return Detected("eml")
    if ext == "mbox":
        return Detected("mbox")
    if ext in ("md", "markdown", "mdx"):
        return Detected("md")
    if ext in ("csv", "tsv", "tab"):
        return Detected("csv")
    if ext in ("yaml", "yml"):
        return Detected("yaml")
    if ext in ("tex", "rst", "adoc", "org", "textile", "wiki", "mediawiki", "dokuwiki", "asciidoc"):
        return Detected("markup", lang=CODE_LANGS.get(ext, ext))
    if ext in CODE_LANGS:
        return Detected("code", lang=CODE_LANGS[ext])
    if ext in ("txt", "text", "log", "out", "asc", "nfo", ""):
        return Detected("txt")
    return Detected("txt", note=f"extension .{ext} inconnue, lu comme texte")


def _looks_json(text: str, size: int) -> bool:
    if size <= 65536:
        try:
            json.loads(text)
            return True
        except ValueError:
            return False
    return bool(re.match(r'\s*[\[{]\s*("|\{|\[|\d|\]|\})', text))
