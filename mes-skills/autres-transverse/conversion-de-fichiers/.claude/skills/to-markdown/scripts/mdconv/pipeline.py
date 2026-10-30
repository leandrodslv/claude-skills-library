"""Pipeline d'un fichier : détection → cascade de moteurs → qualité → Markdown final + rapport."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import Ctx, Options, Protected, Result, Unsupported, engines_for
from .detect import Detected, detect
from .quality import Score, assess, lint_markdown
from .util import (est_tokens, human_bytes, normalize_markdown, sha256_file, words)

# Formats pour lesquels aucune conversion n'est possible : message + piste de contournement.
UNSUPPORTED_HINTS: Dict[str, str] = {
    "encrypted": "fichier Office chiffré : retirer le mot de passe dans Office puis relancer",
    "iwork": "format Apple iWork : exporter en PDF, DOCX, PPTX ou XLSX depuis Pages/Keynote/Numbers",
    "sketch": "fichier Sketch : exporter les artboards en PDF ou PNG",
    "parquet": "fichier Parquet : installer pyarrow ou exporter en CSV",
    "odf-other": "document ODF non textuel (formule, graphique, base) : exporter en PDF",
    "xps": "format XPS : convertir en PDF",
    "binary": "format binaire non reconnu",
    "ole": "conteneur OLE non reconnu",
    "empty": "fichier vide",
    "pub": "Microsoft Publisher : exporter en PDF",
    "vsd": "Visio binaire : exporter en PDF/SVG ou enregistrer en .vsdx",
    "7z": "archive 7-Zip : extraire d'abord (7z x archive.7z) puis relancer sur le dossier",
    "rar": "archive RAR : extraire d'abord (unrar x archive.rar) puis relancer sur le dossier",
    "fig": "fichier Figma (.fig) : exporter les frames en SVG, PDF ou PNG depuis Figma",
}


@dataclass
class Outcome:
    src: Path
    rel: str
    det: Detected
    status: str = "ok"            # ok | warn | needs_vision | unsupported | error
    body: str = ""
    result: Optional[Result] = None
    ctx: Optional[Ctx] = None
    score: Optional[Score] = None
    seconds: float = 0.0
    error: str = ""
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    children: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def assets(self):
        return self.ctx.assets if self.ctx else {}


def _yaml(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{}>&*!|%@`\"',\n\\]|^\s|\s$|^[-?]", s) or s.lower() in ("null", "true", "false", "yes", "no", "~"):
        return json.dumps(s, ensure_ascii=False)
    return s


def front_matter(out: "Outcome", opts: Options, src: Path) -> str:
    if opts.frontmatter == "none" or out.result is None:
        return ""
    r, s = out.result, out.score
    items: List[tuple] = [("source", out.rel.replace(os.sep, "/")), ("format", out.det.label)]
    if r.title:
        items.append(("title", r.title))
    if r.units and r.unit_name:
        items.append((r.unit_name + "s", r.units))
    items.append(("words", s.words if s else len(words(out.body))))
    items.append(("tokens", "~" + str(est_tokens(out.body))))
    items.append(("converter", f"mdconv/{r.engine}"))
    if s and s.value < 0.995:
        items.append(("quality", round(s.value, 2)))
    if out.ctx and out.ctx.warnings:
        items.append(("warnings", list(out.ctx.warnings)))
    if out.ctx and out.ctx.vision:
        items.append(("needs_vision", len(out.ctx.vision)))
    if opts.frontmatter == "full":
        items.append(("size", human_bytes(src.stat().st_size)))
        items.append(("sha256", sha256_file(src)))
        for k in ("author", "created", "modified", "language"):
            if r.meta.get(k):
                items.append((k, r.meta[k]))
        items.append(("converted_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    lines = ["---"]
    for k, v in items:
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"  - {_yaml(x)}" for x in v]
        else:
            lines.append(f"{k}: {_yaml(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _flag_informative_images(body: str, ctx: Ctx) -> None:
    """Grandes images sans texte alternatif (graphique, schéma, capture collés en image) : ajoutées à la liste « à lire »."""
    from .util import image_info

    n = 0
    for m in re.finditer(r"(?<!\\)!\[\]\(([^)\s]+)\)", body):
        name = m.group(1).rsplit("/", 1)[-1]
        a = ctx.assets.get(name)
        if a is None or name.lower().endswith((".svg", ".emf", ".wmf")):
            continue
        fmt, w, h = image_info(a.data)
        if w and h and min(w, h) >= 120 and max(w, h) >= 240 and len(a.data) >= 15_000:
            ctx.need_vision("image", f"{ctx.assets_dir}/{name}", "image sans texte alternatif, peut-être un graphique ou un schéma à décrire")
            n += 1
            if n >= 12:
                break


OPT_IN_ENGINES = {"whisper"}  # lourds ou à modèles téléchargeables : jamais lancés sans demande explicite


def _agreement(a: str, b: str) -> float:
    """Ressemblance (0-1) de deux textes en sacs de mots : mots communs / mots du plus long des deux."""
    from collections import Counter

    from .util import md_plain, words

    ca, cb = Counter(words(md_plain(a))), Counter(words(md_plain(b)))
    total = max(sum(ca.values()), sum(cb.values()))
    return sum((ca & cb).values()) / total if total else 1.0


def _table_cells(md: str) -> List[str]:
    """Contenu normalisé des cellules des tableaux d'un Markdown (hors lignes de séparation)."""
    from .util import words

    cells: List[str] = []
    for ln in md.splitlines():
        if ln.lstrip().startswith("|") and not re.match(r"^\s*\|[\s:|\-]+\|\s*$", ln):
            for c in ln.strip().strip("|").split("|"):
                w = " ".join(words(re.sub(r"<br\s*/?>|[*_`]", " ", c)))
                if w:
                    cells.append(w)
    return cells


