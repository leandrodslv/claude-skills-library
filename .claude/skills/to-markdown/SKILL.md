---
name: to-markdown
description: Convertit n'importe quel fichier en Markdown propre et fidèle pour le faire lire à l'IA — Word (.docx/.doc), PowerPoint (.pptx/.ppt), Excel (.xlsx/.xls/.csv), OpenDocument, RTF, PDF (texte ou scanné, OCR), SVG et diagrammes (draw.io, Visio, Graphviz, Mermaid), HTML, EPUB, e-mails (.eml/.msg), notebooks Jupyter, JSON/XML/YAML, bases SQLite, images, archives ZIP/TAR et dossiers entiers. À utiliser dès que l'utilisateur veut convertir, transformer, lire, résumer, analyser, comparer ou indexer un ou plusieurs fichiers non textuels (« mes entrants », « ce ppt/word/pdf/svg en markdown », « convert to markdown », « rends ça lisible par l'IA », préparation RAG) — même si le mot Markdown n'est pas prononcé. Contrôle qualité automatique, lecture visuelle guidée des scans/schémas, 100 % local.
---

# to-markdown — n'importe quel fichier → Markdown fiable

Un seul outil (`scripts/convert.py`, Python 3.9+ standard, sans installation) pour transformer les « entrants » de l'utilisateur en Markdown que l'IA lit sans perte : titres, listes, **tableaux**, liens, notes, commentaires, images (avec texte alternatif), formules, schémas (→ Mermaid), pages et diapositives repérées. Chaque conversion est **notée automatiquement** (quels mots de la source manquent ?) et ce qu'aucun script ne sait lire — scans, photos, illustrations — est **marqué explicitement** pour que tu le lises à l'œil (vision) au lieu de l'ignorer ou de l'inventer.

Tout se passe en local : aucun envoi de données, aucun accès réseau, macros jamais exécutées.

## Quand l'utiliser

- Un fichier, un dossier ou une archive à lire, résumer, analyser, comparer, extraire, indexer… et le format n'est pas du texte brut : `.docx .pptx .xlsx .pdf .svg .html .epub .eml .msg .odt .rtf .ipynb .png …`
- « Convertis / transforme / mets en Markdown », « mes entrants », « prépare ces documents pour l'IA / pour un RAG ».
- Un autre skill ou une autre étape a besoin du contenu d'un document binaire.

Ne pas l'utiliser pour : un fichier déjà en `.md`/`.txt`/code (le lire directement) ; une page web par URL (WebFetch ou le skill `read`) ; **créer ou modifier** un `.docx/.pptx/.xlsx` (c'est l'autre sens). Un seul PDF court ou une seule image à consulter ponctuellement : l'outil Read suffit — to-markdown apporte de la valeur dès qu'il y a de l'Office, plusieurs fichiers, un dossier, un texte à garder, des tableaux à ne pas déformer, un PDF long ou scanné.

## Démarrage rapide

`convert.py` = `scripts/convert.py` **dans le dossier de ce skill** (`.claude/skills/to-markdown/` dans un projet, `~/.claude/skills/to-markdown/` en global ; le chemin de base est indiqué quand le skill est chargé).

```bash
python3 <skill>/scripts/convert.py rapport.docx                    # → ./markdown_output/rapport.md
python3 <skill>/scripts/convert.py entrants/ -o md/ --combined     # dossier entier : 1 .md par fichier + INDEX.md + combined.md
python3 <skill>/scripts/convert.py deck.pptx -o - --images skip    # Markdown sur la sortie standard
python3 <skill>/scripts/convert.py --doctor                        # ce que cette machine sait faire, et comment aller plus loin
python3 <skill>/scripts/convert.py --check md/                     # vérifie un dossier converti
```

Relancer est sans risque : les fichiers inchangés sont ignorés (cache incrémental, `--force` pour tout refaire), et un dossier de sortie placé dans le dossier d'entrée n'est pas reconverti. **Boîte d'entrée permanente** : `convert.py entrants/ -o entrants_md/` à chaque arrivée de nouveaux fichiers — seuls les nouveaux ou modifiés sont convertis.

## Marche à suivre

