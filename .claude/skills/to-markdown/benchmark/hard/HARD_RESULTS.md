# Batterie de documents difficiles — résultats

_49 documents · généré par `benchmark/hard/run_hard.py` · voir [README](README.md) pour la méthode_

✅ conforme (≥ 95 % des attentes) · ⚠️ partiel (70-95 %) · ❌ échec · 👁 contenu non extrait **mais signalé** à lire visuellement. Le score est la part des vérifications réussies (texte, ordre, doublons, bruit, structure).

## Synthèse

| Convertisseur | ✅ | ⚠️ | ❌ | 👁 | Score moyen |
| --- | ---: | ---: | ---: | ---: | ---: |
| **mdconv-natif** (49 docs) | 46 | 0 | 0 | 3 | 95 |
| **mdconv-auto** (49 docs) | 48 | 0 | 0 | 1 | 98 |
| **markitdown** (26 docs) | 9 | 7 | 10 | 0 | 70 |
| **pandoc** (12 docs) | 3 | 5 | 4 | 0 | 74 |
| **pymupdf4llm** (9 docs) | 5 | 1 | 3 | 0 | 85 |

## Document par document

| Document | Difficulté | mdconv-natif | mdconv-auto | markitdown | pandoc | pymupdf4llm |
| --- | :---: | ---: | ---: | ---: | ---: | ---: |
| `data-archive-imbriquee` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-docx-tronque` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | ✅ 100 | — |
| `data-faux-docx` | ●● | ✅ 100 | ✅ 100 | ✅ 100 | ❌ 0 | — |
| `data-json-profond` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-odt-liste-tableau` | ●●● | ✅ 100 | ✅ 100 | ❌ 0 | ✅ 100 | — |
| `data-pdf-tronque` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | ✅ 100 |
| `data-pdf-tronque-partiel` | ●●●● | ✅ 100 | ✅ 100 | ❌ 0 | — | ❌ 67 |
| `data-rtf-liste-tableau` | ●●● | ✅ 100 | ✅ 100 | ❌ 62 | ⚠️ 85 | — |
| `data-sqlite-relationnelle` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-cp1252` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-koi8r` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-latin2` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-shiftjis` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-utf16` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-xml-namespaces` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `docx-listes-imbriquees` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 75 | ⚠️ 75 | — |
| `docx-multilingue-rtl-cjk` | ●●● | ✅ 100 | ✅ 100 | ✅ 100 | ✅ 100 | — |
| `docx-notes-commentaires-revisions` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 86 | ⚠️ 86 | — |
| `docx-sommaire-equation-controle` | ●●●● | ✅ 100 | ✅ 100 | ❌ 57 | ⚠️ 86 | — |
| `docx-tableaux-fusionnes` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 88 | ❌ 38 | — |
| `docx-zone-texte-entete` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | ❌ 60 | — |
| `legacy-budget-formules-masques` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `legacy-groupes-graphique-notes` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `legacy-tableaux-fusionnes` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `pdf-article-deux-colonnes` | ●●●● | ✅ 100 | ✅ 100 | ❌ 50 | — | ❌ 67 |
| `pdf-mixte-texte-scan-texte` | ●●●● | 👁 62 | ✅ 100 | ❌ 62 | — | ✅ 100 |
| `pdf-notes-de-bas-de-page` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 75 | — | ✅ 100 |
| `pdf-page-pivotee` | ●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | ✅ 100 |
| `pdf-scan-incline-bruite` | ●●●●● | 👁 0 | ✅ 100 | ❌ 0 | — | ✅ 100 |
| `pdf-tableau-bordures-fusionnees` | ●●●● | ✅ 100 | ✅ 100 | ❌ 25 | — | ❌ 50 |
| `pdf-tableau-sans-bordures` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 89 | — | ⚠️ 78 |
| `pptx-diapositive-image` | ●●● | 👁 0 | 👁 0 | ❌ 0 | — | — |
| `pptx-groupes-graphique-notes` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | — |
| `pptx-schema-formes-libres` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | — |
| `svg-architecture-courbes` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `svg-couloirs-processus` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `svg-flux-classes-css` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `svg-graphique-courbe` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `svg-organigramme-coudes` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `svg-pointes-dessinees` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-article-bruite` | ●●● | ✅ 100 | ✅ 100 | ❌ 64 | ❌ 64 | — |
| `web-drawio-sequence` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-email-multipartie` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-epub-chapitres-notes` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-html-structure-tordue` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 95 | ⚠️ 90 | — |
| `web-notebook-sorties` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-svg-processus` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `xlsx-budget-formules-masques` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 93 | — | — |
| `xlsx-grande-feuille-large` | ●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | — |

## Limites constatées de mdconv

Documents où `mdconv-auto` n'est pas ✅, avec ce qui manque (à améliorer en priorité) :

### `pptx-diapositive-image` — 👁 0 %

**Difficulté :** toute l'information est dans une image (aucun texte, aucun texte alternatif)

- contenu non extrait mais signalé à lire visuellement (comportement attendu)
- texte absent : « Chiffre d'affaires 2025 »
- texte absent : « 4,2 M€ »
- texte absent : « Objectif 2026 : 5 M€ »

_Autres convertisseurs : markitdown ❌0_

_Sans OCR, le contenu ne peut pas être extrait : il doit au moins être signalé « à lire visuellement »._

