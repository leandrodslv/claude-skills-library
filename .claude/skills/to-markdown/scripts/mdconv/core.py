"""Structures communes : options, résultat, contexte de conversion, registre de moteurs."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .util import image_info

VERSION = "1.0.0"


class Unsupported(Exception):
    """Ce moteur ne sait pas traiter ce fichier (on passe au suivant)."""

    def __init__(self, msg: str, hint: str = ""):
        super().__init__(msg)
        self.hint = hint


class Protected(Unsupported):
    """Fichier chiffré ou protégé par mot de passe."""


@dataclass
class Options:
    """Réglages d'une conversion (sérialisable : passé tel quel aux processus fils)."""

    images: str = "extract"            # extract | skip
    min_image_px: int = 24             # ignore les puces / pixels espaceurs
    min_image_bytes: int = 400
    comments: bool = True              # commentaires Word/Excel/PowerPoint
    notes: bool = True                 # notes du présentateur, notes de bas de page
    hidden: bool = True                # feuilles/diapos masquées (signalées comme telles)
    headers_footers: bool = False
    keep_toc: bool = False             # conserve la table des matières Word
    formulas: bool = False             # affiche aussi les formules Excel
    track_changes: str = "accept"      # accept | mark
    table_rows: int = 1000             # plafond de lignes par tableau (0 = illimité)
    html_mode: str = "auto"            # auto | full | main
    infer_headings: bool = True
    frontmatter: str = "min"           # min | full | none
    engines: Optional[List[str]] = None  # ordre imposé (noms de moteurs)
    external: bool = True              # autorise les outils externes (LibreOffice, pdftotext…)
    ocr: str = "auto"                  # auto | off | force
    ocr_lang: str = ""                 # ex. « fra+eng » ; vide = détection
    render: bool = False               # produit des PNG de pages/diapos pour lecture visuelle
    max_size_mb: int = 500
    archive_depth: int = 3
    timeout: int = 180                 # secondes, par appel d'outil externe
    quality_threshold: float = 0.90
    compare: bool = False              # essaie tous les moteurs (comparatif), sans s'arrêter au premier bon


@dataclass
class VisionItem:
    """Contenu qu'aucun script ne sait lire : à regarder (Claude) puis à transcrire."""

    kind: str          # image | page | slide | figure | svg
    path: str          # fichier à ouvrir
    reason: str
    pages: str = ""    # plages de pages pour un PDF (« 1-3,7 »)

    def as_dict(self) -> Dict[str, str]:
        d = {"kind": self.kind, "path": self.path, "reason": self.reason}
        if self.pages:
            d["pages"] = self.pages
        return d


@dataclass
class Asset:
    name: str
    data: bytes
    alt: str = ""


@dataclass
class Result:
    """Sortie d'un moteur pour un fichier."""

    markdown: str = ""
    fmt: str = ""
    engine: str = ""
    title: str = ""
    meta: Dict[str, object] = field(default_factory=dict)
    # Dump de texte brut indépendant de la mise en forme, servant à mesurer
    # ce que la conversion aurait pu perdre (rappel de mots).
    source_text: Optional[str] = None
    units: Optional[int] = None        # pages / diapos / feuilles attendues
    unit_name: str = ""
    units_found: Optional[int] = None  # unités effectivement présentes dans le Markdown
    score: float = 1.0
    stats: Dict[str, object] = field(default_factory=dict)