def _native_pdf_tables_win(best: tuple, specs: list, src: Path, base: Ctx, out: "Outcome") -> Optional[tuple]:
    """Un moteur PDF externe peut défaire un tableau (cellules coupées en deux, colonnes décalées) sans que la note de qualité
    le voie : le texte y est, au mauvais endroit. Le lecteur natif, très rapide, relit alors le même fichier ; si ses tableaux
    ont des cellules que la sortie du moteur ne contient pas, et que sa propre note n'est pas inférieure, c'est lui qui gagne."""
    from .util import md_plain, words

    spec = next((x for x in specs if x.name == "pdflite" and x.is_available()), None)
    if spec is None:
        spec = next((x for x in engines_for("pdf") if x.name == "pdflite"), None)
    if spec is None:
        return None
    ctx = base.fork()
    try:
        res = spec.fn(src, ctx)
    except Exception:
        ctx.cleanup()
        return None
    res.engine, res.fmt = "pdflite", res.fmt or "pdf"
    native_cells = _table_cells(res.markdown)
    if len(native_cells) < 4:
        ctx.cleanup()
        return None
    other = " " + " ".join(words(md_plain(best[1].markdown))) + " "
    missing = [c for c in native_cells if f" {c} " not in other]
    score = assess(res)
    if missing and score.value >= best[0].value - 0.05:
        res.score = score.value
        out.attempts.append({"engine": "pdflite", "status": "ok", "score": round(score.value, 3), "words": score.words,
                             "notes": [f"tableaux : {len(missing)} cellule(s) absente(s) de la sortie de {best[1].engine}, lecteur natif retenu"]})
        best[2].cleanup()
        return (score, res, ctx)
    ctx.cleanup()
    return None


def _pick_best(pool: List[tuple]) -> Optional[tuple]:
    """Meilleure tentative : la note la plus haute ; à égalité (à 0,03 près) la plus proche du consensus des autres moteurs.

    Quand aucun moteur n'atteint le seuil, plusieurs notes sont voisines (document peu dense, par exemple) ; l'ordre de priorité
    seul donnerait la sortie d'un moteur qui a pu lire du bruit (OCR d'une page à l'envers, colonnes mélangées). Un texte que
    les autres moteurs ne retrouvent pas est suspect ; un texte qu'ils retrouvent presque tous est fiable.
    """
    if not pool:
        return None
    top = max(p[1].value for p in pool)
    close = [(i, p) for i, p in enumerate(pool) if p[1].value >= top - 0.03]
    if len(pool) < 3 or len(close) == 1:
        chosen = next(p for p in pool if p[1].value >= top - 1e-9)      # priorité d'ordre à égalité de note
    else:
        def consensus(p: tuple) -> float:
            others = [q for q in pool if q is not p]
            return sum(_agreement(p[2].markdown, q[2].markdown) for q in others) / len(others)

        chosen = max(close, key=lambda ip: (round(consensus(ip[1]), 2), ip[1][1].value, -ip[0]))[1]
    for p in pool:
        if p is not chosen:
            p[3].cleanup()
    return (chosen[1], chosen[2], chosen[3])


def _order_specs(fmt: str, opts: Options):
    specs = [s for s in engines_for(fmt) if s.name not in OPT_IN_ENGINES or (opts.engines and s.name in opts.engines)]
    if not opts.external:
        specs = [s for s in specs if s.kind == "native"]
    if opts.engines:
        by_name: Dict[str, List] = {}
        for s in specs:
            by_name.setdefault(s.name, []).append(s)
        ordered = []
        for name in opts.engines:
            ordered.extend(by_name.get(name, []))
        return ordered
    return specs


