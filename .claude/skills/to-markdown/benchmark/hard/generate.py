#!/usr/bin/env python3
"""Génère la batterie de documents difficiles dans hard/corpus/ et écrit manifest.json.

    python3 benchmark/hard/generate.py [--only docx,pdf] [--with-big]

Les producteurs (reportlab, Pillow, xlsxwriter, python-pptx, LibreOffice…) sont optionnels : une catégorie
dont l'outil manque est ignorée. Les fichiers générés sont versionnés : pas besoin de relancer pour s'en servir.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MODULES = ["gen_docx", "gen_office", "gen_pdf", "gen_web", "gen_data"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="catégories (séparées par des virgules) : docx, office, pdf, web, data")
    ap.add_argument("--with-big", action="store_true", help="ajoute les gros fichiers de charge (PDF de 300 pages, CSV de 200 000 lignes)")
    a = ap.parse_args(argv)
    only = set(a.only.split(",")) if a.only else None
    import gen_common
    gen_common.WITH_BIG = a.with_big
    cases = []
    for name in MODULES:
        short = name.replace("gen_", "")
        if only and short not in only:
            continue
        try:
            mod = importlib.import_module(name)
        except ImportError as exc:
            print(f"[ignoré] {name} : {exc}", file=sys.stderr)
            continue
        got = mod.build()
        print(f"{short:8s} {len(got)} documents", file=sys.stderr)
        cases += got
    path = HERE / "manifest.json"
    old = {}
    if path.exists() and only:
        old = {c["id"]: c for c in json.loads(path.read_text(encoding="utf-8"))}
    for c in cases:
        old[c.id] = c.to_json()
    merged = sorted(old.values(), key=lambda c: (c["category"], c["id"]))
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(merged)} documents dans le manifeste", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