1. **Repérer les entrants.** `ls` du dossier ou du fichier ; ne devine rien sur le contenu. Choisis un dossier de sortie explicite (`-o md/` à côté des sources, ou celui que l'utilisateur demande) pour ne pas laisser de `markdown_output/` traîner.
2. **Convertir** avec la commande ci-dessus. Première utilisation sur une machine, ou résultat décevant (`.doc/.ppt` anciens, PDF complexes, scans) : lance d'abord `--doctor` — il dit quels moteurs optionnels (LibreOffice, poppler, tesseract, pandoc, pymupdf4llm…) sont présents et quoi installer pour gagner en fidélité.
3. **Lire le résumé** affiché en fin de commande (stderr) : nombre de fichiers par statut, éléments à lire visuellement, avertissements. Détail par fichier dans `md/_report.json` (statut, moteur, note de qualité, mots, avertissements, `vision_needed`). Statuts :

   | Statut | Sens | Que faire |
   |---|---|---|
   | `ok` | converti, qualité ≥ 0,90 | rien |
   | `unchanged` | source inchangée depuis le dernier passage | rien |
   | `warn` | converti mais un contrôle a sonné (texte manquant, densité faible…) | lire l'avertissement ; essayer `--compare` ou un autre moteur (`references/engines.md`) |
   | `needs_vision` | du contenu est visuel (scan, image, schéma sans texte) | **étape 4** |
   | `unsupported` / `error` | format non géré, fichier chiffré/corrompu | lire le message : il propose une piste (exporter en PDF, retirer le mot de passe…) |

4. **Traiter la lecture visuelle** (`needs_vision`, ou tout marqueur `> **[À COMPLÉTER : …]**` dans un `.md`). Pour chaque entrée de `vision_needed` du rapport : ouvre `path` avec l'outil Read (PNG d'une page/d'une image, ou PDF avec les pages indiquées), **décris ce que tu vois**, puis remplace le marqueur par ta transcription avec Edit. Suis `references/vision-protocol.md` (gabarits par type : scan, graphique → tableau de données, schéma → Mermaid, capture d'écran, photo) ; règle absolue : **ne rien inventer**, écrire `[illisible]` plutôt que deviner un chiffre ou un nom. Pour vérifier un diaporama chargé en schémas ou une mise en page complexe, ajoute `--render` : un PNG par page/diapositive est écrit dans le dossier d'assets (non inséré dans le Markdown).
5. **Vérifier** : `convert.py --check md/` doit répondre « aucun problème détecté » (plus de marqueur `[À COMPLÉTER`, liens et images valides, pas de caractères illisibles, Markdown bien formé).
6. **Livrer** : indique où sont les `.md` (et `INDEX.md`), ce qui a été converti, ce qui a demandé une lecture visuelle et ce qui reste limité. N'affiche pas des milliers de lignes de Markdown : ouvre seulement les fichiers utiles à la demande.

## Ce que tu peux attendre (et ne pas attendre)

