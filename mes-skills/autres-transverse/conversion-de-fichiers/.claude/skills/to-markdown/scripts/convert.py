#!/usr/bin/env python3
"""convert.py — convertit n'importe quel fichier (Word, PowerPoint, Excel, SVG, PDF, HTML, images…) en Markdown.

Usage :
    python convert.py <fichier|dossier> [...] [-o SORTIE] [options]
    python convert.py --doctor          # moteurs disponibles sur cette machine
    python convert.py --check SORTIE/   # vérifie un dossier déjà converti

Bibliothèque standard uniquement pour le noyau ; les outils externes
(LibreOffice, pdftotext, pandoc, tesseract, markitdown…) sont facultatifs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mdconv.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
