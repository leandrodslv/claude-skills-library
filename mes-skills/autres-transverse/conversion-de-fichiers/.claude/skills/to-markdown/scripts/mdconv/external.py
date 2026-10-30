"""Moteurs externes optionnels : détection FONCTIONNELLE, LibreOffice, rendu SVG/PDF, OCR.

Principe : un outil « installé » n'est pas un outil « qui marche » (ici, `soffice` peut exister sans
aucun module Writer/Calc/Impress). Chaque capacité est donc vérifiée par une vraie mini-conversion,
une seule fois par processus. Rien n'est jamais téléchargé ni envoyé sur le réseau.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_TIMEOUT = 180


# --------------------------------------------------------------------------
# Détection de base
# --------------------------------------------------------------------------

def which(*names: str) -> Optional[str]:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def run(cmd: Sequence[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None, input_bytes: Optional[bytes] = None) -> Tuple[int, bytes, bytes]:
    """Lance un processus sans shell, avec délai ; tue le groupe de processus au dépassement."""
    kw: Dict[str, object] = {}
    if os.name == "posix":
        kw["start_new_session"] = True
    try:
        p = subprocess.Popen(list(cmd), cwd=cwd, env=env, stdin=subprocess.PIPE if input_bytes else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)  # type: ignore[arg-type]
    except (OSError, ValueError) as exc:
        return 127, b"", str(exc).encode()
    try:
        out, err = p.communicate(input=input_bytes, timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
        except OSError:
            pass
        out, err = p.communicate()
        return 124, out, err + b"\n[delai depasse]"


# --------------------------------------------------------------------------
# LibreOffice
# --------------------------------------------------------------------------

_SOFFICE_CANDIDATES = ("soffice", "libreoffice", "soffice.bin")
_MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
_WIN_SOFFICE = (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe")


def soffice_path() -> Optional[str]:
    p = which(*_SOFFICE_CANDIDATES)
    if p:
        return p
    for cand in (_MAC_SOFFICE,) + _WIN_SOFFICE:
        if os.path.exists(cand):
            return cand
    return None


def _lo_env() -> Dict[str, str]:
    env = os.environ.copy()
    if sys.platform.startswith("linux") and not env.get("DISPLAY"):
        env.setdefault("SAL_USE_VCLPLUGIN", "svp")
    return env


def soffice_convert(files: Sequence[Path], fmt: str, outdir: Path, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Path]:
    """Convertit des fichiers via LibreOffice en un seul lancement (le démarrage domine le coût).

    ``fmt`` : « docx », « pdf », « png », « xlsx:Calc MS Excel 2007 XML »… Renvoie {nom source: fichier produit}.
    Un profil temporaire évite tout conflit avec une instance LibreOffice déjà ouverte par l'utilisateur.
    """
    exe = soffice_path()
    if not exe or not files:
        return {}
    outdir.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="mdconv_lo_")
    try:
        cmd = [exe, "--headless", "--norestore", "--nolockcheck", "--nodefault", "--nofirststartwizard",
               f"-env:UserInstallation={Path(profile).as_uri()}", "--convert-to", fmt, "--outdir", str(outdir)]
        cmd += [str(f) for f in files]
        run(cmd, timeout=timeout * max(1, min(len(files), 10)), env=_lo_env())
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    ext = fmt.split(":", 1)[0]
    out: Dict[str, Path] = {}
    for f in files:
        cand = outdir / (Path(f).stem + "." + ext)
        if cand.exists() and cand.stat().st_size > 0:
            out[str(f)] = cand
    return out


_FODT = ('<?xml version="1.0" encoding="UTF-8"?><office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
         'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2" '
         'office:mimetype="application/vnd.oasis.opendocument.text"><office:body><office:text><text:p>probe</text:p>'
         '</office:text></office:body></office:document>')
_FODS = ('<?xml version="1.0" encoding="UTF-8"?><office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
         'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
         'office:version="1.2" office:mimetype="application/vnd.oasis.opendocument.spreadsheet"><office:body><office:spreadsheet>'
         '<table:table table:name="T"><table:table-row><table:table-cell office:value-type="string"><text:p>probe</text:p>'
         '</table:table-cell></table:table-row></table:table></office:spreadsheet></office:body></office:document>')
_FODP = ('<?xml version="1.0" encoding="UTF-8"?><office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
         'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
         'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" office:version="1.2" '
         'office:mimetype="application/vnd.oasis.opendocument.presentation"><office:body><office:presentation>'
         '<draw:page draw:name="p1"/></office:presentation></office:body></office:document>')


@lru_cache(maxsize=1)
def libreoffice_modules() -> Dict[str, bool]:
    """Modules LibreOffice réellement fonctionnels : writer, calc, impress (test par conversion).

    Le processus principal sonde une fois et transmet le résultat aux processus fils par l'environnement.
    """
    res = {"writer": False, "calc": False, "impress": False}
    if not soffice_path():
        return res
    shared = os.environ.get("MDCONV_LO_MODULES")
    if shared is not None:
        return {k: (k in shared.split(",")) for k in res}
    tmp = Path(tempfile.mkdtemp(prefix="mdconv_probe_"))
    try:
        for key, ext, xml in (("writer", "fodt", _FODT), ("calc", "fods", _FODS), ("impress", "fodp", _FODP)):
            f = tmp / f"probe.{ext}"
            f.write_text(xml, encoding="utf-8")
            out = soffice_convert([f], "pdf", tmp / f"out_{key}", timeout=90)
            res[key] = bool(out)
            if not out and key == "writer":
                break  # sans Writer, inutile d'insister : le noyau LibreOffice est absent ou cassé
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def libreoffice_ok(kind: str = "writer") -> bool:
    try:
        ok = libreoffice_modules()
        os.environ.setdefault("MDCONV_LO_MODULES", ",".join(k for k, v in ok.items() if v))
        return ok.get(kind, False)
    except Exception:
        return False


# --------------------------------------------------------------------------
# Outils PDF / rendu
# --------------------------------------------------------------------------

@lru_cache(maxsize=None)
def tool(name: str) -> Optional[str]:
    return which(name)


def pdf_page_count(pdf: Path) -> Optional[int]:
    """Nombre de pages, sans dépendance (pdfinfo, sinon lecture des objets /Type /Page)."""
    if tool("pdfinfo"):
        rc, out, _ = run([tool("pdfinfo") or "pdfinfo", str(pdf)], timeout=30)
        m = re.search(rb"Pages:\s+(\d+)", out)
        if rc == 0 and m:
            return int(m.group(1))
    try:
        data = Path(pdf).read_bytes()
        n = len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
        m = re.findall(rb"/Count\s+(\d+)", data)
        return max(n, max((int(x) for x in m), default=0)) or None
    except OSError:
        return None


def render_pdf_pages(pdf: Path, pages: Sequence[int], dpi: int = 110, timeout: int = DEFAULT_TIMEOUT) -> Dict[int, bytes]:
    """Rend des pages PDF (numérotées à partir de 1) en PNG. Essaie pdftoppm, PyMuPDF, pypdfium2, mutool, gs."""
    out: Dict[int, bytes] = {}
    if not pages:
        return out
    tmp = Path(tempfile.mkdtemp(prefix="mdconv_pdf_"))
    try:
        if tool("pdftoppm"):
            for p in pages:
                rc, _o, _e = run([tool("pdftoppm") or "pdftoppm", "-png", "-r", str(dpi), "-f", str(p), "-l", str(p),
                                  "-singlefile", str(pdf), str(tmp / f"p{p}")], timeout=timeout)
                f = tmp / f"p{p}.png"
                if rc == 0 and f.exists():
                    out[p] = f.read_bytes()
            if out:
                return out
        if has_module("fitz"):
            import fitz  # type: ignore

            with fitz.open(str(pdf)) as doc:
                for p in pages:
                    if 1 <= p <= len(doc):
                        out[p] = doc[p - 1].get_pixmap(dpi=dpi).tobytes("png")
            if out:
                return out
        if has_module("pypdfium2") and has_module("PIL"):
            import pypdfium2 as pdfium  # type: ignore

            doc = pdfium.PdfDocument(str(pdf))
            try:
                for p in pages:
                    if 1 <= p <= len(doc):
                        import io

                        buf = io.BytesIO()
                        doc[p - 1].render(scale=dpi / 72).to_pil().save(buf, format="PNG")
                        out[p] = buf.getvalue()
            finally:
                doc.close()
            if out:
                return out
        if tool("mutool"):
            for p in pages:
                f = tmp / f"p{p}.png"
                rc, _o, _e = run([tool("mutool") or "mutool", "draw", "-r", str(dpi), "-o", str(f), str(pdf), str(p)], timeout=timeout)
                if rc == 0 and f.exists():
                    out[p] = f.read_bytes()
            if out:
                return out
        if tool("gs"):
            for p in pages:
                f = tmp / f"p{p}.png"
                rc, _o, _e = run([tool("gs") or "gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m", f"-r{dpi}",
                                  f"-dFirstPage={p}", f"-dLastPage={p}", f"-sOutputFile={f}", str(pdf)], timeout=timeout)
                if rc == 0 and f.exists():
                    out[p] = f.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def can_render_pdf() -> bool:
    return bool(tool("pdftoppm") or has_module("fitz") or (has_module("pypdfium2") and has_module("PIL")) or tool("mutool") or tool("gs"))


# --------------------------------------------------------------------------
# Rendu SVG → PNG
# --------------------------------------------------------------------------

_CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge")
_CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


@lru_cache(maxsize=1)
def chrome_path() -> Optional[str]:
    p = which(*_CHROME_NAMES)
    if p:
        return p
    for cand in _CHROME_PATHS:
        if os.path.exists(cand):
            return cand
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), os.path.expanduser("~/.cache/ms-playwright"), "/opt/pw-browsers"]
    for r in roots:
        if r and os.path.isdir(r):
            for sub in sorted(os.listdir(r), reverse=True):
                if sub.startswith("chromium"):
                    for rel in ("chrome-linux/chrome", "chrome-linux64/chrome", "chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
                        c = os.path.join(r, sub, rel)
                        if os.path.exists(c):
                            return c
    return None


def svg_renderers() -> List[str]:
    out = []
    if tool("rsvg-convert"):
        out.append("rsvg-convert")
    if tool("inkscape"):
        out.append("inkscape")
    if has_module("cairosvg"):
        out.append("cairosvg")
    if tool("magick") or tool("convert"):
        out.append("imagemagick")
    if chrome_path():
        out.append("chrome")
    if libreoffice_ok("writer") or libreoffice_ok("impress"):
        out.append("libreoffice")
    return out


def render_svg_bytes(svg: Path, width: int = 1400, timeout: int = 90) -> Optional[bytes]:
    tmp = Path(tempfile.mkdtemp(prefix="mdconv_svg_"))
    png = tmp / "out.png"
    try:
        if tool("rsvg-convert"):
            rc, out, _e = run([tool("rsvg-convert") or "rsvg-convert", "-w", str(width), "--keep-aspect-ratio", "-b", "white", str(svg)], timeout=timeout)
            if rc == 0 and out[:4] == b"\x89PNG":
                return out
        if tool("inkscape"):
            rc, _o, _e = run([tool("inkscape") or "inkscape", str(svg), "--export-type=png", f"--export-width={width}",
                              "--export-background=white", f"--export-filename={png}"], timeout=timeout)
            if rc == 0 and png.exists():
                return png.read_bytes()
        if has_module("cairosvg"):
            import cairosvg  # type: ignore

            data = cairosvg.svg2png(url=str(svg), output_width=width, background_color="white")
            if data:
                return data
        im = tool("magick") or tool("convert")
        if im:
            cmd = [im, "-background", "white", "-density", "150", str(svg), "-resize", f"{width}x", str(png)]
            rc, _o, _e = run(cmd, timeout=timeout)
            if rc == 0 and png.exists():
                return png.read_bytes()
        chrome = chrome_path()
        if chrome:
            rc, _o, _e = run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                              "--force-device-scale-factor=1", f"--screenshot={png}", f"--window-size={width},{int(width * 0.75)}",
                              svg.resolve().as_uri()], timeout=timeout)
            if png.exists():
                return png.read_bytes()
        if libreoffice_ok("writer") or libreoffice_ok("impress"):
            got = soffice_convert([svg], "png", tmp, timeout=timeout)
            for p in got.values():
                return p.read_bytes()
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None


def render_svg(svg: Path, ctx) -> Optional[str]:
    """Rend un SVG en PNG, l'enregistre comme asset et renvoie son lien relatif (ou None)."""
    if not ctx.opts.external:
        return None
    data = render_svg_bytes(Path(svg), timeout=min(ctx.opts.timeout, 90))
    if not data:
        return None
    link = ctx.add_asset(data, "png", stem=f"{Path(svg).stem}-rendu")
    return link


