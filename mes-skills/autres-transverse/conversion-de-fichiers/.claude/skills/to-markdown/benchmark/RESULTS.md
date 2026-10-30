# Résultats du banc d'essai

_36 fichiers · 4 documents · Python 3.11.15 · Linux · généré par `benchmark/run.py`_

Scores en % (plus haut = mieux). **Rappel** : mots du contenu retrouvés ; **Précision** : part de la sortie qui est du vrai contenu (pénalise doublons et bruit) ; **Titres / Tableaux / Listes / Liens** : éléments de structure retrouvés comme tels en Markdown. « — » : sans objet pour ce format. Temps : médiane par fichier, convertisseur déjà chargé (pandoc et pdftotext : processus lancé à chaque fichier).

## Vue d'ensemble

| Convertisseur | Formats couverts | Rappel | Précision | Titres | Tableaux | Listes | Liens | Temps médian (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **mdconv-auto** | 8/8 | 100 | 95 | 100 | 100 | 100 | 100 | 0.00 |
| **mdconv-natif** | 8/8 | 100 | 95 | 100 | 100 | 92 | 100 | 0.01 |
| **markitdown** | 8/8 | 86 | 75 | 65 | 82 | 59 | 67 | 0.02 |
| **pandoc** | 4/8 | 99 | 93 | 98 | 100 | 100 | 75 | 0.05 |
| **pymupdf4llm** | 1/8 | 100 | 100 | 100 | 100 | 100 | — | 0.28 |
| **pdftotext** | 1/8 | 100 | 100 | 0 | 0 | 100 | — | 0.02 |

_Moyenne sur les formats que chaque convertisseur accepte : un outil spécialisé (pdftotext, pymupdf4llm : PDF seulement) n'est comparable qu'à la ligne PDF ci-dessous._

## CSV

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 71 | — | 100 | — | — | 0 | 0.00 |
| mdconv-auto | 100 | 71 | — | 100 | — | — | 0 | 0.00 |
| markitdown | 100 | 100 | — | 100 | — | — | 0 | 0.01 |

## DOCX

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.02 |
| mdconv-auto | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.02 |
| markitdown | 100 | 100 | 90 | 100 | 100 | 100 | 0 | 0.22 |
| pandoc | 98 | 100 | 90 | 100 | 100 | 100 | 0 | 0.11 |

## HTML

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.00 |
| mdconv-auto | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.00 |
| markitdown | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.01 |
| pandoc | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.03 |

## ODT

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.01 |
| mdconv-auto | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.00 |
| pandoc | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.04 |
| markitdown | 0 | 0 | — | — | — | — | 4 | 0.02 |

## PDF

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 97 | 100 | 100 | 50 | — | 0 | 0.01 |
| mdconv-auto | 100 | 99 | 100 | 100 | 100 | — | 0 | 0.27 |
| pymupdf4llm | 100 | 100 | 100 | 100 | 100 | — | 0 | 0.28 |
| markitdown | 100 | 100 | 0 | 75 | 96 | — | 0 | 0.07 |
| pdftotext | 100 | 100 | 0 | 0 | 100 | — | 0 | 0.02 |

## PPTX

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 93 | 100 | 100 | 100 | — | 0 | 0.01 |
| mdconv-auto | 100 | 93 | 100 | 100 | 100 | — | 0 | 0.01 |
| markitdown | 100 | 90 | 100 | 100 | 0 | — | 0 | 0.04 |

## RTF

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.01 |
| mdconv-auto | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 0.01 |
| pandoc | 98 | 70 | 100 | 100 | 100 | 0 | 0 | 0.06 |
| markitdown | 91 | 7 | 0 | 0 | 0 | 0 | 0 | 0.01 |

## XLSX

| Convertisseur | Rappel | Précision | Titres | Tableaux | Listes | Liens | Erreurs | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mdconv-natif | 100 | 100 | 100 | 100 | — | — | 0 | 0.00 |
| mdconv-auto | 100 | 100 | 100 | 100 | — | — | 0 | 0.00 |
| markitdown | 100 | 100 | 100 | 100 | — | — | 0 | 0.02 |

## Convertisseurs et versions

- **mdconv-natif** — mdconv, bibliothèque standard seule (--no-external)
- **mdconv-auto** — mdconv, moteurs externes utilisés s'ils sont installés
- **markitdown** — Microsoft markitdown
- **pandoc** — pandoc -t gfm
- **pymupdf4llm** — pymupdf4llm
- **pdftotext** — pdftotext -layout (texte brut : pas de structure Markdown)

Versions : markitdown 0.1.8 · pymupdf4llm 1.28.2 · python-docx 1.2.0 · python-pptx 1.0.2 · openpyxl 3.1.5 · pandoc 3.1.3 · pdftotext version 24.02.0 · LibreOffice 24.2.7.2 420(Build:2)
