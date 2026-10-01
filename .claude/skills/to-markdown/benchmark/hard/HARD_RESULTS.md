# Batterie de documents difficiles — résultats

_48 documents · généré par `benchmark/hard/run_hard.py` · voir [README](README.md) pour la méthode_

✅ conforme (≥ 95 % des attentes) · ⚠️ partiel (70-95 %) · ❌ échec · 👁 contenu non extrait **mais signalé** à lire visuellement. Le score est la part des vérifications réussies (texte, ordre, doublons, bruit, structure).

## Synthèse

| Convertisseur | ✅ | ⚠️ | ❌ | 👁 | Score moyen |
| --- | ---: | ---: | ---: | ---: | ---: |
| **mdconv-natif** (48 docs) | 36 | 4 | 6 | 2 | 86 |
| **mdconv-auto** (48 docs) | 37 | 3 | 8 | 0 | 87 |
| **markitdown** (25 docs) | 7 | 7 | 11 | 0 | 65 |
| **pandoc** (12 docs) | 3 | 5 | 4 | 0 | 74 |
| **pymupdf4llm** (8 docs) | 3 | 1 | 4 | 0 | 64 |

## Document par document

| Document | Difficulté | mdconv-natif | mdconv-auto | markitdown | pandoc | pymupdf4llm |
| --- | :---: | ---: | ---: | ---: | ---: | ---: |
| `data-archive-imbriquee` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-docx-tronque` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | ✅ 100 | — |
| `data-faux-docx` | ●● | ✅ 100 | ✅ 100 | ✅ 100 | ❌ 0 | — |
| `data-json-profond` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-odt-liste-tableau` | ●●● | ✅ 100 | ✅ 100 | ❌ 0 | ✅ 100 | — |
| `data-pdf-tronque` | ●●●● | ❌ 0 | ❌ 0 | ❌ 0 | — | ❌ 0 |
| `data-rtf-liste-tableau` | ●●● | ✅ 100 | ✅ 100 | ❌ 62 | ⚠️ 85 | — |
| `data-sqlite-relationnelle` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-cp1252` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-koi8r` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-latin2` | ●● | ❌ 0 | ❌ 0 | — | — | — |
| `data-texte-shiftjis` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-texte-utf16` | ●● | ✅ 100 | ✅ 100 | — | — | — |
| `data-xml-namespaces` | ●●● | ⚠️ 75 | ⚠️ 75 | — | — | — |
| `docx-listes-imbriquees` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 75 | ⚠️ 75 | — |
| `docx-multilingue-rtl-cjk` | ●●● | ✅ 100 | ✅ 100 | ✅ 100 | ✅ 100 | — |
| `docx-notes-commentaires-revisions` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 86 | ⚠️ 86 | — |
| `docx-sommaire-equation-controle` | ●●●● | ✅ 100 | ✅ 100 | ❌ 57 | ⚠️ 86 | — |
| `docx-tableaux-fusionnes` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 88 | ❌ 38 | — |
| `docx-zone-texte-entete` | ●●●● | ✅ 100 | ✅ 100 | ✅ 100 | ❌ 60 | — |
| `legacy-budget-formules-masques` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `legacy-groupes-graphique-notes` | ●●●● | ⚠️ 80 | ✅ 100 | — | — | — |
| `legacy-tableaux-fusionnes` | ●●●● | ❌ 67 | ❌ 67 | — | — | — |
| `pdf-article-deux-colonnes` | ●●●● | ✅ 100 | ❌ 67 | ❌ 50 | — | ❌ 67 |
| `pdf-mixte-texte-scan-texte` | ●●●● | 👁 62 | ✅ 100 | ❌ 62 | — | ✅ 100 |
| `pdf-notes-de-bas-de-page` | ●●● | ✅ 100 | ✅ 100 | ⚠️ 75 | — | ✅ 100 |
| `pdf-page-pivotee` | ●●● | ✅ 100 | ❌ 17 | ❌ 17 | — | ❌ 17 |
| `pdf-scan-incline-bruite` | ●●●●● | 👁 0 | ✅ 100 | ❌ 0 | — | ✅ 100 |
| `pdf-tableau-bordures-fusionnees` | ●●●● | ⚠️ 75 | ❌ 50 | ❌ 25 | — | ❌ 50 |
| `pdf-tableau-sans-bordures` | ●●●● | ❌ 22 | ⚠️ 78 | ⚠️ 89 | — | ⚠️ 78 |
| `pptx-diapositive-image` | ●●● | ❌ 0 | ❌ 0 | ❌ 0 | — | — |
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
| `web-email-multipartie` | ●●●● | ❌ 38 | ❌ 38 | — | — | — |
| `web-epub-chapitres-notes` | ●●● | ⚠️ 89 | ⚠️ 89 | — | — | — |
| `web-html-structure-tordue` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 95 | ⚠️ 90 | — |
| `web-notebook-sorties` | ●●● | ✅ 100 | ✅ 100 | — | — | — |
| `web-svg-processus` | ●●●● | ✅ 100 | ✅ 100 | — | — | — |
| `xlsx-budget-formules-masques` | ●●●● | ✅ 100 | ✅ 100 | ⚠️ 93 | — | — |
| `xlsx-grande-feuille-large` | ●●● | ✅ 100 | ✅ 100 | ✅ 100 | — | — |

