"""PDF → Markdown : cascade de moteurs, reflow, puis escalade OCR → lecture visuelle pour les pages sans texte.

Ordre par défaut (le premier dont la qualité est suffisante l'emporte) :
PyMuPDF4LLM → pdftotext → pdfplumber (tableaux) → pypdfium2 → pypdf → lecteur Python pur (repli sans aucune dépendance).
Une page sans texte n'est jamais laissée vide en silence : OCR (Tesseract) si disponible, sinon élément « lecture visuelle ».
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import external as ext
from .core import Ctx, Protected, Result, Unsupported, engine
from .textflow import is_page_number, page_marker, reflow, repeated_sets, strip_repeated, words_count
from .util import clean_text, esc_inline, md_table

MIN_WORDS_PAGE = 5
OCR_PAGE_CAP = 60
VISION_PNG_CAP = 12


def _ranges(pages: Sequence[int]) -> str:
    pages = sorted(pages)
    out: List[str] = []
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


def pdf_info(path: Path) -> Dict[str, str]:
    """Titre/auteur depuis le dictionnaire /Info (lecture minimale, sans dépendance)."""
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    tail = data[-65536:] + data[:65536]
    out: Dict[str, str] = {}
    if b"/Encrypt" in tail:      # les chaînes du dictionnaire /Info sont chiffrées : pas de titre lisible sans les déchiffrer
        return out
    for key, name in ((b"Title", "title"), (b"Author", "author"), (b"Subject", "subject")):
        m = re.search(rb"/" + key + rb"\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]+>)", tail)
        if not m:
            continue
        raw = m.group(1)
        try:
            if raw.startswith(b"<"):
                b = bytes.fromhex(re.sub(rb"\s", b"", raw[1:-1]).decode())
            else:
                b = re.sub(rb"\\([nrtbf()\\])", lambda mm: {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}.get(mm.group(1), mm.group(1)), raw[1:-1])
            txt = b.decode("utf-16", "ignore") if b[:2] in (b"\xfe\xff", b"\xff\xfe") else b.decode("cp1252", "ignore")
            txt = clean_text(txt).strip()
            if name == "title" and re.match(r"(?i)^(untitled|sans titre|document\d*|microsoft (word|powerpoint|excel).*|.*\.(docx?|pptx?|xlsx?|pdf|tex|indd|odt))$", txt):
                continue
            if txt and len(txt) < 300:
                out[name] = txt
        except Exception:
            continue
    return out


_OCR_CACHE: Dict[tuple, Tuple[str, float]] = {}


def _ocr_pages(path: Path, pages: List[int], ctx: Ctx) -> Dict[int, Tuple[str, float]]:
    """OCR des pages demandées. Résultats gardés en mémoire : si plusieurs moteurs PDF se succèdent sur un même scan
    (le premier n'a rien trouvé), les pages déjà reconnues ne sont pas relues."""
    try:
        st = Path(path).stat()
        stamp: tuple = (str(path), st.st_size, st.st_mtime_ns, ctx.opts.ocr_lang)
    except OSError:
        stamp = (str(path), 0, 0, ctx.opts.ocr_lang)
    got = {p: _OCR_CACHE[stamp + (p,)] for p in pages if stamp + (p,) in _OCR_CACHE}
    missing = [p for p in pages if p not in got]
    if missing:
        images = ext.render_pdf_pages(path, missing, dpi=200, timeout=ctx.opts.timeout)
        for p in missing:
            png = images.get(p)
            if not png:
                continue
            got[p] = _OCR_CACHE[stamp + (p,)] = ext.ocr_png(png, ctx.opts.ocr_lang, timeout=ctx.opts.timeout)
        if len(_OCR_CACHE) > 400:
            _OCR_CACHE.clear()
    return dict(sorted(got.items()))


def finish(pages: List[str], ctx: Ctx, engine_name: str, path: Path, already_md: bool = False,
           tables: Optional[Dict[int, str]] = None) -> Result:
    """Texte par page → Markdown avec marqueurs de page ; escalade OCR / vision pour les pages vides."""
    n = len(pages)
    if n == 0:
        raise Unsupported("aucune page")
    if not already_md:
        pages = strip_repeated(pages)
        pages = [reflow(p) for p in pages]
    counts = [words_count(p) for p in pages]
    empty = [i + 1 for i, c in enumerate(counts) if c < MIN_WORDS_PAGE]
    force = ctx.opts.ocr == "force"
    ocr_used: Dict[int, float] = {}
    todo = list(range(1, n + 1)) if force else empty
    if todo and ctx.opts.ocr != "off" and ctx.opts.external and ext.has_ocr() and ext.can_render_pdf():
        batch = todo[:OCR_PAGE_CAP]
        for p, (text, conf) in _ocr_pages(path, batch, ctx).items():
            if words_count(text) >= MIN_WORDS_PAGE and (conf >= 45 or not pages[p - 1].strip()):
                pages[p - 1] = "\n\n".join(esc_inline(t.strip()) for t in text.split("\n\n") if t.strip())
                ocr_used[p] = conf
        if len(todo) > OCR_PAGE_CAP:
            ctx.warn(f"OCR limité à {OCR_PAGE_CAP} pages ({len(todo) - OCR_PAGE_CAP} pages non traitées)")
        if ocr_used:
            avg = sum(ocr_used.values()) / len(ocr_used)
            ctx.warn(f"{len(ocr_used)} page(s) lue(s) par OCR (confiance moyenne {avg:.0f} %) : vérifier chiffres et noms propres")
    counts = [words_count(p) for p in pages]
    empty = [i + 1 for i, c in enumerate(counts) if c < MIN_WORDS_PAGE]
    low_conf = [p for p, c in ocr_used.items() if c < 60]
    vision_pages = sorted(set(empty) | set(low_conf))
    parts: List[str] = []
    marker_note: Dict[int, str] = {}
    if vision_pages:
        reason = "aucun texte extractible (page scannée ou image)" if set(vision_pages) & set(empty) else "OCR peu fiable"
        pngs = {}
        if ctx.opts.external and ext.can_render_pdf() and len(vision_pages) <= VISION_PNG_CAP:
            pngs = ext.render_pdf_pages(path, vision_pages, dpi=110, timeout=ctx.opts.timeout)
        for p in vision_pages:
            png = pngs.get(p)
            link = ctx.add_asset(png, "png", stem=f"page-{p:03d}", force=True, unique=True) if png else None
            marker_note[p] = (f"![page {p}]({link})\n\n" if link else "") + \
                f"> **[À COMPLÉTER : lecture visuelle]** page {p} — {reason}."
            if link:
                ctx.need_vision("page", link, f"page {p} : {reason}")
        if not pngs:
            ctx.need_vision("page", str(path), f"{reason}", pages=_ranges(vision_pages))
        elif len(pngs) < len(vision_pages):
            rest = [p for p in vision_pages if p not in pngs]
            ctx.need_vision("page", str(path), reason, pages=_ranges(rest))
    for i, text in enumerate(pages, 1):
        tag = page_marker(i) if i not in ocr_used else f"<!-- page {i} (OCR {ocr_used[i]:.0f} %) -->"
        block = text.strip()
        if i in marker_note:
            block = (block + "\n\n" if block else "") + marker_note[i]
        if tables and i in tables:
            block = (block + "\n\n" if block else "") + tables[i]
        parts.append(f"{tag}\n\n{block}" if block else tag)
    md = "\n\n".join(parts)
    info = pdf_info(path)
    res = Result(markdown=md, fmt="pdf", engine=engine_name, title=info.get("title", ""),
                 meta={k: v for k, v in info.items() if k in ("author", "subject")})
    res.units, res.unit_name, res.units_found = n, "page", len(re.findall(r"<!-- page \d+", md))
    return res


# --------------------------------------------------------------------------
# Moteurs
# --------------------------------------------------------------------------

def _use_pymupdf4llm() -> bool:
    return ext.has_module("pymupdf4llm")


@engine("pdf", name="pymupdf4llm", kind="external", prio=10, available=_use_pymupdf4llm)
def pdf_pymupdf4llm(path, ctx: Ctx) -> Result:
    import pymupdf4llm  # type: ignore

    kwargs: Dict[str, object] = {"page_chunks": True}
    imgdir = Path(ctx.tmp) / "pmimg"
    if ctx.opts.images == "extract":
        imgdir.mkdir(exist_ok=True)
        kwargs.update(write_images=True, image_path=str(imgdir), image_format="png", dpi=150)
    try:
        chunks = pymupdf4llm.to_markdown(str(path), show_progress=False, **kwargs)
    except TypeError:
        chunks = pymupdf4llm.to_markdown(str(path), **kwargs)
    pages: List[str] = []
    for c in chunks:
        text = c["text"] if isinstance(c, dict) else str(c)

        def repl(m: "re.Match[str]") -> str:
            f = Path(m.group(2))
            if not f.is_absolute():
                f = imgdir / f.name
            if f.exists():
                link = ctx.add_asset(f.read_bytes(), "png", stem="fig", alt=m.group(1))
                return f"![{m.group(1)}]({link})" if link else ""
            return ""

        pages.append(re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, text))
    shutil.rmtree(imgdir, ignore_errors=True)
    return finish(pages, ctx, "pymupdf4llm", Path(path), already_md=True)


