"""`convert.py --plan ENTRÉES` : avant de convertir, ce qui s'y trouve et les choix disponibles.

Analyse seulement (détection du format par le contenu, aucune conversion, aucun réseau, rien d'installé).
Pour chaque amélioration possible, dit si l'outil est déjà là, à quels fichiers il servirait et
comment l'installer : c'est à l'utilisateur de choisir, le skill n'installe jamais rien.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

from . import external as ext
from .core import VERSION

# Formats (identifiants de detect.py) concernés, et ce que l'outil apporte.
# `ok(caps)` dit si l'outil est déjà disponible sur cette machine.
OPTIONS: List[Dict[str, Any]] = [
    {"id": "tesseract", "titre": "OCR (tesseract)", "formats": ["image", "pdf"],
     "gain": "texte des scans, photos de documents et captures ; sans lui ces pages passent en lecture visuelle par Claude",
     "install": "apt install tesseract-ocr tesseract-ocr-fra   |   brew install tesseract tesseract-lang",
     "ok": lambda c: bool(c["ocr"]["tesseract"])},
    {"id": "pymupdf4llm", "titre": "Structure PDF fine (pymupdf4llm)", "formats": ["pdf"],
     "gain": "titres, colonnes et tableaux complexes mieux restitués (licence AGPL / commerciale : à vérifier pour un usage pro)",
     "install": "pip install pymupdf4llm",
     "ok": lambda c: bool(c["modules"].get("pymupdf4llm") or c["modules"].get("docling"))},
    {"id": "poppler", "titre": "PDF rapides (poppler)", "formats": ["pdf"],
     "gain": "extraction plus rapide et fidèle du texte des PDF, rendu des pages en PNG",
     "install": "apt install poppler-utils   |   brew install poppler",
     "ok": lambda c: bool(c["pdf"].get("pdftotext"))},
    {"id": "libreoffice", "titre": "LibreOffice", "formats": ["doc", "ppt", "xls", "xlsb"],
     "gain": "anciens formats Office (.doc/.ppt/.xls) avec titres, listes et mise en forme ; sans lui : lecteurs natifs simplifiés",
     "install": "apt install libreoffice-writer libreoffice-calc libreoffice-impress   |   brew install --cask libreoffice   |   winget install LibreOffice",
     "ok": lambda c: bool(c["libreoffice"].get("writer") and c["libreoffice"].get("calc") and c["libreoffice"].get("impress"))},
    {"id": "svg", "titre": "Rendu SVG → PNG", "formats": ["svg", "drawio", "vsdx"],
     "gain": "aperçu PNG des schémas pour la lecture visuelle et la vérification",
     "install": "apt install librsvg2-bin   |   brew install librsvg",
     "ok": lambda c: bool(c["svg_renderers"])},
    {"id": "pandoc", "titre": "pandoc", "formats": ["markup"],
     "gain": "LaTeX, reStructuredText, Org : conversion complète au lieu d'une lecture simplifiée",
     "install": "apt install pandoc   |   brew install pandoc",
     "ok": lambda c: bool(c["pandoc"])},
    {"id": "whisper", "titre": "Transcription audio/vidéo (faster-whisper)", "formats": ["audio", "video"],
     "gain": "sans lui, l'audio et la vidéo ne sont pas convertis ; le premier usage télécharge un modèle (fait par faster-whisper, pas par le skill)",
     "install": "pip install faster-whisper      (puis : --engines whisper)",
     "ok": lambda c: bool(c["modules"].get("faster_whisper") or c["modules"].get("whisper")), "bloquant": True},
    {"id": "pyarrow", "titre": "Lecture Parquet (pyarrow)", "formats": ["parquet"],
     "gain": "sans lui, les fichiers Parquet ne sont pas lisibles (ou les exporter en CSV)",
     "install": "pip install pyarrow",
     "ok": lambda c: ext.has_module("pyarrow"), "bloquant": True},
]


def _count_formats(inputs: List[str], include: List[str], exclude: List[str]) -> Dict[str, Any]:
    from .cli import collect_inputs
    from .detect import detect

    files = collect_inputs(inputs, include, exclude, None)
    fmts: Counter = Counter()
    examples: Dict[str, List[str]] = {}
    for f in files:
        try:
            fmt = detect(f.src).fmt
        except OSError:
            fmt = "illisible"
        fmts[fmt] += 1
        examples.setdefault(fmt, [])
        if len(examples[fmt]) < 3:
            examples[fmt].append(f.rel)
    return {"total": len(files), "formats": dict(fmts.most_common()), "exemples": examples}


def build_plan(inputs: List[str], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None,
               timeout: int = 90) -> Dict[str, Any]:
    scan = _count_formats(inputs, include or [], exclude or [])
    caps = ext.capabilities(timeout)
    fmts = scan["formats"]
    choices: List[Dict[str, Any]] = []
    for o in OPTIONS:
        concerned = {f: fmts[f] for f in o["formats"] if f in fmts}
        if not concerned:
            continue
        ok = bool(o["ok"](caps))
        choices.append({
            "id": o["id"], "titre": o["titre"], "installe": ok, "fichiers": concerned,
            "gain": o["gain"], "install": o["install"], "bloquant": bool(o.get("bloquant")),
        })
    # OCR : la langue française manque
    if caps["ocr"]["tesseract"] and "fra" not in caps["ocr"]["langues"] and any(f in fmts for f in ("image", "pdf")):
        choices.append({"id": "tesseract-fra", "titre": "OCR : langue française", "installe": False,
                        "fichiers": {f: fmts[f] for f in ("image", "pdf") if f in fmts},
                        "gain": "meilleure lecture des accents et du français", "install": "apt install tesseract-ocr-fra   |   brew install tesseract-lang",
                        "bloquant": False})
    missing = [c for c in choices if not c["installe"]]
    return {"version": VERSION, "fichiers": scan, "choix": choices,
            "a_proposer": [c["id"] for c in missing], "pret": not missing}


def run_plan(inputs: List[str], include: List[str], exclude: List[str], as_json: bool = False, timeout: int = 90) -> int:
    if not inputs:
        print("--plan demande au moins un fichier ou un dossier.", file=sys.stderr)
        return 2
    plan = build_plan(inputs, include, exclude, timeout)
    if as_json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["fichiers"]["total"] else 1
    w = sys.stdout.write
    total = plan["fichiers"]["total"]
    if not total:
        w("Aucun fichier à convertir.\n")
        return 1
    w(f"mdconv {VERSION} — plan avant conversion\n\n{total} fichier(s) :\n")
    for fmt, n in plan["fichiers"]["formats"].items():
        w(f"  {n:>4} × {fmt}\n")
    w("\nChoix disponibles pour ces fichiers :\n")
    if not plan["choix"]:
        w("  (rien de plus à installer : le noyau natif suffit pour ces formats)\n")
    for c in plan["choix"]:
        mark = "✓ installé" if c["installe"] else ("✗ absent — NÉCESSAIRE pour ces fichiers" if c["bloquant"] else "✗ absent — optionnel")
        conc = ", ".join(f"{k} ×{v}" for k, v in c["fichiers"].items())
        w(f"  {mark:<8} {c['titre']}  [{conc}]\n")
        w(f"      apport : {c['gain']}\n")
        if not c["installe"]:
            w(f"      installer : {c['install']}\n")
    if plan["pret"]:
        w("\nTout ce qui peut servir ici est déjà installé : tu peux lancer la conversion.\n")
    else:
        w("\nRien n'est installé ni téléchargé par le skill. Choisis : installer un outil ci-dessus, puis relancer --plan,\n"
          "ou convertir tel quel (les fichiers concernés seront moins fins, ou signalés « unsupported » / à lire visuellement).\n")
    return 0