def convert_to_memory(src: Path, opts: Options, rel: str = "", assets_dir: str = "assets",
                      det: Optional[Detected] = None, verbose: bool = False) -> Outcome:
    """Convertit un fichier sans rien écrire. Ne lève jamais : les échecs sont dans ``Outcome``."""
    t0 = time.time()
    src = Path(src)
    rel = rel or src.name
    try:
        det = det or detect(src)
    except Exception as exc:  # fichier illisible, permissions…
        return Outcome(src, rel, Detected("binary"), "error", error=f"lecture impossible : {exc}")
    out = Outcome(src, rel, det)
    size_mb = src.stat().st_size / (1 << 20)
    if size_mb > opts.max_size_mb:
        out.status, out.error = "unsupported", f"fichier trop volumineux ({size_mb:.0f} Mo > {opts.max_size_mb} Mo)"
        return out
    base = Ctx(src, opts, assets_dir, origin=rel)
    if det.fmt in UNSUPPORTED_HINTS and not engines_for(det.fmt):
        out.status, out.error = "unsupported", UNSUPPORTED_HINTS[det.fmt] + (f" ({det.note})" if det.note and det.fmt == "encrypted" else "")
        return out
    specs = _order_specs(det.fmt, opts)
    if not specs:
        out.status = "unsupported"
        out.error = UNSUPPORTED_HINTS.get(det.fmt, f"aucun convertisseur pour le format « {det.label} »")
        return out

    best: Optional[tuple] = None  # (score, result, ctx)
    pool: List[tuple] = []         # (moteur, note, résultat, contexte) de chaque tentative réussie
    protected: Optional[str] = None
    for spec in specs:
        if not spec.is_available():
            out.attempts.append({"engine": spec.name, "status": "indisponible"})
            continue
        ctx = base.fork()
        ts = time.time()
        try:
            if spec.kind == "external" and not verbose:
                # les bibliothèques tierces (pymupdf4llm, docling, markitdown…) bavardent sur stdout/stderr : ne jamais
                # polluer un Markdown envoyé sur la sortie standard (-o -)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    res = spec.fn(src, ctx)
            else:
                res = spec.fn(src, ctx)
        except Protected as exc:
            protected = str(exc)
            out.attempts.append({"engine": spec.name, "status": "protégé", "detail": str(exc)})
            ctx.cleanup()
            break
        except Unsupported as exc:
            out.attempts.append({"engine": spec.name, "status": "non pris en charge", "detail": str(exc)})
            ctx.cleanup()
            continue
        except MemoryError:
            out.attempts.append({"engine": spec.name, "status": "erreur", "detail": "mémoire insuffisante"})
            ctx.cleanup()
            continue
        except Exception as exc:  # un moteur ne doit jamais faire tomber le lot
            detail = f"{type(exc).__name__}: {exc}"
            if verbose:
                detail += "\n" + traceback.format_exc()
            out.attempts.append({"engine": spec.name, "status": "erreur", "detail": detail})
            ctx.cleanup()
            continue
        res.engine = spec.name if spec.name != "native" else "native"
        res.fmt = res.fmt or det.fmt
        score = assess(res)
        res.score = score.value
        out.attempts.append({"engine": spec.name, "status": "ok", "score": round(score.value, 3),
                             "words": score.words, "seconds": round(time.time() - ts, 3),
                             **({"notes": score.notes} if score.notes else {})})
        pool.append((spec.name, score, res, ctx))
        if score.value >= opts.quality_threshold and not opts.compare:
            break
    best = _pick_best(pool)
    out.seconds = time.time() - t0
    if best is None:
        if protected:
            out.status, out.error = "unsupported", "fichier protégé par mot de passe : " + protected
        else:
            details = "; ".join(f"{a['engine']}: {a.get('detail', a['status'])}" for a in out.attempts) or "aucun moteur disponible"
            damaged = next((a["detail"] for a in out.attempts if "abîmé ou tronqué" in str(a.get("detail", ""))), "")
            if damaged:                       # le diagnostic utile d'abord ; les erreurs techniques des moteurs ne servent à rien à l'utilisateur
                details = damaged
            hint = UNSUPPORTED_HINTS.get(det.fmt, "")
            out.status = "error" if any(a["status"] == "erreur" for a in out.attempts) else "unsupported"
            out.error = details + (f" — {hint}" if hint else "")
        return out
    if det.fmt == "pdf" and best[1].engine != "pdflite" and not opts.compare and (not opts.engines or "pdflite" in opts.engines):
        best = _native_pdf_tables_win(best, specs, src, base, out) or best
    score, res, ctx = best
    out.score, out.result, out.ctx = score, res, ctx
    if opts.render:
        try:
            from .preview import make_previews

            make_previews(src, det.fmt, ctx)
        except Exception as exc:      # un aperçu raté ne doit jamais faire perdre la conversion
            ctx.warn(f"--render : {exc}")
    body = normalize_markdown(res.markdown)
    title = str(res.meta.get("title") or res.title or "").strip()
    if title and not re.search(r"(?m)^#\s+\S", body):
        first = re.search(r"(?m)^#{1,6}\s+(.+?)\s*$", body)
        def norm(t: str) -> str:
            return re.sub(r"[\s*_`\\]+", " ", t).strip().casefold()

        # inutile d'ajouter un H1 si le premier titre du corps porte déjà le titre du document (« Slide 1 — Titre »)
        if not (first and norm(title) in norm(first.group(1))):
            body = f"# {title}\n\n{body}"
    problems = lint_markdown(body)
    for p in problems:
        ctx.warn("structure Markdown : " + p)
    blind = len(re.findall(r"(?<!\\)!\[\]\(", body))      # image extraite sans texte alternatif : son contenu n'a pas été lu
    if blind:
        _flag_informative_images(body, ctx)
        ctx.warn(f"{blind} image(s) sans texte alternatif (![](…)) : à ouvrir si leur contenu compte (schéma, capture, graphique)")
    for n in score.notes:
        ctx.warn(n)
    if det.ext_mismatch:
        ctx.warn(f"l'extension .{det.ext} ne correspond pas au contenu réel ({det.label})")
    if det.note and det.note not in ("macros", "structure atypique") and not det.note.startswith("OLE"):
        ctx.warn(det.note)
    if opts.no_vision:
        body = _apply_no_vision(body, ctx)
    out.body = body
    if ctx.vision:
        out.status = "needs_vision"
    elif score.value < opts.quality_threshold or ctx.unread:
        out.status = "warn"
    return out


