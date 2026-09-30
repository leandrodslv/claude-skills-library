"""`convert.py --doctor` : ce que cette machine sait convertir, à quel niveau, et comment aller plus loin."""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from . import external as ext
from .core import VERSION, engines_for

# (identifiant, libellé, [extensions])
FORMATS = [
    ("docx", "Word (.docx)", ".docx .docm .dotx"), ("pptx", "PowerPoint (.pptx)", ".pptx .ppsx .potx"),
    ("xlsx", "Excel (.xlsx)", ".xlsx .xlsm"), ("odt", "OpenDocument texte", ".odt"), ("odp", "OpenDocument présentation", ".odp"),
    ("ods", "OpenDocument tableur", ".ods"), ("rtf", "RTF", ".rtf"), ("doc", "Word 97-2003 (.doc)", ".doc"),
    ("ppt", "PowerPoint 97-2003 (.ppt)", ".ppt .pps"), ("xls", "Excel 97-2003 (.xls)", ".xls"), ("xlsb", "Excel binaire", ".xlsb"),
    ("pdf", "PDF", ".pdf"), ("svg", "SVG", ".svg"), ("drawio", "draw.io", ".drawio"), ("html", "HTML", ".html .htm"),
    ("epub", "EPUB", ".epub"), ("csv", "CSV / TSV", ".csv .tsv"), ("json", "JSON / JSONL", ".json .jsonl"),
    ("ipynb", "Notebook Jupyter", ".ipynb"), ("xml", "XML / RSS", ".xml"), ("md", "Markdown / texte / code", ".md .txt .py …"),
    ("eml", "E-mail", ".eml .mbox"), ("msg", "Outlook", ".msg"), ("image", "Images", ".png .jpg .gif .webp .tiff"),
    ("markup", "LaTeX / reST / Org", ".tex .rst .org"), ("sqlite", "Base SQLite", ".db .sqlite .sqlite3"),
    ("odg", "OpenDocument dessin", ".odg"), ("vsdx", "Visio", ".vsdx"), ("xml2003-sheet", "Excel XML 2003", ".xml .xls"), ("xml2003-word", "Word XML 2003", ".xml"), ("audio", "Audio / vidéo", ".mp3 .wav .mp4"),
]

INSTALL = {
    "libreoffice": "apt install libreoffice-writer libreoffice-calc libreoffice-impress   |   brew install --cask libreoffice   |   winget install LibreOffice",
    "poppler": "apt install poppler-utils   |   brew install poppler",
    "tesseract": "apt install tesseract-ocr tesseract-ocr-fra   |   brew install tesseract tesseract-lang",
    "pandoc": "apt install pandoc   |   brew install pandoc",
    "pdf-python": "pip install pymupdf4llm      (meilleure structure des PDF : titres, tableaux, colonnes) ; pdfplumber (pip install pdfplumber) pour les PDF à tableaux : --engines pdfplumber",
    "markitdown": "pip install 'markitdown[all]'      (second avis sur de nombreux formats)",
    "svg": "apt install librsvg2-bin   |   brew install librsvg      (rendu PNG des SVG pour lecture visuelle)",
    "whisper": "pip install faster-whisper      (transcription audio/vidéo, sur demande : --engines whisper)",
}


def collect(timeout: int = 90) -> Dict[str, Any]:
    caps = ext.capabilities(timeout)
    rows: List[Dict[str, Any]] = []
    for fid, label, exts in FORMATS:
        specs = engines_for(fid)
        avail = [s for s in specs if s.is_available()]
        native = [s.name for s in avail if s.kind == "native" and s.name != "archive"]
        external = [s.name for s in avail if s.kind == "external"]
        if fid in ("audio",):
            level = "opt-in" if external else "absent"
        elif fid == "image":
            level = "métadonnées + OCR" if ext.has_ocr() else "métadonnées + lecture visuelle"
        elif native and fid not in ("markup",):
            level = "natif"
        elif external:
            level = "externe"
        elif native:
            level = "natif"
        else:
            level = "absent"
        rows.append({"format": fid, "label": label, "extensions": exts, "niveau": level, "moteurs": native + external,
                     "manquants": [s.name for s in specs if not s.is_available()]})
    return {"version": VERSION, "capabilities": caps, "formats": rows}


