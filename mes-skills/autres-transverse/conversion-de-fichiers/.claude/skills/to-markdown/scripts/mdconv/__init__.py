"""mdconv — convertit n'importe quel fichier (Word, PowerPoint, Excel, SVG, PDF, HTML…) en Markdown.

Noyau en bibliothèque standard ; moteurs externes optionnels (LibreOffice,
pdftotext, pandoc, tesseract, markitdown…) utilisés en repli ou en renfort.
"""
from .core import VERSION, Options  # noqa: F401

__version__ = VERSION
