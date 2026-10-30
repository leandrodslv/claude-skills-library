#!/usr/bin/env python3
"""Banc d'essai reproductible : mdconv contre d'autres convertisseurs sur des documents à contenu connu.

    python3 benchmark/run.py                      # corpus temporaire, convertisseurs disponibles, écrit RESULTS.md
    python3 benchmark/run.py --keep corpus/       # garde les fichiers générés
    python3 benchmark/run.py --only mdconv-natif,pandoc --out -

Producteurs du corpus (python-docx, python-pptx, openpyxl, LibreOffice) et concurrents (markitdown,
pymupdf4llm, pandoc, pdftotext) sont OPTIONNELS : ceux qui manquent sont simplement absents du tableau.
Méthode et limites : benchmark/README.md.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import corpus  # noqa: E402
import metrics  # noqa: E402

warnings.filterwarnings("ignore")
METRICS = ("recall", "precision", "headings", "tables", "lists", "links")
LABELS = {"recall": "Rappel", "precision": "Précision", "headings": "Titres", "tables": "Tableaux", "lists": "Listes", "links": "Liens"}

Runner = Callable[[Path], str]


# --------------------------------------------------------------------------
# Convertisseurs
# --------------------------------------------------------------------------

def _mdconv(external: bool) -> Runner:
    from mdconv.core import Options
    from mdconv.pipeline import convert_to_memory

    def run(path: Path) -> str:
        opts = Options(frontmatter="none", images="skip", external=external)
        out = convert_to_memory(path, opts, rel=path.name, assets_dir="a")
        if not out.result:
            raise RuntimeError(out.error or out.status)
        return out.body
    return run


def _markitdown() -> Optional[Runner]:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return None
    md = MarkItDown()
    return lambda p: md.convert(str(p)).text_content


def _pymupdf4llm() -> Optional[Runner]:
    try:
        import pymupdf4llm
    except ImportError:
        return None
    return lambda p: pymupdf4llm.to_markdown(str(p))


def _pandoc() -> Optional[Runner]:
    exe = shutil.which("pandoc")
    if not exe:
        return None

    def run(p: Path) -> str:
        r = subprocess.run([exe, "-t", "gfm", "--wrap=none", str(p)], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:120])
        return r.stdout
    return run


def _pdftotext() -> Optional[Runner]:
    exe = shutil.which("pdftotext")
    if not exe:
        return None

    def run(p: Path) -> str:
        r = subprocess.run([exe, "-layout", str(p), "-"], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:120])
        return r.stdout
    return run


# nom → (fabrique, formats pris en charge, description)
def converters() -> Dict[str, Tuple[Optional[Runner], Optional[set], str]]:
    all_fmt = {"docx", "odt", "rtf", "pdf", "pptx", "xlsx", "csv", "html"}
    return {
        "mdconv-natif": (_mdconv(False), all_fmt, "mdconv, bibliothèque standard seule (--no-external)"),
        "mdconv-auto": (_mdconv(True), all_fmt, "mdconv, moteurs externes utilisés s'ils sont installés"),
        "markitdown": (_markitdown(), all_fmt, "Microsoft markitdown"),
        "pandoc": (_pandoc(), {"docx", "odt", "rtf", "html", "pptx"}, "pandoc -t gfm"),
        "pymupdf4llm": (_pymupdf4llm(), {"pdf"}, "pymupdf4llm"),
        "pdftotext": (_pdftotext(), {"pdf"}, "pdftotext -layout (texte brut : pas de structure Markdown)"),
    }


# --------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------

def run_benchmark(files, only: Optional[List[str]], log) -> Dict[str, object]:
    convs = {k: v for k, v in converters().items() if v[0] is not None and (not only or k in only)}
    rows: List[Dict[str, object]] = []
    for path, docslug, fmt, truth in files:
        for name, (runner, fmts, _d) in convs.items():
            if fmts and fmt not in fmts:
                continue
            t0 = time.perf_counter()
            err = None
            try:
                out = runner(path)  # type: ignore[misc]
            except Exception as exc:  # noqa: BLE001
                if "Unknown input format" in str(exc):          # cette version de l'outil ne lit pas ce format : hors comparaison
                    continue
                out, err = "", f"{type(exc).__name__}: {str(exc)[:100]}"
            dt = time.perf_counter() - t0
            row: Dict[str, object] = {"converter": name, "document": docslug, "format": fmt, "file": path.name,
                                      "seconds": round(dt, 3), "error": err}
            row.update(metrics.score_output(truth, out) if not err else {m: None for m in METRICS})
            if err:
                row.update({"recall": 0.0, "precision": 0.0})
            rows.append(row)
            log(f"  {name:13s} {path.name:34s} " + (f"ERREUR {err}" if err else f"rappel {row['recall']:.0f} % · précision {row['precision']:.0f} %"))
    return {"rows": rows, "converters": {k: v[2] for k, v in convs.items()}}


def aggregate(rows: List[Dict[str, object]]) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    by: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
    for r in rows:
        by.setdefault(str(r["converter"]), {}).setdefault(str(r["format"]), []).append(r)
    out: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    for c, fm in by.items():
        out[c] = {}
        for f, rs in fm.items():
            agg: Dict[str, Optional[float]] = {m: metrics.mean([r[m] for r in rs]) for m in METRICS}  # type: ignore[misc]
            agg["seconds"] = statistics.median(float(r["seconds"]) for r in rs)  # type: ignore[arg-type]
            agg["errors"] = float(sum(1 for r in rs if r["error"]))
            agg["n"] = float(len(rs))
            out[c][f] = agg
    return out


def versions_line() -> str:
    v: List[str] = []
    try:
        import importlib.metadata as md
        for pkg in ("markitdown", "pymupdf4llm", "python-docx", "python-pptx", "openpyxl"):
            try:
                v.append(f"{pkg} {md.version(pkg)}")
            except md.PackageNotFoundError:
                pass
    except ImportError:
        pass
    for exe, args in (("pandoc", ["--version"]), ("pdftotext", ["-v"]), ("soffice", ["--version"])):
        path = shutil.which(exe)
        if path:
            r = subprocess.run([path, *args], capture_output=True, text=True, timeout=60)
            first = ((r.stdout or r.stderr).strip().splitlines() or [""])[0]
            v.append(first[:60])
    return "Versions : " + " · ".join(v)


def _f(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.0f}"


def render_markdown(result: Dict[str, object], files_n: int) -> str:
    rows = result["rows"]  # type: ignore[assignment]
    agg = aggregate(rows)  # type: ignore[arg-type]
    descr: Dict[str, str] = result["converters"]  # type: ignore[assignment]
    formats = sorted({str(r["format"]) for r in rows})  # type: ignore[union-attr]
    out = ["# Résultats du banc d'essai", "",
           f"_{files_n} fichiers · {len(set(r['document'] for r in rows))} documents · Python {platform.python_version()} · {platform.system()} · "  # type: ignore[union-attr]
           f"généré par `benchmark/run.py`_", "",
           "Scores en % (plus haut = mieux). **Rappel** : mots du contenu retrouvés ; **Précision** : part de la sortie qui est du vrai contenu (pénalise doublons et bruit) ; "
           "**Titres / Tableaux / Listes / Liens** : éléments de structure retrouvés comme tels en Markdown. « — » : sans objet pour ce format. "
           "Temps : médiane par fichier, convertisseur déjà chargé (pandoc et pdftotext : processus lancé à chaque fichier).", "",
           "## Vue d'ensemble", "",
           "| Convertisseur | Formats couverts | Rappel | Précision | Titres | Tableaux | Listes | Liens | Temps médian (s) |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    def overall(fm: Dict[str, Dict[str, Optional[float]]]) -> float:
        return metrics.mean([metrics.mean([v[m] for m in METRICS]) for v in fm.values()]) or 0.0

    for c, fm in sorted(agg.items(), key=lambda kv: (-len(kv[1]), -overall(kv[1]))):
        cols = [metrics.mean([v[m] for v in fm.values()]) for m in METRICS]
        t = statistics.median(v["seconds"] for v in fm.values())  # type: ignore[type-var]
        out.append(f"| **{c}** | {len(fm)}/{len(formats)} | " + " | ".join(_f(x) for x in cols) + f" | {t:.2f} |")
    out += ["", "_Moyenne sur les formats que chaque convertisseur accepte : un outil spécialisé (pdftotext, pymupdf4llm : PDF seulement) n'est comparable qu'à la ligne PDF ci-dessous._", ""]
    for f in formats:
        out += [f"## {f.upper()}", "", "| Convertisseur | " + " | ".join(LABELS[m] for m in METRICS) + " | Erreurs | Temps (s) |",
                "| --- | " + " | ".join("---:" for _ in METRICS) + " | ---: | ---: |"]
        for c in sorted(agg, key=lambda c: -(((agg[c].get(f) or {}).get("recall")) or -1)):
            v = agg[c].get(f)
            if not v:
                continue
            out.append(f"| {c} | " + " | ".join(_f(v[m]) for m in METRICS) + f" | {int(v['errors'] or 0)} | {v['seconds']:.2f} |")
        out.append("")
    out += ["## Convertisseurs et versions", ""] + [f"- **{k}** — {d}" for k, d in descr.items()] + ["", versions_line(), ""]
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Banc d'essai mdconv vs autres convertisseurs (contenu connu).")
    ap.add_argument("--keep", metavar="DOSSIER", help="écrit le corpus généré dans ce dossier (sinon dossier temporaire)")
    ap.add_argument("--only", help="liste de convertisseurs séparés par des virgules")
    ap.add_argument("--out", default=str(HERE / "RESULTS.md"), help="fichier Markdown de résultats (« - » : sortie standard)")
    ap.add_argument("--json", metavar="FICHIER", help="écrit aussi les mesures détaillées en JSON")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)
    log = (lambda s: None) if a.quiet else (lambda s: print(s, file=sys.stderr))
    tmp = None
    if a.keep:
        target = Path(a.keep)
    else:
        tmp = tempfile.mkdtemp(prefix="mdbench_")
        target = Path(tmp)
    try:
        log("Génération du corpus…")
        files = corpus.build_corpus(target, log)
        if not files:
            print("Aucun fichier généré : installer au moins python-docx, python-pptx, openpyxl ou LibreOffice.", file=sys.stderr)
            return 1
        log(f"{len(files)} fichiers. Conversion…")
        result = run_benchmark(files, a.only.split(",") if a.only else None, log)
        md = render_markdown(result, len(files))
        if a.out == "-":
            print(md)
        else:
            Path(a.out).write_text(md, encoding="utf-8")
            log(f"Résultats : {a.out}")
        if a.json:
            Path(a.json).write_text(json.dumps(result["rows"], ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
