# Formats pris en charge — ce qui est extrait, avec quel moteur, et les limites

Le format est identifié par le **contenu** du fichier (signature, structure interne), pas par l'extension : un `.doc` qui est en réalité du HTML, un `.docx` renommé en `.zip` ou un PDF sans extension sont reconnus (avertissement « l'extension ne correspond pas au contenu »).

Légende des moteurs : **natif** = Python standard, toujours disponible ; *(ext.)* = outil optionnel, utilisé s'il est installé et **testé pour de vrai** (`--doctor`). L'outil essaie les moteurs par priorité croissante et s'arrête au premier dont la note de qualité est ≥ 0,90.

## Tableau récapitulatif

| Famille | Extensions | Moteurs (par priorité) |
|---|---|---|
| Word | `.docx .docm .dotx` | natif · pandoc *(ext.)* · markitdown *(ext.)* |
| Word ancien | `.doc` `.wps` | LibreOffice *(ext.)* → lecteur natif « texte fidèle » |
| PowerPoint | `.pptx .pptm .ppsx .potx` | natif · markitdown *(ext.)* |
| PowerPoint ancien | `.ppt .pps` | LibreOffice *(ext.)* → lecteur natif |
| Excel | `.xlsx .xlsm` | natif (lecture en flux) · markitdown *(ext.)* |
| Excel ancien | `.xls` · `.xlsb` | LibreOffice *(ext.)* → lecteur natif BIFF8 (`.xls`) ; `.xlsb` : LibreOffice seulement |
| OpenDocument | `.odt .odp .ods` | natif · LibreOffice *(ext.)* · pandoc *(ext.)* |
| RTF | `.rtf` | natif · LibreOffice *(ext.)* · pandoc *(ext.)* |
| PDF | `.pdf` | pymupdf4llm *(ext.)* · docling *(ext.)* · pdftotext *(ext.)* · pdfplumber *(ext.)* · markitdown · pypdfium2 · pypdf · **lecteur natif** |
| SVG | `.svg .svgz` | natif |
| Diagrammes | `.drawio .excalidraw`, SVG Graphviz/Mermaid/draw.io | natif → bloc `mermaid` |
| HTML | `.html .htm .xhtml` (et faux `.xls/.doc` HTML) | natif · markitdown · pandoc |
| E-books | `.epub` | natif · pandoc |
| Tableaux de données | `.csv .tsv` | natif |
| Données structurées | `.json .jsonl .yaml .xml` (RSS/Atom) | natif |
| Notebooks | `.ipynb` | natif · pandoc |
| Texte, Markdown, code | `.txt .md .log` et une soixantaine de langages (`.py .js .sql .sh …`) | natif |
| Balisage | `.tex .rst .org .adoc .textile …` | pandoc *(ext.)* → natif (texte brut balisé) |
| E-mails | `.eml .mbox .mhtml .msg` | natif |
| Images | `.png .jpg .gif .webp .bmp .tiff …` | natif : métadonnées + OCR *(tesseract, ext.)* + lecture visuelle |
| Archives | `.zip .tar .tgz .gz .bz2 .xz` | ouverture sûre, puis chaque membre converti |
| Audio / vidéo | `.mp3 .wav .mp4 …` | **sur demande** : `--engines whisper` (faster-whisper) |

Non convertibles (message explicite + piste) : Apple iWork (exporter en PDF/DOCX), Sketch, Publisher, Visio binaire, XPS, SQLite/Parquet (exporter en CSV), fichiers Office chiffrés (retirer le mot de passe), binaires inconnus.

## Détail par famille