def advice(caps: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    lo = caps["libreoffice"]
    if not (lo.get("writer") and lo.get("calc") and lo.get("impress")):
        out.append("Formats .doc/.xls/.ppt de meilleure fidélité : " + INSTALL["libreoffice"])
    if not caps["pdf"].get("pdftotext"):
        out.append("PDF plus rapides et fidèles : " + INSTALL["poppler"])
    mods = caps["modules"]
    if not (mods.get("pymupdf4llm") or mods.get("docling")):
        out.append("Structure des PDF (tableaux, titres) : " + INSTALL["pdf-python"])
    if not caps["ocr"]["tesseract"]:
        out.append("OCR des PDF scannés et des images : " + INSTALL["tesseract"])
    elif "fra" not in caps["ocr"]["langues"]:
        out.append("OCR français : installer le paquet de langue tesseract-ocr-fra")
    if not caps["svg_renderers"]:
        out.append("Rendu PNG des SVG/diagrammes : " + INSTALL["svg"])
    if not caps["pandoc"]:
        out.append("LaTeX/reST/Org : " + INSTALL["pandoc"])
    return out


def run_doctor(as_json: bool = False, timeout: int = 90) -> int:
    data = collect(timeout)
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    caps = data["capabilities"]
    w = sys.stdout.write
    w(f"mdconv {VERSION} — diagnostic\n")
    w(f"Python {caps['python']} · {caps['platform']}\n\n")
    w("Noyau natif (aucune installation requise) : Word, PowerPoint, Excel, OpenDocument, RTF, SVG/draw.io/Graphviz,\n")
    w("HTML, EPUB, CSV/JSON/XML/YAML, notebooks, e-mails (.eml/.mbox/.msg), PDF à texte, archives (zip/tar/gz).\n\n")
    w("Moteurs optionnels (testés pour de vrai) :\n")
    lo = caps["libreoffice"]
    mods = ", ".join(k for k in ("writer", "calc", "impress") if lo.get(k)) or "aucun module fonctionnel"
    w(f"  {'✓' if lo.get('writer') else '✗'} LibreOffice        {lo.get('binaire') or 'absent'} ({mods})\n")
    w(f"  {'✓' if caps['pandoc'] else '✗'} pandoc             {caps['pandoc'] or 'absent'}\n")
    pdf = caps["pdf"]
    w(f"  {'✓' if pdf.get('pdftotext') else '✗'} poppler            pdftotext={'oui' if pdf.get('pdftotext') else 'non'} pdftoppm={'oui' if pdf.get('pdftoppm') else 'non'}\n")
    ocr = caps["ocr"]
    w(f"  {'✓' if ocr['tesseract'] else '✗'} tesseract (OCR)    langues : {', '.join(ocr['langues']) or '—'}\n")
    w(f"  {'✓' if caps['svg_renderers'] else '✗'} rendu SVG → PNG    {', '.join(caps['svg_renderers']) or 'aucun'}\n")
    m = caps["modules"]
    pymods = [k for k in ("pymupdf4llm", "pdfplumber", "pypdfium2", "pypdf", "markitdown", "docling", "openpyxl", "PIL") if m.get(k)]
    w(f"  {'✓' if pymods else '✗'} modules Python      {', '.join(pymods) or 'aucun'}\n\n")
    w("Couverture par format :\n")
    for r in data["formats"]:
        mark = {"natif": "✓", "externe": "◐", "absent": "✗", "opt-in": "◐"}.get(r["niveau"], "◐")
        w(f"  {mark} {r['label']:<28} {r['niveau']:<32} {', '.join(r['moteurs'])}\n")
    tips = advice(caps)
    if tips:
        w("\nPour aller plus loin :\n")
        for t in tips:
            w(f"  - {t}\n")
    w("\nLégende : ✓ couvert  ◐ couvert via un moteur externe ou avec limites  ✗ non couvert sur cette machine.\n")
    return 0