_VISION_MARK = re.compile(r"> \*\*\[À COMPLÉTER : (?:lecture|description) visuelle\]\*\*")


def _apply_no_vision(body: str, ctx: Ctx) -> str:
    """--no-vision : rien n'est proposé à la lecture visuelle. Les rendus PNG créés pour elle sont retirés,
    les marqueurs « à compléter » deviennent « NON LU » et les éléments sont comptés à part dans le rapport."""
    prefix = ctx.assets_dir + "/"
    for v in ctx.vision:
        if v.kind in ("page", "svg") and v.path.startswith(prefix):       # rendus fabriqués pour être regardés
            body = re.sub(r"(?m)^!\[[^\]]*\]\(" + re.escape(v.path) + r"\)[ \t]*\n*", "", body)
            ctx.assets.pop(v.path[len(prefix):], None)
        item = {"kind": v.kind, "reason": v.reason}
        if v.pages:
            item["pages"] = v.pages
        ctx.unread.append(item)
    body, n = _VISION_MARK.subn("> **[NON LU : lecture visuelle désactivée]**", body)
    ctx.vision = []
    total = max(n, len(ctx.unread))
    if total:
        ctx.warn(f"--no-vision : {total} élément(s) non textuel(s) volontairement non lu(s) (marqueur « NON LU »)")
    return body


def report_entry(out: Outcome, out_md: Optional[str] = None) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "source": out.rel.replace(os.sep, "/"),
        "format": out.det.label,
        "status": out.status,
    }
    if out_md:
        d["output"] = out_md.replace(os.sep, "/")
    if out.result:
        d.update({
            "engine": out.result.engine,
            "score": round(out.score.value, 3) if out.score else None,
            "recall": round(out.score.recall, 4) if out.score and out.score.recall is not None else None,
            "words": out.score.words if out.score else 0,
            "tokens_est": est_tokens(out.body),
            "title": out.result.title or None,
            "assets": len(out.ctx.assets) if out.ctx else 0,
        })
    if out.ctx and out.ctx.warnings:
        d["warnings"] = list(out.ctx.warnings)
    if out.ctx and out.ctx.vision:
        d["vision"] = [v.as_dict() for v in out.ctx.vision]
    if out.ctx and out.ctx.unread:
        d["unread"] = list(out.ctx.unread)
    if out.ctx and out.ctx.previews:
        d["previews"] = list(out.ctx.previews)
    if out.error:
        d["error"] = out.error
    d["seconds"] = round(out.seconds, 3)
    if out.attempts:
        d["attempts"] = out.attempts
    if out.children:
        d["children"] = out.children
    return {k: v for k, v in d.items() if v not in (None, [], {})}