### Word (`.docx`)
**Extrait** : titres (styles, niveaux de plan, numérotation ; **déduits de la taille/graisse** quand le document n'a aucun style de titre, désactivable par `--no-infer-headings`), listes à puces/numérotées/lettrées multi-niveaux, tableaux (cellules fusionnées horizontalement et verticalement aplaties, en-têtes à deux niveaux fusionnés, tableau d'une seule cellule → citation), gras/italique/barré/code, exposants/indices (Unicode pour les exposants courts, `<sup>` sinon ; « 1er » reste en clair), liens (y compris champs `HYPERLINK`), notes de bas de page et de fin `[^1]`, **commentaires** en notes `[^c1]` avec auteur, date, texte commenté et réponses, **modifications suivies** (acceptées, ou `<ins>`/`<del>` avec `--track-changes mark`), images (texte alternatif conservé), graphiques (données en tableau), SmartArt (listes imbriquées), zones de texte (sans doublon), équations OMML → LaTeX (`$…$`, `$$…$$`), contrôles de contenu, cases à cocher, table des matières retirée (sauf `--keep-toc`), en-têtes/pieds de page (avec `--headers-footers`).
**Limites** : mise en page (colonnes, positionnement flottant) aplatie ; dessins vectoriels sans texte non décrits (utiliser `--render` pour les voir) ; objets OLE incorporés non extraits.