def _use_docling() -> bool:
    return ext.has_module("docling")


@engine("pdf", name="docling", kind="external", prio=12, available=_use_docling)
def pdf_docling(path, ctx: Ctx) -> Result:
    from docling.document_converter import DocumentConverter  # type: ignore

    doc = DocumentConverter().convert(str(path)).document
    md = doc.export_to_markdown()
    n = ext.pdf_page_count(Path(path)) or 1
    res = Result(markdown=md, fmt="pdf", engine="docling", title=pdf_info(Path(path)).get("title", ""))
    res.units, res.unit_name = n, "page"
    per = len(re.findall(r"\w+", md)) / max(n, 1)
    res.stats["words_per_page"] = round(per, 1)
    return res


@engine("pdf", name="pdftotext", kind="external", prio=20, available=lambda: bool(ext.tool("pdftotext")))
def pdf_pdftotext(path, ctx: Ctx) -> Result:
    rc, out, err = ext.run([ext.tool("pdftotext") or "pdftotext", "-enc", "UTF-8", str(path), "-"], timeout=ctx.opts.timeout)
    if rc != 0:
        msg = err.decode("utf-8", "replace").strip()
        if "password" in msg.lower() or "encrypted" in msg.lower():
            raise Protected("PDF protégé par mot de passe")
        raise Unsupported(f"pdftotext a échoué : {msg[:200]}")
    pages = out.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return finish(pages, ctx, "pdftotext", Path(path))


