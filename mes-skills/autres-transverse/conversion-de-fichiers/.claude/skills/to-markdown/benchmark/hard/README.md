# Batterie de documents difficiles

42 documents conçus pour **trouver les limites** de to-markdown (et des autres convertisseurs), pas pour flatter les scores. Chaque document est fabriqué pour casser une hypothèse courante : colonnes, cellules fusionnées, scans, formes libres, notes, doublons, bruit du web, encodages, fichiers abîmés…

```bash
python3 benchmark/hard/run_hard.py                         # tout, écrit HARD_RESULTS.md
python3 benchmark/hard/run_hard.py --only pdf-             # une famille (préfixe d'identifiant)
python3 benchmark/hard/run_hard.py --show pdf-article-deux-colonnes     # voir la sortie de chaque convertisseur
python3 benchmark/hard/run_hard.py --dump sorties/         # garder tous les Markdown produits pour les relire
python3 benchmark/hard/generate.py [--with-big]            # régénère le corpus (producteurs optionnels : reportlab, Pillow, xlsxwriter, python-pptx, LibreOffice)
```

Les fichiers sont versionnés dans `corpus/` (2 Mo) : inutile de les régénérer pour les utiliser. `manifest.json` décrit, pour chacun, la difficulté (1-5), ce qui le rend dur et **ce qu'on doit en retrouver**. Résultats : [`HARD_RESULTS.md`](HARD_RESULTS.md) ; chaque limite y est détaillée avec les vérifications qui échouent.

## Contenu

| Famille | Documents | Pièges |
| --- | --- | --- |
| `docx-` (6) | listes à 4 niveaux · cellules fusionnées + tableau imbriqué · notes de bas de page/de fin, commentaires, suivi des modifications · zone de texte en double, en-tête/pied · arabe/hébreu/CJK/emoji · sommaire, équation, contrôle de contenu | structure Word que seuls les moteurs fins gardent |
| `pptx-` (3) | schéma en formes libres + connecteurs · groupes, graphique, tableau fusionné, notes, diapositive masquée · diapositive qui n'est qu'une image | contenu hors des zones de texte |
| `xlsx-` (2) | titre fusionné, formats monnaie/%/date, formule, commentaire, lignes et feuilles masquées · 3 000 × 30 | valeur affichée ≠ valeur stockée, charge |
| `legacy-` (3) | .doc, .xls, .ppt (produits par LibreOffice) | formats binaires : le moteur natif est limité |
| `pdf-` (7) | deux colonnes + en-tête courant · tableau sans bordures · tableau à traits fusionné · page pivotée · scan incliné et bruité · texte/scan/texte · notes de bas de page | ordre de lecture, tableaux, OCR |
| `web-` (7) | article noyé dans le bruit · HTML tordu (tables de mise en page, details, MathML, SVG…) · e-mail multipartie avec message transféré · notebook · EPUB · SVG de processus · draw.io | extraction du « vrai » contenu |
| `data-` (14) | JSON profond · XML à espaces de noms · SQLite · 5 encodages hérités · zip imbriqué avec membre corrompu · DOCX/PDF tronqués · faux DOCX · RTF et ODT | robustesse |

## Comment un document est noté

Le manifeste liste des attentes ; chaque attente réussie ou ratée compte pour une vérification :

- `must` / `any_of` — le texte (ou une de ses variantes) est retrouvé ;
- `order` — l'ordre de lecture est respecté ;
- `absent` / `once` / `at_most` — le bruit est exclu, rien n'est dupliqué, les en-têtes courants ne sont pas répétés ;
- `headings` / `cells` / `items` / `links` / `rows` / `levels` — la structure est restituée *comme structure Markdown* (titres, tableau avec chaque ligne sur une ligne, listes dont l'indentation suit l'imbrication, liens) ;
- `expect` : `ok` (extraire le contenu), `vision` (l'extraire, **ou** le signaler « à lire visuellement » — jamais le perdre en silence), `error` (échouer proprement avec un message).

Verdict : ✅ ≥ 95 % des vérifications, ⚠️ 70-95 %, ❌ en dessous, 👁 contenu non extrait mais signalé. Les convertisseurs concurrents sont jugés sur les mêmes attentes.

## À savoir avant d'interpréter

- **Les attentes sont les miennes** : certaines sont discutables (la feuille masquée doit-elle apparaître ? un e-mail doit-il contenir la pièce jointe ?). Elles sont écrites dans `manifest.json` et dans les `notes` ; changez-les si votre besoin diffère.
- **Auteur du skill = auteur de la batterie.** La batterie a été écrite *après* le moteur et contre ses angles morts, mais gardez un œil critique ; ajoutez vos propres documents réels (`manifest.json` : un objet de plus).
- **Un ✅ ne dit pas « parfait »** : les vérifications portent sur le texte et la structure, pas sur la mise en page ni les images.
- Pour ajouter un cas : déposer le fichier dans `corpus/`, ajouter son entrée dans `manifest.json` (ou un `Case` dans `gen_*.py`), relancer `run_hard.py --only <id>`.
