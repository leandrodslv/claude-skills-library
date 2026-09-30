"""Images (PNG, JPEG, GIF, WebP, BMP, TIFF…) → Markdown : référence, métadonnées, OCR, puis lecture visuelle.

Une image n'a pas de « texte » à convertir : ce module en tire tout ce qu'un script peut (dimensions, texte
incrusté PNG, OCR si Tesseract est là) et signale le reste comme travail de lecture visuelle pour Claude.
"""
from __future__ import annotations

import shutil
import struct
import tempfile
from pathlib import Path
from typing import Dict, Optional

from . import external as ext
from .core import Ctx, Result, Unsupported, engine
from .util import clean_text, esc_inline, human_bytes, image_info, slugify
from .textflow import words_count

OCR_MIN_WORDS = 30
OCR_MIN_CONF = 70


def png_text_chunks(data: bytes) -> Dict[str, str]:
    """Métadonnées texte d'un PNG (tEXt/iTXt) : légende, prompt de génération, logiciel…"""
    out: Dict[str, str] = {}
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return out
    i = 8
    while i + 8 <= len(data) and len(out) < 12:
        try:
            ln, typ = struct.unpack(">I4s", data[i:i + 8])
        except struct.error:
            break
        body = data[i + 8:i + 8 + ln]
        i += 12 + ln
        if typ == b"tEXt" and b"\x00" in body:
            k, v = body.split(b"\x00", 1)
            out[k.decode("latin-1")] = v.decode("latin-1", "replace")
        elif typ == b"iTXt" and b"\x00" in body:
            k, rest = body.split(b"\x00", 1)
            if len(rest) > 4 and rest[0] == 0:
                v = rest[2:].split(b"\x00", 2)
                if len(v) == 3:
                    out[k.decode("latin-1")] = v[2].decode("utf-8", "replace")
        elif typ == b"IEND":
            break
    return {k: clean_text(v).strip() for k, v in out.items() if v.strip() and len(v) < 4000}


def _convert_to_png(path: Path, timeout: int) -> Optional[bytes]:
    """HEIC/AVIF/TIFF exotiques → PNG avec un outil du système (sips, magick, heif-convert)."""
    tmp = Path(tempfile.mkdtemp(prefix="mdconv_img_"))
    out = tmp / "out.png"
    try:
        if ext.tool("sips"):
            rc, _o, _e = ext.run([ext.tool("sips") or "sips", "-s", "format", "png", str(path), "--out", str(out)], timeout=timeout)
            if rc == 0 and out.exists():
                return out.read_bytes()
        if ext.tool("heif-convert"):
            rc, _o, _e = ext.run([ext.tool("heif-convert") or "heif-convert", str(path), str(out)], timeout=timeout)
            if out.exists():
                return out.read_bytes()
        im = ext.tool("magick") or ext.tool("convert")
        if im:
            rc, _o, _e = ext.run([im, str(path) + "[0]", str(out)], timeout=timeout)
            if rc == 0 and out.exists():
                return out.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None


@engine("image", name="native", prio=10)
def image_native(path, ctx: Ctx) -> Result:
    p = Path(path)
    data = p.read_bytes()
    fmt, w, h = image_info(data)
    stem = slugify(p.stem) or "image"
    ocr_source = data
    if fmt == "?":  # HEIC/AVIF ou format non lisible sans outil externe
        png = _convert_to_png(p, ctx.opts.timeout) if ctx.opts.external else None
        if png is None:
            raise Unsupported(f"format image non lisible ({p.suffix or 'inconnu'})",
                              hint="convertir en PNG/JPEG (sips, ImageMagick, heif-convert) puis relancer")
        data, ocr_source = png, png
        fmt, w, h = image_info(png)
    link = ctx.add_asset(data, fmt if fmt != "?" else p.suffix, stem=stem, alt=p.stem, force=True, unique=True)
    dims = f"{w}×{h} px" if w and h else "dimensions inconnues"
    parts = [f"# {esc_inline(p.stem)}", f"![{esc_inline(p.stem)}]({link})" if link else "",
             f"> Image {fmt.upper() if fmt != '?' else ''} · {dims} · {human_bytes(len(data))}".replace("Image  ·", "Image ·")]
    meta = png_text_chunks(data)
    if meta:
        parts.append("**Métadonnées du fichier :**\n\n" + "\n".join(f"- **{esc_inline(k)}** : {esc_inline(v[:600])}" for k, v in meta.items()))
    ocr_text, conf = "", 0.0
    if ctx.opts.ocr != "off" and ctx.opts.external and ext.has_ocr():
        ocr_text, conf = ext.ocr_png(ocr_source, ctx.opts.ocr_lang, timeout=ctx.opts.timeout)
    substantial = words_count(ocr_text) >= OCR_MIN_WORDS and conf >= OCR_MIN_CONF
    if ocr_text.strip() and words_count(ocr_text) >= 3:
        head = "Texte reconnu (OCR"
        parts.append(f"## {head}, confiance {conf:.0f} %)\n\n" + "\n\n".join(esc_inline(t.strip()) for t in ocr_text.split("\n\n") if t.strip()))
        ctx.warn(f"texte lu par OCR (confiance {conf:.0f} %) : vérifier chiffres et noms propres")
    if not substantial:
        if ctx.opts.ocr == "off":
            why = "image à lire visuellement (OCR désactivé par --ocr off)"
        elif not (ctx.opts.external and ext.has_ocr()):
            why = "image : aucun outil OCR installé — contenu à lire visuellement"
        elif not ocr_text.strip():
            why = "image sans texte lisible par OCR — contenu à décrire visuellement"
        else:
            why = "OCR insuffisant pour décrire l'image — à lire visuellement"
        ctx.need_vision("image", str(p.resolve()), why)
        parts.append(f"> **[À COMPLÉTER : description visuelle]** {why}.")
    md = "\n\n".join(x for x in parts if x)
    res = Result(markdown=md, fmt="image", engine="native+ocr" if ocr_text else "native", title=p.stem)
    res.source_text = None
    res.stats["partial_source"] = True
    res.stats["ocr_confidence"] = round(conf, 1)
    return res
