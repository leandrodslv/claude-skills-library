"""Moteurs externes optionnels : LibreOffice (formats binaires legacy), pandoc, markitdown, transcription audio.

Chaque moteur est testé pour de vrai avant usage (voir external.py). LibreOffice convertit un format legacy
(.doc/.ppt/.xls…) en OOXML, puis les convertisseurs NATIFS font le reste : on profite de la fidélité du noyau
sans réécrire un lecteur binaire — et, groupés, les fichiers legacy d'un dossier partent en UN seul lancement.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import external as ext
from .core import Ctx, Result, Unsupported, engine
from .util import esc_inline

LO_CACHE_ENV = "MDCONV_LO_CACHE"

# format d'entrée → (format cible OOXML, module LibreOffice requis)
LO_TARGET = {
    "doc": ("docx", "writer"), "rtf": ("docx", "writer"), "odt": ("docx", "writer"), "wps": ("docx", "writer"),
    "xls": ("xlsx", "calc"), "xlsb": ("xlsx", "calc"), "ods": ("xlsx", "calc"),
    "ppt": ("pptx", "impress"), "odp": ("pptx", "impress"), "iwork": ("docx", "writer"),
}


def lo_cache_dir() -> Optional[Path]:
    d = os.environ.get(LO_CACHE_ENV)
    return Path(d) if d and Path(d).is_dir() else None


def lo_cache_key(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:16]


def prepare_legacy(files: List[Path], staging: Path, timeout: int = 180) -> None:
    """Pré-conversion groupée des fichiers legacy (un seul lancement LibreOffice par format cible).

    Les résultats sont déposés dans ``staging`` et retrouvés par les moteurs via la variable d'environnement.
    """
    if not ext.soffice_path():
        return
    by_target: Dict[str, List[Path]] = {}
    for f in files:
        by_target.setdefault(f.suffix.lower().lstrip("."), []).append(f)
    staging.mkdir(parents=True, exist_ok=True)
    index: Dict[str, str] = {}
    for suffix, group in by_target.items():
        target = LO_TARGET.get({"dot": "doc", "xlt": "xls", "pps": "ppt", "pot": "ppt"}.get(suffix, suffix))
        if not target or not ext.libreoffice_ok(target[1]):
            continue
        stage = staging / f"in_{suffix}"
        stage.mkdir(exist_ok=True)
        mapping: Dict[str, Path] = {}
        for f in group:
            key = lo_cache_key(f)
            cp = stage / f"{key}{f.suffix.lower()}"
            try:
                shutil.copyfile(f, cp)
            except OSError:
                continue
            mapping[str(cp)] = f
        out = ext.soffice_convert(list(map(Path, mapping)), target[0], staging / f"out_{target[0]}", timeout=timeout)
        for cp, produced in out.items():
            index[lo_cache_key(mapping[cp])] = str(produced)
    (staging / "index.json").write_text(json.dumps(index), encoding="utf-8")
    os.environ[LO_CACHE_ENV] = str(staging)


def _cached_conversion(path: Path) -> Optional[Path]:
    d = lo_cache_dir()
    if not d:
        return None
    try:
        idx = json.loads((d / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    p = idx.get(lo_cache_key(path))
    return Path(p) if p and Path(p).exists() else None


def _native_for(target: str) -> Callable[[Path, Ctx], Result]:
    if target == "docx":
        from .fmt_docx import docx_native as fn
    elif target == "xlsx":
        from .fmt_xlsx import xlsx_native as fn
    else:
        from .fmt_pptx import pptx_native as fn
    return fn


def _make_lo_engine(fmt: str, target: str, module: str, prio: int):
    def run_lo(path, ctx: Ctx) -> Result:
        path = Path(path)
        produced = _cached_conversion(path)
        if produced is None:
            if not ext.libreoffice_ok(module):
                raise Unsupported(f"LibreOffice ({module}) indisponible")
            tmp = Path(ctx.tmp)
            src = tmp / f"in{path.suffix.lower() or '.' + fmt}"
            shutil.copyfile(path, src)
            got = ext.soffice_convert([src], target, tmp / "lo_out", timeout=ctx.opts.timeout)
            produced = got.get(str(src))
            if produced is None:
                raise Unsupported("la conversion LibreOffice n'a rien produit (fichier corrompu ou protégé ?)")
        res = _native_for(target)(produced, ctx)
        res.engine = "libreoffice+native"
        res.fmt = fmt
        return res

    engine(fmt, name="libreoffice", kind="external", prio=prio, available=lambda: lo_cache_dir() is not None or ext.libreoffice_ok(module))(run_lo)


for _fmt, (_target, _module) in LO_TARGET.items():
    # formats sans lecteur natif : LibreOffice passe en premier ; ODF/RTF ont un lecteur natif, LibreOffice ne sert qu'en repli
    _make_lo_engine(_fmt, _target, _module, 5 if _fmt in ("doc", "xls", "xlsb", "ppt", "wps", "iwork") else 40)


# --------------------------------------------------------------------------
# markitdown (Microsoft) — second avis / repli quand il est installé
# --------------------------------------------------------------------------

def _use_markitdown() -> bool:
    return ext.has_module("markitdown") or bool(ext.tool("markitdown"))


def _md_data_uris(md: str, ctx: Ctx) -> str:
    def repl(m: "re.Match[str]") -> str:
        import base64

        try:
            data = base64.b64decode(m.group(3))
        except Exception:
            return ""
        link = ctx.add_asset(data, m.group(2).replace("jpeg", "jpg"), stem="img", alt=m.group(1))
        return f"![{m.group(1)}]({link})" if link else ""

    return re.sub(r"!\[([^\]]*)\]\(data:image/([\w+.-]+);base64,([^)]+)\)", repl, md)


def _run_markitdown(path, ctx: Ctx) -> Result:
    path = Path(path)
    if ext.has_module("markitdown"):
        from markitdown import MarkItDown  # type: ignore

        r = MarkItDown().convert(str(path))
        md, title = r.text_content, (getattr(r, "title", None) or "")
    else:
        rc, out, err = ext.run([ext.tool("markitdown") or "markitdown", str(path)], timeout=ctx.opts.timeout)
        if rc != 0:
            raise Unsupported("markitdown a échoué : " + err.decode("utf-8", "replace")[:200])
        md, title = out.decode("utf-8", "replace"), ""
    if not md.strip():
        raise Unsupported("markitdown n'a produit aucun texte")
    res = Result(markdown=_md_data_uris(md, ctx), engine="markitdown", title=title)
    res.stats["partial_source"] = True
    return res


for _f in ("docx", "pptx", "xlsx", "xls", "pdf", "html", "csv", "json", "xml", "epub", "msg", "ipynb", "doc", "ppt", "rtf", "odt"):
    engine(_f, name="markitdown", kind="external", prio=50 if _f != "pdf" else 30, available=_use_markitdown)(_run_markitdown)


# --------------------------------------------------------------------------
# pandoc
# --------------------------------------------------------------------------

_PANDOC_FROM = {"docx": "docx", "odt": "odt", "epub": "epub", "rtf": "rtf", "html": "html", "ipynb": "ipynb"}
_MARKUP_FROM = {"tex": "latex", "latex": "latex", "rst": "rst", "org": "org", "textile": "textile", "wiki": "mediawiki",
                "mediawiki": "mediawiki", "dokuwiki": "dokuwiki"}


def _pandoc_available() -> bool:
    return bool(ext.tool("pandoc"))


def _pandoc_run(path: Path, fmt_from: str, ctx: Ctx) -> Result:
    media = Path(ctx.tmp) / "pandoc_media"
    cmd = [ext.tool("pandoc") or "pandoc", "-f", fmt_from, "-t", "gfm", "--wrap=none", "--extract-media", str(media)]
    if fmt_from == "docx":
        cmd += ["--track-changes=accept"]
    cmd.append(str(path))
    rc, out, err = ext.run(cmd, timeout=ctx.opts.timeout, cwd=ctx.tmp)
    if rc != 0:
        raise Unsupported("pandoc a échoué : " + err.decode("utf-8", "replace")[:200])
    md = out.decode("utf-8", "replace")

    def asset_for(src: str, alt: str) -> Optional[str]:
        f = Path(src)
        cand = f if f.is_absolute() else Path(ctx.tmp) / f
        if cand.exists() and cand.is_file():
            link = ctx.add_asset(cand.read_bytes(), cand.suffix, stem="img", alt=alt)
            return f"![{alt}]({link})" if link else ""
        return None

    md = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: asset_for(m.group(2), m.group(1)) if asset_for(m.group(2), m.group(1)) is not None else m.group(0), md)

    def repl_img(m: "re.Match[str]") -> str:
        alt = re.search(r'alt="([^"]*)"', m.group(0))
        got = asset_for(m.group(1), alt.group(1) if alt else "")
        return got if got is not None else m.group(0)

    md = re.sub(r'<img\s+[^>]*?src="([^"]+)"[^>]*>', repl_img, md)
    md = _md_data_uris(md, ctx)
    if not md.strip():
        raise Unsupported("pandoc n'a produit aucun texte")
    res = Result(markdown=md, engine="pandoc")
    res.stats["partial_source"] = True
    return res


for _f, _from in _PANDOC_FROM.items():
    engine(_f, name="pandoc", kind="external", prio=45 if _f != "html" else 60,
           available=_pandoc_available)(lambda path, ctx, _from=_from: _pandoc_run(Path(path), _from, ctx))


@engine("markup", name="pandoc", kind="external", prio=10, available=_pandoc_available)
def markup_pandoc(path, ctx: Ctx) -> Result:
    src = _MARKUP_FROM.get(Path(path).suffix.lower().lstrip("."))
    if not src:
        raise Unsupported("format de balisage non géré par pandoc")
    return _pandoc_run(Path(path), src, ctx)


# --------------------------------------------------------------------------
# Transcription audio/vidéo (opt-in : lourde et modèles à télécharger une fois)
# --------------------------------------------------------------------------

def _whisper_available() -> bool:
    return ext.has_module("faster_whisper")


def _whisper(path, ctx: Ctx) -> Result:
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(os.environ.get("MDCONV_WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(path), vad_filter=True)
    lines: List[str] = []
    for s in segments:
        t = int(s.start)
        lines.append(f"**[{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}]** {esc_inline(s.text.strip())}")
    if not lines:
        raise Unsupported("aucune parole détectée")
    res = Result(markdown=f"# {esc_inline(Path(path).stem)}\n\n_Transcription automatique (langue : {info.language})_\n\n" + "\n\n".join(lines),
                 engine="faster-whisper", title=Path(path).stem)
    res.stats["partial_source"] = True
    ctx.warn("transcription automatique : relire les noms propres et chiffres")
    return res


for _f in ("audio", "video"):
    engine(_f, name="whisper", kind="external", prio=50, available=_whisper_available)(_whisper)