- **Structure conservée** : niveaux de titres (y compris déduits de la mise en forme quand le document n'utilise pas de styles), listes imbriquées, tableaux (cellules fusionnées aplaties, en-têtes à deux niveaux fusionnés), liens, notes de bas de page `[^1]`, commentaires en notes `[^c1]`, notes du présentateur, texte des zones de texte, formules en LaTeX, graphiques Excel/PowerPoint en tableaux de données, SmartArt en listes, connecteurs PowerPoint/draw.io/Graphviz/SVG en `mermaid`.
- **Repères** : `<!-- page N -->` pour les PDF, `## Slide N — titre` pour les présentations, `## <nom de la feuille>` pour les classeurs ; contenu masqué signalé (`*(masquée)*`), jamais perdu en silence.
- **Images** extraites dans `<nom>_assets/` avec leur texte alternatif quand il existe ; scans et images standalone passés à l'OCR (tesseract) s'il est installé, sinon marqués pour lecture visuelle.
- **Tableaux volumineux** : plafond de 1000 lignes par tableau (`--table-rows`), avec le fichier complet en CSV à côté — dit explicitement dans le Markdown.
- **Pas magique** : sans outil PDF installé, les PDF à colonnes ou à tableaux complexes sont moins fins qu'avec pymupdf4llm ; PDF très mis en page (colonnes multiples, tableaux sans bordures) → le lecteur natif est correct mais moins fin que pymupdf4llm/pdfplumber (à installer si le PDF compte) ; écriture manuscrite → lecture visuelle ; fichiers chiffrés → l'utilisateur doit retirer le mot de passe. Voir `references/formats.md` pour le détail par format.

## Options utiles

| Besoin | Option |
|---|---|
| Dossier de sortie / sortie standard | `-o md/` · `-o -` (un seul fichier) · `--in-place` (à côté des sources) |
| Tout dans un seul fichier | `--combined` (garde aussi les .md) · `--only-combined` |
| Découper pour un RAG / un contexte limité | `--chunk-tokens 2000` → `<nom>_chunks/part-01.md…` (coupe aux titres, sans casser tableaux ni code) |
| En-tête YAML (source, format, mots, jetons, qualité) | `--frontmatter min` (défaut) · `full` (+ sha256, dates, auteur) · `none` |
| Sans images / sans commentaires / sans notes | `--images skip` · `--no-comments` · `--no-notes` |
| Word : suivi des modifications | `--track-changes accept` (défaut) · `mark` (`<ins>`/`<del>`) ; `--keep-toc`, `--headers-footers` |
| Excel : formules, feuilles masquées, lignes | `--formulas` · `--no-hidden` · `--table-rows 0` (illimité) |
| HTML : page entière ou contenu principal | `--html-mode full` · `main` · `auto` (défaut) |
| OCR (PDF scannés, images) | `--ocr auto` (défaut) · `off` · `force` ; `--ocr-lang fra+eng` |
| Comparer les moteurs | `--compare` (essaie tous les moteurs et affiche le score de chacun) · `--engines native,pandoc` |
| Aperçus PNG pour vérifier à l'œil | `--render` |
| Lots | `-j 4` (processus), `--include '*.pdf'`, `--exclude 'brouillons/*'`, `--force`, `--json` |

## Cas particuliers

- **PDF scannés** : tesseract fait l'OCR page par page (confiance moyenne signalée) ; si aucun OCR n'est installé ou si la confiance est basse, les pages sont marquées `[À COMPLÉTER : lecture visuelle]` avec un PNG à ouvrir. Vérifie toujours chiffres et noms propres d'un texte OCR.
- **Fichiers `.doc/.xls/.ppt/.xlsb/.wps`** : lecteurs natifs de secours, mais **LibreOffice** (un seul lancement pour tout le lot) donne un meilleur rendu s'il est installé — `--doctor` le dit.
- **E-mails** : en-têtes, corps, et chaque pièce jointe convertie à son tour (lien depuis le mail). `.msg` Outlook lu nativement.
- **Archives** : `.zip/.tar/.gz…` ouvertes (protection contre les chemins piégés et les zip bombs) ; chaque membre est converti, les sorties gardent l'arborescence.
- **Audio / vidéo** : transcription seulement sur demande explicite (`--engines whisper`, nécessite `faster-whisper`) ; sinon ignorés avec un message.
- **Macros** (`.docm`, `.xlsm`) : jamais exécutées, signalées. **Fichiers protégés par un vrai mot de passe d'ouverture** : refusés avec le message qui explique quoi faire (jamais contournés) ; les PDF « sécurisés » sans mot de passe d'ouverture sont lus normalement.
- **Fichier volumineux** : au-delà de 500 Mo (`--max-size-mb`) le fichier est refusé ; les classeurs Excel sont lus en flux (mémoire bornée) et les longs tableaux tronqués avec un CSV complet à côté.

## Si quelque chose cloche

1. `--doctor` : moteurs présents/absents et commandes d'installation.
2. `--compare` sur le fichier fautif : score et nombre de mots par moteur ; l'outil garde déjà le meilleur, mais on voit pourquoi.
3. `-v` : trace détaillée des tentatives de chaque moteur.
4. `references/engines.md` : installer un moteur, forcer un ordre (`--engines`), lire les notes de qualité.
5. Bug ou format non géré : dis-le franchement à l'utilisateur, propose l'export depuis l'application d'origine (PDF, DOCX, CSV) et ne fabrique pas de contenu.

## Références (à ouvrir seulement si besoin)

- `references/formats.md` — matrice des formats : ce qui est extrait, moteurs, limites connues.
- `references/vision-protocol.md` — comment décrire scans, graphiques, schémas, captures, photos ; gabarits et règles d'intégrité.
- `references/engines.md` — moteurs, ordre de priorité, notes de qualité, installation, `--compare`, dépannage.
- `references/output-format.md` — arborescence de sortie, en-tête YAML, `_report.json`, `INDEX.md`, découpage, codes de retour.
