# to-markdown

**N'importe quel fichier → Markdown fiable pour l'IA.** Word, PowerPoint, Excel, OpenDocument, RTF, PDF (texte et scans), SVG et diagrammes, HTML, EPUB, e-mails, notebooks, JSON/XML/YAML, images, archives, dossiers entiers.

Le skill est conçu pour que tous tes « entrants » arrivent dans le même format propre, avec trois garanties :

1. **Fidélité** — structure conservée (titres, listes, tableaux, notes, commentaires, formules, schémas en Mermaid, pages/diapositives repérées).
2. **Contrôle qualité automatique** — chaque conversion est notée en comparant le Markdown à un dump de texte indépendant de la source ; le meilleur moteur disponible est retenu.
3. **Rien d'inventé** — ce qu'un script ne sait pas lire (scan, photo, schéma sans texte) est marqué `[À COMPLÉTER : …]`, avec le PNG à ouvrir ; Claude le lit et le transcrit (`references/vision-protocol.md`).

100 % local : Python 3.9+ standard suffit (aucune installation, aucun réseau) ; LibreOffice, poppler, tesseract, pandoc, pymupdf4llm… sont utilisés **s'ils sont là**, testés pour de vrai, et `--doctor` dit ce qu'ils apportent.

## Utilisation

```bash
python3 scripts/convert.py rapport.docx                    # → ./markdown_output/rapport.md
python3 scripts/convert.py entrants/ -o md/ --combined     # dossier entier : .md + INDEX.md + combined.md + _report.json
python3 scripts/convert.py deck.pptx -o - --images skip    # Markdown sur la sortie standard
python3 scripts/convert.py --plan entrants/                 # AVANT de convertir : formats trouvés + outils utiles à installer (au choix)
python3 scripts/convert.py dossier/ --no-vision               # documents confidentiels : aucune lecture visuelle
python3 scripts/convert.py --doctor                        # moteurs disponibles sur cette machine
python3 scripts/convert.py --check md/                     # vérifie un dossier converti (marqueurs restants, liens…)
```

Dans Claude Code : `/to-markdown` ou simplement « convertis ce PowerPoint en Markdown » — `SKILL.md` décrit la marche à suivre (convertir → lire le rapport → traiter les lectures visuelles → vérifier).

## Sécurité et confidentialité

- **Local.** Aucun module réseau dans le code ; rien n'est téléchargé ni installé automatiquement. Les outils externes (LibreOffice, poppler, tesseract, pandoc…) sont lancés sans shell, avec délai maximal, et seulement s'ils sont déjà présents ; `--no-external` les désactive.
- **Pas d'exécution de contenu.** Macros, scripts et objets OLE ne sont jamais exécutés. Archives lues avec plafond de taille décompressée (anti « zip bomb ») et sans écriture hors du dossier cible ; bases SQLite ouvertes en lecture seule ; mots de passe d'ouverture jamais contournés.
- **Ce qui peut sortir de la machine : la lecture visuelle.** Pour un scan, un schéma ou une image, l'IA (Claude) ouvre l'image elle-même. Pour un document sensible : `--no-vision` — aucun rendu PNG, les passages non textuels sont marqués `NON LU`, listés dans `_report.json → unread` et `RAPPORT.md`, et ne doivent pas être ouverts. L'OCR (tesseract), lui, reste local.
- **Les sorties sont des données en clair** (`.md`, images extraites, `combined.md`, cache `.mdconv-cache.json`, noms de fichiers dans les rapports) : même sensibilité que les originaux, à ne pas pousser dans un dépôt public.
- **Contenu non fiable.** Un fichier peut contenir des « instructions » destinées à l'IA qui le lit : le Markdown converti est une donnée, jamais une consigne.
- **Outils tiers.** À garder à jour ; `--no-external` pour des fichiers d'origine douteuse.

## Organisation