def _use_pdfplumber() -> bool:
    return ext.has_module("pdfplumber")


@engine("pdf", name="pdfplumber", kind="external", prio=25, available=_use_pdfplumber)
def pdf_pdfplumber(path, ctx: Ctx) -> Result:
    import pdfplumber  # type: ignore

    pages_lines: List[List[Tuple[float, str]]] = []
    page_tables: List[List[Tuple[float, List[List[str]]]]] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            tables = []
            try:
                tables = page.find_tables()
            except Exception:
                tables = []
            boxes = [t.bbox for t in tables]

            def outside(obj, boxes=boxes) -> bool:
                cx = (obj["x0"] + obj["x1"]) / 2
                cy = (obj["top"] + obj["bottom"]) / 2
                return not any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)

            lines: List[Tuple[float, str]] = []
            try:
                for ln in (page.filter(outside) if boxes else page).extract_text_lines():
                    lines.append((float(ln["top"]), ln["text"]))
            except Exception:
                txt = (page.filter(outside) if boxes else page).extract_text() or ""
                lines = [(float(i), t) for i, t in enumerate(txt.split("\n"))]
            pages_lines.append(lines)
            tbls = []
            for t in tables:
                try:
                    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in t.extract()]
                except Exception:
                    rows = []
                if rows and len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                    tbls.append((float(t.bbox[1]), rows))
            page_tables.append(tbls)
    heads, tails = repeated_sets([[t for _y, t in ls] for ls in pages_lines])
    from .textflow import _norm_for_repeat  # noqa: WPS433

    pages: List[str] = []
    for i, (lines, tbls) in enumerate(zip(pages_lines, page_tables), 1):
        kept = [(y, t) for y, t in lines if _norm_for_repeat(t) not in heads and _norm_for_repeat(t) not in tails and not is_page_number(t)]
        if lines and sum(len(t.split()) for _y, t in kept) * 2 < sum(len(t.split()) for _y, t in lines):
            kept = [(y, t) for y, t in lines if not is_page_number(t)]      # on ne retire jamais plus de la moitié d'une page
        items: List[Tuple[float, str, object]] = [(y, "t", t) for y, t in kept] + [(y, "tbl", rows) for y, rows in tbls]
        items.sort(key=lambda it: it[0])
        chunk: List[str] = []
        out: List[str] = []
        for _y, kind, payload in items:
            if kind == "t":
                chunk.append(payload)  # type: ignore[arg-type]
            else:
                if chunk:
                    out.append(reflow("\n".join(chunk)))
                    chunk = []
                out.append(md_table([[esc_inline(c) for c in r] for r in payload]))  # type: ignore[union-attr]
        if chunk:
            out.append(reflow("\n".join(chunk)))
        pages.append("\n\n".join(x for x in out if x.strip()))
    return finish(pages, ctx, "pdfplumber", Path(path), already_md=True)


def _use_pdfium() -> bool:
    return ext.has_module("pypdfium2")


@engine("pdf", name="pypdfium2", kind="external", prio=35, available=_use_pdfium)
def pdf_pdfium(path, ctx: Ctx) -> Result:
    import pypdfium2 as pdfium  # type: ignore

    doc = pdfium.PdfDocument(str(path))
    try:
        pages = []
        for i in range(len(doc)):
            page = doc[i]
            tp = page.get_textpage()
            pages.append(tp.get_text_range())
            tp.close()
            page.close()
    finally:
        doc.close()
    return finish(pages, ctx, "pypdfium2", Path(path))


def _use_pypdf() -> bool:
    return ext.has_module("pypdf") or ext.has_module("PyPDF2")


@engine("pdf", name="pypdf", kind="external", prio=40, available=_use_pypdf)
def pdf_pypdf(path, ctx: Ctx) -> Result:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore

    reader = PdfReader(str(path))
    if getattr(reader, "is_encrypted", False):
        try:
            if not reader.decrypt(""):
                raise Protected("PDF protégé par mot de passe")
        except Protected:
            raise
        except Exception:
            raise Protected("PDF chiffré : déchiffrement impossible sans mot de passe")
    pages = [(p.extract_text() or "") for p in reader.pages]
    return finish(pages, ctx, "pypdf", Path(path))


@engine("pdf", name="pdflite", kind="native", prio=60)
def pdf_lite(path, ctx: Ctx) -> Result:
    from .pdf_lite import extract_pages

    pages, notes = extract_pages(Path(path).read_bytes())
    for n in notes:
        ctx.warn(n)
    return finish(pages, ctx, "pdflite", Path(path))