### PowerPoint (`.pptx`)
**Extrait** : une section `## Slide N — titre` par diapositive **dans l'ordre réel du diaporama** (pas celui des fichiers), sections du diaporama en `##` (les diapositives passent alors en `###`), ordre de lecture reconstitué d'après la géométrie (titre d'abord), puces hiérarchisées, tableaux, graphiques (données), SmartArt, groupes de formes, **connecteurs → diagramme `mermaid`**, images avec texte alternatif, **notes du présentateur**, commentaires, diapositives masquées signalées (`--no-hidden` pour les ignorer). Diapositive faite d'images sans texte → marquée pour lecture visuelle.
**Limites** : flèches ou schémas dessinés en formes libres sans connecteurs, animations, vidéos et audio incorporés non restitués — `--render` produit un PNG par diapositive pour vérifier (les diapositives masquées n'y figurent pas).

### Excel (`.xlsx`)
**Extrait** : une section `## <feuille>` par feuille, les blocs séparés par des lignes vides deviennent des tableaux distincts (un titre seul au-dessus d'un tableau reste un titre), types lisibles (dates ISO, pourcentages, booléens, nombres sans bruit flottant `0.30000000000000004` → `0.3`), cellules fusionnées répétées, liens, commentaires (classiques et fils de discussion), graphiques et zones de texte des dessins, feuilles masquées signalées. Formule sans valeur en cache (classeur jamais recalculé) → la formule est affichée et signalée ; `--formulas` ajoute toujours les formules.
**Limites** : mise en forme conditionnelle, couleurs et validations de données non restituées ; grandes feuilles **tronquées à 1000 lignes** dans le Markdown (`--table-rows`) avec un CSV complet `<feuille>.csv` dans le dossier d'assets ; TCD lus comme des cellules ordinaires (valeurs en cache).

### Anciens formats Office (`.doc .ppt .xls .xlsb .wps`)
Avec **LibreOffice** : conversion vers OOXML (un seul lancement pour tout un lot) puis convertisseurs natifs → fidélité complète. Sans lui : lecteurs natifs volontairement « texte fidèle » — `.doc` : texte complet mais titres et listes perdus ; `.xls` (BIFF8) : valeurs de cellules et feuilles ; `.ppt` : texte des diapositives (sans notes ni images). `--doctor` indique quelle situation s'applique.

### OpenDocument et RTF
`.odt/.odp/.ods` : mêmes fidélités que leurs équivalents OOXML (titres, listes fusionnées, tableaux, notes de bas de page, objets graphiques et formules incorporés, connecteurs). RTF : texte, gras/italique, titres (styles), listes, tableaux, liens (champs imbriqués compris), images PNG/JPEG, notes, caractères Unicode et pages de codes.

### PDF
Un marqueur `<!-- page N -->` précède chaque page (`<!-- page N (OCR 87 %) -->` pour une page lue par OCR). Le moteur choisi dépend de ce qui est installé (`--doctor`) :
- **pymupdf4llm** : Markdown structuré (titres, tableaux, colonnes, images) — le meilleur choix si le PDF compte ;
- **pdftotext (poppler)** : texte fiable, ordre de lecture correct sur plusieurs colonnes, très rapide ;
- **pdfplumber** : tableaux (à demander : `--engines pdfplumber`) ;
- **lecteur natif** (aucune installation) : objets et flux compressés, polices avec table Unicode, colonnes, paragraphes d'après l'espacement, titres d'après la taille de police et le gras, en-têtes/pieds de page répétés retirés.
Avec les moteurs « texte » (pdftotext, pdfplumber, pypdfium2, pypdf, natif) : numéros de page et en-têtes/pieds répétés retirés — jamais plus de la moitié d'une page, et « Chapitre 3 » n'est pas pris pour un en-tête. Pages sans texte → **OCR** (tesseract, 200 dpi) sinon lecture visuelle (PNG de la page fourni quand un outil de rendu existe).
**Limites** : PDF chiffrés (avec ou sans mot de passe utilisateur) → refusés par le lecteur natif, poppler/pymupdf les ouvrent si le mot de passe utilisateur est vide ; tableaux sans bordures aplatis par les moteurs texte ; formules mathématiques et manuscrits → lecture visuelle ; polices sans table Unicode (`(cid:12)`) → caractères signalés, essayer un autre moteur.

### SVG et diagrammes
Un SVG est du XML : le texte est **entièrement** récupérable, dans l'ordre de lecture (positions et transformations appliquées ; texte masqué ignoré ; `foreignObject` et `switch` gérés). Détection de structure : Graphviz, draw.io (fichiers `.drawio`, compressés inclus, et SVG exportés), Excalidraw, Mermaid → nœuds et liens en `flowchart` Mermaid (groupes/clusters reconstitués). Petit SVG (icône, logo) : source simplifiée ≤ 8 Ko incluse ; SVG sans texte ni structure → **lecture visuelle** avec rendu PNG (rsvg-convert, Inkscape, cairosvg, ImageMagick, Chrome ou LibreOffice — le premier disponible). Courbes matplotlib (texte en chemins) : texte relu dans les commentaires du fichier.

### HTML, EPUB
Titres, listes imbriquées, tableaux (tableaux de mise en page aplatis, cellules avec listes/retours à la ligne), code avec langage, citations, liens, images (data-URI extraites), maths KaTeX/MathJax. **Contenu principal** sélectionné et bruit retiré (menus, cookies, pieds de page) — `--html-mode full` garde tout. Encodage lu depuis `<meta charset>`. EPUB : chapitres dans l'ordre du *spine*, titre du livre en `#` et chapitres en `##`, images extraites.

### Données et texte
- **CSV/TSV** : séparateur et encodage devinés (UTF-8, cp1252, cp1251, CJK…), guillemets et retours à la ligne dans les cellules, tableau + **schéma des colonnes** (type, non-vides, aperçu) ; plafonné à `--table-rows`.
- **JSON/JSONL** : liste d'objets → tableau (colonnes imbriquées aplaties `a.b`) ; sinon bloc `json` borné. **YAML/XML** : bloc de code (XML : résumé de la racine, des balises et de la profondeur). **Notebooks** : cellules Markdown telles quelles, code en blocs, sorties texte et images extraites.
- **Markdown/texte/code** : recopiés (en-tête YAML d'un `.md` mis en bloc de code), langage détecté pour le code.
- Encodages : UTF-8/16/32, cp1252, cp1250, cp1254, cyrillique (cp1251, KOI8-R), grec, hébreu, arabe, japonais, chinois, coréen — devinés sans dépendance.

### E-mails
`.eml/.mbox/.mhtml/.msg` : objet en titre, de/à/cc/date, corps (texte ou HTML converti), **pièces jointes extraites puis converties à leur tour** (`<nom>_attachments/`), liens depuis le mail.

### Images
Dimensions, format, métadonnées (EXIF, texte PNG) ; **OCR** si tesseract est installé (`--ocr-lang fra+eng` pour forcer les langues) ; une image sans texte reconnu ou à faible confiance est marquée pour lecture visuelle. Une image n'est jamais « décrite » par le script : c'est ton travail (`vision-protocol.md`).

## Sécurité (toutes familles)
XML : entités externes et déclarations d'entités refusées. ZIP/OOXML/ODF/EPUB : plafonds de taille décompressée, de nombre de membres et de ratio (zip bombs), chemins normalisés (aucune écriture hors du dossier de sortie). Macros VBA : jamais exécutées, signalées. Aucun accès réseau : les images distantes d'un HTML restent des liens, jamais téléchargées.
