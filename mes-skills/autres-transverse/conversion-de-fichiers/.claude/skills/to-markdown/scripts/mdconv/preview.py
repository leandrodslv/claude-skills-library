"""``--render`` : aperçus PNG (une image par page, diapositive ou feuille) pour vérifier une conversion à l'œil.

Les aperçus ne sont pas insérés dans le Markdown : ils sont écrits dans le dossier d'assets du fichier
(``apercu-001.png``…) et listés dans ``_report.json`` (clé ``previews``). Utile pour les diaporamas chargés en
schémas, les mises en page complexes et tout ce que le texte extrait ne décrit pas.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import external as ext
from .core import Ctx

PAGE_CAP = 60      # au-delà, les aperçus s'arrêtent (avertissement) : un PNG par page pèse vite
DPI = 90           # lisible pour vérifier une mise en page ; les pages à lire visuellement sont rendues à part (110 dpi)

# module LibreOffice nécessaire pour ouvrir chaque format
_LO_MODULE = {"docx": "writer", "doc": "writer", "odt": "writer", "rtf": "writer", "wps": "writer",
              "xlsx": "calc", "xls": "calc", "ods": "calc", "xlsb": "calc",
              "pptx": "impress", "ppt": "impress", "odp": "impress"}


def make_previews(src: Path, fmt: str, ctx: Ctx) -> int:
    """Ajoute des aperçus PNG aux assets de ``ctx`` (``ctx.previews`` en garde les liens). Renvoie leur nombre."""
    opts = ctx.opts
    if not opts.render:
        return 0
    if not opts.external:
        ctx.warn("--render : aucun aperçu en mode « noyau natif seul » (retirer --no-external)")
        return 0
    if fmt in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff"):
        return 0                                    # une image est son propre aperçu
    if fmt == "svg":
        data = ext.render_svg_bytes(Path(src), timeout=min(opts.timeout, 90))
        link = ctx.add_asset(data, "png", stem="apercu-001", force=True, unique=True) if data else None
        if link:
            ctx.previews.append(link)
        else:
            ctx.warn("--render : aucun outil pour rendre ce SVG en image (voir --doctor)")
        return len(ctx.previews)
    pdf: Optional[Path] = None
    if fmt == "pdf":
        pdf = Path(src)
    elif fmt in _LO_MODULE and ext.libreoffice_ok(_LO_MODULE[fmt]):
        made = ext.soffice_convert([Path(src)], "pdf", Path(ctx.tmp) / "preview", timeout=opts.timeout)
        pdf = next(iter(made.values()), None)
    if pdf is None:
        ctx.warn(f"--render : pas d'aperçu possible pour ce format ({fmt}) ou LibreOffice absent (voir --doctor)")
        return 0
    total = ext.pdf_page_count(pdf) or 0
    pages = list(range(1, min(total or PAGE_CAP, PAGE_CAP) + 1))
    pngs = ext.render_pdf_pages(pdf, pages, dpi=DPI, timeout=opts.timeout)
    for p in pages:
        if p in pngs:
            link = ctx.add_asset(pngs[p], "png", stem=f"apercu-{p:03d}", force=True, unique=True)
            if link:
                ctx.previews.append(link)
    if not ctx.previews:
        ctx.warn("--render : rendu des pages impossible (installer poppler ou pymupdf, voir --doctor)")
    elif total > PAGE_CAP:
        ctx.warn(f"--render : aperçus limités aux {PAGE_CAP} premières pages sur {total}")
    return len(ctx.previews)