# --------------------------------------------------------------------------
# OCR
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def tesseract_langs() -> List[str]:
    exe = tool("tesseract")
    if not exe:
        return []
    rc, out, err = run([exe, "--list-langs"], timeout=30)
    text = (out + err).decode("utf-8", "replace")
    return [ln.strip() for ln in text.splitlines()[1:] if ln.strip() and ln.strip() != "osd"]


def pick_ocr_lang(requested: str = "") -> str:
    avail = tesseract_langs()
    if requested:
        wanted = [x for x in requested.split("+") if x in avail]
        return "+".join(wanted) or (avail[0] if avail else "eng")
    for combo in ("fra+eng", "eng"):
        if all(x in avail for x in combo.split("+")):
            return combo
    return avail[0] if avail else "eng"


def has_ocr() -> bool:
    return bool(tool("tesseract") and tesseract_langs())


def ocr_png(png: bytes, lang: str = "", timeout: int = 120) -> Tuple[str, float]:
    """OCR d'une image → (texte structuré en paragraphes, confiance moyenne 0-100)."""
    exe = tool("tesseract")
    if not exe:
        return "", 0.0
    tmp = Path(tempfile.mkdtemp(prefix="mdconv_ocr_"))
    try:
        f = tmp / "in.png"
        f.write_bytes(png)
        env = os.environ.copy()
        env["OMP_THREAD_LIMIT"] = "1"  # sans cela, chaque tesseract lance un thread par cœur : les lots parallèles s'écroulent
        rc, out, _e = run([exe, str(f), "stdout", "-l", pick_ocr_lang(lang), "--psm", "3", "tsv"], timeout=timeout, env=env)
        if rc != 0:
            return "", 0.0
        lines: Dict[Tuple[int, int, int], List[str]] = {}
        confs: List[float] = []
        para_of: Dict[Tuple[int, int, int], Tuple[int, int]] = {}
        for row in out.decode("utf-8", "replace").splitlines()[1:]:
            cols = row.split("\t")
            if len(cols) < 12 or cols[0] != "5":
                continue
            try:
                conf = float(cols[10])
            except ValueError:
                continue
            word = cols[11].strip()
            if not word or conf < 25:
                continue
            key = (int(cols[2]), int(cols[3]), int(cols[4]))
            lines.setdefault(key, []).append(word)
            para_of[key] = (int(cols[2]), int(cols[3]))
            confs.append(conf)
        paras: Dict[Tuple[int, int], List[str]] = {}
        for key in sorted(lines):
            paras.setdefault(para_of[key], []).append(" ".join(lines[key]))
        text = "\n\n".join(" ".join(v) for _k, v in sorted(paras.items()))
        return text.strip(), (sum(confs) / len(confs) if confs else 0.0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# Synthèse pour `--doctor`
# --------------------------------------------------------------------------

def capabilities(timeout: int = 90) -> Dict[str, object]:
    lo = libreoffice_modules() if soffice_path() else {"writer": False, "calc": False, "impress": False}
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "libreoffice": {"binaire": soffice_path(), **lo},
        "pandoc": which("pandoc"),
        "pdf": {k: which(k) for k in ("pdftotext", "pdftoppm", "pdfinfo", "mutool", "gs", "qpdf")},
        "ocr": {"tesseract": which("tesseract"), "langues": tesseract_langs(), "ocrmypdf": which("ocrmypdf")},
        "svg_renderers": svg_renderers(),
        "chrome": chrome_path(),
        "modules": {m: has_module(m) for m in (
            "markitdown", "pymupdf4llm", "fitz", "docling", "pdfplumber", "pypdf", "PyPDF2", "pdfminer", "pypdfium2", "PIL",
            "pytesseract", "cairosvg", "xlrd", "openpyxl", "mammoth", "bs4", "lxml", "defusedxml", "charset_normalizer",
            "faster_whisper", "whisper", "extract_msg", "olefile", "yaml")},
    }