class Ctx:
    """Contexte d'une tentative de conversion : assets, avertissements, éléments visuels."""

    def __init__(self, src: Path, opts: Options, assets_dir: str = "assets", origin: str = ""):
        self.src = Path(src)
        self.opts = opts
        self.assets_dir = assets_dir
        self.origin = origin or str(src)
        self.assets: Dict[str, Asset] = {}
        self.warnings: List[str] = []
        self.vision: List[VisionItem] = []
        self.previews: List[str] = []       # aperçus PNG (--render), liens relatifs comme les assets
        self.skipped_images = 0
        self._by_hash: Dict[str, str] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._tmp: Optional[str] = None

    # -- cycle de vie ------------------------------------------------------
    def fork(self) -> "Ctx":
        """Contexte vierge pour une nouvelle tentative (assets/avertissements séparés)."""
        c = Ctx(self.src, self.opts, self.assets_dir, self.origin)
        c._tmp = None
        return c

    @property
    def tmp(self) -> str:
        if self._tmp is None:
            self._tmp = tempfile.mkdtemp(prefix="mdconv_")
        return self._tmp

    def cleanup(self) -> None:
        if self._tmp and os.path.isdir(self._tmp):
            shutil.rmtree(self._tmp, ignore_errors=True)
        self._tmp = None

    # -- ressources --------------------------------------------------------
    def add_asset(self, data: bytes, ext: str = "", stem: str = "img", alt: str = "", force: bool = False,
                  unique: bool = False) -> Optional[str]:
        """Enregistre une image extraite ; renvoie le lien relatif à utiliser dans le Markdown.

        Renvoie None si les images sont désactivées ou si l'image est insignifiante (puce, pixel
        espaceur) — l'appelant n'écrit alors rien. ``force`` ignore ces filtres (image qui EST le
        contenu) ; ``unique`` garde le nom tel quel au lieu d'ajouter un compteur.
        """
        if (self.opts.images == "skip" and not force) or not data:
            return None
        fmt, w, h = image_info(data)
        ext = (ext or (fmt if fmt != "?" else "bin")).lower().lstrip(".")
        if ext == "jpeg":
            ext = "jpg"
        if not force and fmt not in ("svg", "emf", "wmf"):
            if w and h and min(w, h) < self.opts.min_image_px:
                self.skipped_images += 1
                return None
            if len(data) < self.opts.min_image_bytes:
                self.skipped_images += 1
                return None
        digest = hashlib.sha1(data).hexdigest()
        if digest in self._by_hash:
            return f"{self.assets_dir}/{self._by_hash[digest]}"
        if unique:
            name = f"{stem}.{ext}"
            k = 1
            while name in self.assets:
                k += 1
                name = f"{stem}-{k}.{ext}"
        else:
            self._counters[stem] += 1
            name = f"{stem}-{self._counters[stem]:02d}.{ext}"
        self.assets[name] = Asset(name, data, alt)
        self._by_hash[digest] = name
        return f"{self.assets_dir}/{name}"

    def add_file(self, name: str, data: bytes, alt: str = "") -> str:
        """Enregistre un fichier annexe (CSV d'une grande feuille…) ; renvoie son lien relatif."""
        stem, _dot, ext = name.rpartition(".")
        base = stem or name
        candidate, k = name, 1
        while candidate in self.assets:
            k += 1
            candidate = f"{base}-{k}.{ext}" if stem else f"{base}-{k}"
        self.assets[candidate] = Asset(candidate, data, alt)
        return f"{self.assets_dir}/{candidate}"

    def warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def need_vision(self, kind: str, path: str, reason: str, pages: str = "") -> None:
        item = VisionItem(kind, path, reason, pages)
        if all((v.path, v.pages, v.reason) != (item.path, item.pages, item.reason) for v in self.vision):
            self.vision.append(item)


# --------------------------------------------------------------------------
# Registre de moteurs
# --------------------------------------------------------------------------

@dataclass
class EngineSpec:
    fmt: str
    name: str                                  # « native », « markitdown », « pandoc »…
    fn: Callable[[Path, Ctx], Result]
    kind: str = "native"                       # native | external
    prio: int = 50                             # plus petit = essayé d'abord
    available: Optional[Callable[[], bool]] = None

    def is_available(self) -> bool:
        if self.available is None:
            return True
        try:
            return bool(self.available())
        except Exception:
            return False


_REGISTRY: Dict[str, List[EngineSpec]] = defaultdict(list)


def engine(fmt, name: str = "native", kind: str = "native", prio: int = 50,
           available: Optional[Callable[[], bool]] = None):
    """Décorateur : enregistre ``fn(path, ctx) -> Result`` comme moteur pour un ou plusieurs formats."""
    fmts = [fmt] if isinstance(fmt, str) else list(fmt)

    def deco(fn):
        for f in fmts:
            _REGISTRY[f].append(EngineSpec(f, name, fn, kind, prio, available))
            _REGISTRY[f].sort(key=lambda s: s.prio)
        return fn

    return deco


def engines_for(fmt: str) -> List[EngineSpec]:
    load_all()
    return list(_REGISTRY.get(fmt, []))


def all_engine_names() -> List[str]:
    load_all()
    return sorted({s.name for specs in _REGISTRY.values() for s in specs})


_LOADED = False


def load_all() -> None:
    """Importe les modules de formats (chacun s'enregistre à l'import)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    import importlib

    for mod in (
        "fmt_docx", "fmt_pptx", "fmt_xlsx", "fmt_odf", "fmt_html", "fmt_epub", "fmt_svg",
        "fmt_data", "fmt_rtf", "fmt_mail", "fmt_pdf", "fmt_image", "fmt_archive", "fmt_legacy", "fmt_binary", "fmt_diagram", "fmt_visio", "fmt_xml2003",
    ):
        try:
            importlib.import_module(f"{__package__}.{mod}")
        except ModuleNotFoundError as exc:  # module pas encore écrit / retiré
            if exc.name != f"{__package__}.{mod}":
                raise