## Limites constatées de mdconv

Documents où `mdconv-auto` n'est pas ✅, avec ce qui manque (à améliorer en priorité) :

### `data-pdf-tronque` — ❌ 0 %

**Difficulté :** PDF tronqué à 50 % (sans table de références ni fin de fichier)

- erreur : pymupdf4llm: FzErrorArgument: code=4: not a dict (null); docling: indisponible; pdftotext: pdftotext

_Autres convertisseurs : markitdown ❌0, pymupdf4llm ❌0_

_Récupération partielle bienvenue (le début du texte), sinon échec propre._

### `data-texte-latin2` — ❌ 0 %

**Difficulté :** texte non UTF-8 sans déclaration d'encodage (iso8859_2)

- texte absent : « Zażółć gęślą jaźń, pójdę do łóżka »

_L'encodage doit être deviné correctement (aucun caractère de remplacement)._

### `pptx-diapositive-image` — ❌ 0 %

**Difficulté :** toute l'information est dans une image (aucun texte, aucun texte alternatif)

- contenu perdu SANS signalement (aucun marqueur de lecture visuelle)
- texte absent : « Chiffre d'affaires 2025 »
- texte absent : « 4,2 M€ »
- texte absent : « Objectif 2026 : 5 M€ »

_Autres convertisseurs : markitdown ❌0_

_Sans OCR, le contenu ne peut pas être extrait : il doit au moins être signalé « à lire visuellement »._

### `pdf-page-pivotee` — ❌ 17 %

**Difficulté :** une page est marquée /Rotate 90 : le texte est dessiné dans le repère non pivoté

- texte absent : « Page pivotée de 90 degrés : tableau des écarts »
- texte absent : « Écart de calibrage : 0,8 mm »
- texte absent : « Écart de planéité : 1,2 mm »
- texte absent : « Écart angulaire : 0,3 degré »
- ordre de lecture : « Écart de calibrage » absent ou après son suivant

_Autres convertisseurs : markitdown ❌17, pymupdf4llm ❌17_

### `web-email-multipartie` — ❌ 38 %

**Difficulté :** sujet encodé, corps texte + HTML, tableau, pièce jointe texte, e-mail transféré en pièce jointe

- texte absent : « Bilan budgétaire »
- texte absent : « Nicolas »
- texte absent : « Planning de recette »
- texte absent : « Vérifier le budget restant : 18 400 euros »
- texte absent : « Validation du devis fournisseur »
- texte absent : « devis numéro 2025-0417 »
- ligne de tableau éclatée ou mal alignée : Bilan budgétaire | Nicolas
- ligne de tableau éclatée ou mal alignée : Planning de recette | Inès

_Un seul corps (texte OU HTML, pas les deux dupliqués) ; les pièces jointes texte et le message transféré doivent être lus._

### `pdf-tableau-bordures-fusionnees` — ❌ 50 %

**Difficulté :** tableau à traits avec cellules fusionnées horizontalement et verticalement

- ligne de tableau éclatée ou mal alignée : Nord | 410 | 455 | 900
- tableaux : 87 % retrouvés comme structure Markdown

_Autres convertisseurs : markitdown ❌25, pymupdf4llm ❌50_

_Chaque valeur doit rester sur la ligne de sa région ; les cellules fusionnées sont répétées ou clairement indiquées._

### `legacy-tableaux-fusionnes` — ❌ 67 %

**Difficulté :** Word 97-2003 (.doc) : tableau à cellules fusionnées

- tableaux : 0 % retrouvés comme structure Markdown

### `pdf-article-deux-colonnes` — ❌ 67 %

**Difficulté :** deux colonnes sur 3 pages, titre/résumé pleine largeur, en-tête et numéros de page répétés

- texte à exclure présent : « Page 2 sur 3 »
- « Journal of Examples — Vol. 12, 2025 » répété 2 fois (max 1)

_Autres convertisseurs : markitdown ❌50, pymupdf4llm ❌67_

_Ordre de lecture : colonne de gauche entière puis colonne de droite ; l'en-tête courant et les numéros de page ne doivent pas être répétés dans le corps._

### `data-xml-namespaces` — ⚠️ 75 %

**Difficulté :** XML à espaces de noms, CDATA avec chevrons et esperluette, contenu mixte (texte + éléments en ligne)

- texte absent : « fiche technique »
- texte absent : « avant toute commande »

_Le contenu mixte doit rester une phrase continue ; le CDATA doit être restitué littéralement._

### `pdf-tableau-sans-bordures` — ⚠️ 78 %

**Difficulté :** tableau sans aucun trait : seules les positions des colonnes le structurent

- ligne de tableau éclatée ou mal alignée : Produit | Référence | Prix unitaire | Stock | Statut
- tableaux : 97 % retrouvés comme structure Markdown

_Autres convertisseurs : markitdown ⚠️89, pymupdf4llm ⚠️78_

_Doit devenir un vrai tableau Markdown (une ligne par ligne, une colonne par colonne), pas un texte aplati._

### `web-epub-chapitres-notes` — ⚠️ 89 %

**Difficulté :** EPUB 3 : ordre de lecture (spine), table des matières, note de fin liée, métadonnées

- texte absent : « Note : la maison fut vendue en 1952 »