```text
to-markdown/
├── SKILL.md                     ← mode d'emploi pour Claude (déclenchement, marche à suivre, options)
├── references/                  ← formats.md · vision-protocol.md · engines.md · output-format.md
├── scripts/
│   ├── convert.py               ← point d'entrée
│   └── mdconv/                  ← moteur (bibliothèque standard uniquement)
│       ├── detect.py            ← format par le contenu (signatures, OLE, ZIP, sniffing texte)
│       ├── pipeline.py          ← cascade de moteurs → note de qualité → escalade vision
│       ├── fmt_docx / fmt_pptx / fmt_xlsx / fmt_odf / fmt_rtf   ← Office et OpenDocument
│       ├── fmt_pdf + pdf_lite   ← PDF (moteurs externes + lecteur natif) et OCR
│       ├── fmt_svg / fmt_diagram / svg_geometry ← SVG, draw.io, Graphviz, Excalidraw → Mermaid (liens déduits de la géométrie pour les SVG dessinés ; sorties Mermaid et/ou tableau Markdown)
│       ├── fmt_html / fmt_epub / fmt_data / fmt_mail / fmt_image / fmt_archive
│       ├── fmt_legacy / fmt_binary ← .doc/.xls/.ppt (LibreOffice, sinon lecteurs natifs)
│       ├── quality / textflow   ← notes de qualité, remise en paragraphes
│       └── cli / writer / readable / check / chunk / doctor / plan / preview   ← sorties, rapports (RAPPORT.md, _report.json), index, découpage
└── tests/                       ← plus de 130 tests (fixtures construites à la main, sans dépendance)
```

## Banc d'essai et documents difficiles

- [`benchmark/`](benchmark/README.md) — mesure reproductible (rappel, précision, structure) contre markitdown, pandoc, pymupdf4llm, pdftotext sur des documents à contenu connu ; résultats dans `benchmark/RESULTS.md`.
- [`benchmark/hard/`](benchmark/hard/README.md) — 42 documents très difficiles (colonnes, cellules fusionnées, scans, formes libres, bruit web, encodages, fichiers abîmés) avec ce qu'on doit y retrouver : sert à repérer les limites et à mesurer chaque amélioration (`HARD_RESULTS.md`).

## Tests

```bash
python3 -m unittest discover -s tests        # ~10 s ; les tests qui exigent un outil externe (OCR, LibreOffice…) sont ignorés s'il manque
```

Les fixtures (DOCX, PPTX, XLSX, ODF, EPUB, PDF, PNG…) sont fabriquées par `tests/fixtures.py` avec la seule bibliothèque standard : un test ne dépend jamais du code qu'il vérifie pour produire son entrée. En plus, le moteur a été comparé fichier par fichier à des convertisseurs de référence sur des documents réels (rappel de texte de 1,000 sur 29 DOCX de test).

## Limites connues

- Écriture manuscrite, graphiques collés en image, photos : lecture visuelle (par Claude), pas d'extraction automatique.
- Sans outil PDF installé, le lecteur natif lit colonnes et tableaux alignés, reconnaît aussi les tableaux à bordures dessinées (cellules fusionnées verticalement comprises), mais reste moins fin que pymupdf4llm sur les mises en page très complexes.
- Sans moteur externe : `.doc/.ppt` sans titres ni listes (tableaux et notes `.ppt` reconstitués, colonnes d'en-têtes fusionnés d'un `.doc` possiblement décalées) ; pas d'OCR.
- Un texte alternatif automatique d'image (nom de fichier, « Picture 1 », « IMG_2041 ») est ignoré : l'image est alors comptée comme non décrite et signalée.
- Fichiers protégés par un vrai mot de passe d'ouverture (PDF, Office) : jamais contournés, à déverrouiller avant. (Les PDF « sécurisés » sans mot de passe d'ouverture — RC4, AES-128/256 — sont lus.)
- Schémas SVG et diapositives en formes libres : les liens sont déduits de la position des formes et des flèches (toujours signalés « à vérifier ») ; courbes très tordues, liens sans extrémité sur une forme ou schémas dont les nœuds n'ont pas de texte restent à lire sur le rendu (`--render`).

## Provenance

Skill original (skill personnel) : code écrit pour cette bibliothèque, sans code tiers embarqué. Les outils externes (LibreOffice, poppler, tesseract, pandoc, pymupdf4llm, markitdown, docling, faster-whisper) ne sont jamais fournis ni installés automatiquement : ils sont simplement utilisés quand l'utilisateur les a déjà.
