# Moteurs, qualité et dépannage

## Comment l'outil choisit

Pour chaque fichier : détection du format par le contenu → moteurs disponibles essayés **par priorité croissante** → chaque résultat est **noté** → arrêt au premier moteur dont la note atteint **0,90** (`--threshold`) → sinon le meilleur des essais est retenu et le statut passe à `warn`. Un moteur qui plante ou dit « non pris en charge » est simplement sauté : un échec ne fait jamais tomber un lot.

| Format | Ordre des moteurs (priorité) |
|---|---|
| `docx` | natif (10) · pandoc (45) · markitdown (50) |
| `pptx`, `xlsx` | natif (10) · markitdown (50) |
| `odt/odp/ods` | natif (10) · LibreOffice (40) · pandoc (45, odt) · markitdown (50, odt) |
| `rtf` | natif (10) · LibreOffice (40) · pandoc (45) · markitdown (50) |
| `doc`, `ppt`, `xls` | **LibreOffice (5)** · natif « texte fidèle » (20) · markitdown (50) |
| `xlsb`, `wps`, iWork | LibreOffice (5) |
| `pdf` | pymupdf4llm (10) · docling (12) · pdftotext (20) · pdfplumber (25) · markitdown (30) · pypdfium2 (35) · pypdf (40) · natif (60) |
| `html` | natif (10) · markitdown (50) · pandoc (60) |
| `epub`, `ipynb` | natif (10) · pandoc (45) · markitdown (50) |
| `markup` (LaTeX, reST, Org…) | pandoc (10) · natif (90, texte balisé) |
| `svg`, `drawio`, `excalidraw`, `csv`, `json`, `yaml`, `xml`, `eml`, `msg`, `md`, `txt`, code, images | natif (+ markitdown en second avis pour csv/json/xml/msg) |
| audio, vidéo | faster-whisper (50) **uniquement** avec `--engines whisper` |

- `--engines native,pandoc` impose l'ordre (et n'essaie que ces moteurs) ; `--no-external` = noyau natif seul (résultats identiques d'une machine à l'autre, utile pour comparer ou reproduire).
- `--compare` essaie **tous** les moteurs disponibles et affiche pour chacun statut, note, nombre de mots, durée — le meilleur est gardé. À utiliser quand un fichier important « semble mal converti » : on voit tout de suite si un autre moteur fait mieux.
- Un moteur externe n'est proposé que s'il a été **testé pour de vrai** (ex. LibreOffice : conversion d'un mini-fichier par module Writer/Calc/Impress) — un LibreOffice « installé mais sans module Writer » est détecté et ignoré, avec l'indication de ce qu'il faut installer.

## La note de qualité (0 à 1)

Elle ne fait jamais confiance au moteur : elle compare le Markdown à un **dump de texte indépendant** de la source.

| Signal | Effet | Message dans le rapport |
|---|---|---|
| Rappel de mots (part des mots de la source retrouvés dans le Markdown ; balisage, exposants Unicode et CJK normalisés) | la note **est** le rappel | « rappel de texte 87,3 % » (signalé sous 97 %) |
| Texte dupliqué (Markdown ≫ source) | −0,10 | « texte probablement dupliqué » |
| Caractères de remplacement `�`, `(cid:12)`, mojibake (`Ã©`) | jusqu'à −0,6 | « N caractère(s) illisible(s) ou mal décodé(s) » |
| PDF : mots par page (< 6 : scan probable ; < 20 : peu de texte) | plafond 0,35 / 0,75 | « très peu de texte par page… document probablement scanné » |
| Unités attendues absentes (pages, diapositives, feuilles) | −0,05 par unité manquante (max −0,3) | « 8/10 pages retrouvées » |

Autres avertissements (informatifs, sans effet sur la note) : diapositives/feuilles masquées incluses ou ignorées ; images décoratives ignorées ; « N image(s) sans texte alternatif » (à ouvrir si leur contenu compte) ; « bruit de page retiré » (HTML) ; « l'extension .x ne correspond pas au contenu réel » ; macros présentes (jamais exécutées) ; OCR utilisé (confiance moyenne) ; « structure Markdown : … » (bloc de code non fermé, tableau aux lignes de largeurs différentes).

`needs_vision` prime sur `warn` : dès qu'un élément demande une lecture visuelle, le statut le dit.

## Installer des moteurs (rien n'est jamais installé automatiquement)

`convert.py --doctor` teste chaque outil pour de vrai et affiche les commandes adaptées. Repères :

| Apporte | Debian/Ubuntu | macOS | Windows / pip |
|---|---|---|---|
| **LibreOffice** : `.doc/.ppt/.xls/.xlsb/.wps` complets, aperçus `--render` des documents Office | `apt install libreoffice-writer libreoffice-calc libreoffice-impress` | `brew install --cask libreoffice` | `winget install LibreOffice` |
| **poppler** (`pdftotext`, `pdftoppm`) : PDF fiables et rapides, rendu des pages pour l'OCR et la lecture visuelle | `apt install poppler-utils` | `brew install poppler` | `choco install poppler` |
| **tesseract** : OCR des PDF scannés et des images | `apt install tesseract-ocr tesseract-ocr-fra` | `brew install tesseract tesseract-lang` | `choco install tesseract` |
| **pandoc** : LaTeX, reST, Org, second avis Word/EPUB/ODT | `apt install pandoc` | `brew install pandoc` | `winget install JohnMacFarlane.Pandoc` |
| **pymupdf4llm** : PDF → Markdown structuré (titres, tableaux, colonnes) | — | — | `pip install pymupdf4llm` |
| pdfplumber : PDF à tableaux (`--engines pdfplumber`) | — | — | `pip install pdfplumber` |
| docling : mise en page PDF par apprentissage (lourd, télécharge ses modèles au premier usage) | — | — | `pip install docling` |
| markitdown : second avis sur beaucoup de formats | — | — | `pip install 'markitdown[all]'` |
| rendu SVG → PNG | `apt install librsvg2-bin` | `brew install librsvg` | Inkscape, `pip install cairosvg`, ou Chrome |
| faster-whisper : transcription audio/vidéo (**télécharge un modèle au premier usage** — seul cas d'accès réseau, jamais sans `--engines whisper`) | — | — | `pip install faster-whisper` |

Langues OCR : `tesseract --list-langs` ; le français demande le paquet `tesseract-ocr-fra`. L'outil choisit tout seul parmi les langues installées (`--ocr-lang fra+eng` pour forcer).

## Performance

- **Parallèle** : `-j N` processus (défaut : auto, jusqu'à 8, dès 4 fichiers). Tout le lot legacy `.doc/.xls/.ppt` part en **un seul** lancement de LibreOffice (le démarrage domine le coût).
- **Incrémental** : `.mdconv-cache.json` dans le dossier de sortie ; un fichier inchangé (taille, date, empreinte) et converti avec les mêmes options est ignoré (`--force` pour refaire).
- **Mémoire bornée** : Excel lu en flux, plafonds sur les archives et les flux compressés, `--max-size-mb` (500), `--timeout` par outil externe (180 s).
- Ordres de grandeur sur du DOCX/PPTX/XLSX réels : quelques dizaines de millisecondes à quelques secondes par fichier avec le noyau natif ; un lot de 84 fichiers mélangés (Office, PDF, SVG, HTML, images avec OCR…) en une dizaine de secondes.

## Dépannage

| Symptôme | Cause probable / remède |
|---|---|
| « `--doctor` dit LibreOffice ✗ alors qu'il est installé » | Le paquet de base sans module (`libreoffice-core`) : installer `libreoffice-writer/calc/impress`. Le test fonctionnel détecte ce cas. |
| `.doc/.ppt` : titres et listes absents | Lecteur natif de secours : installer LibreOffice (voir ci-dessus). |
| PDF : `(cid:12)`, `�`, texte incohérent | Police sans table Unicode : essayer `--engines pdftotext`, `pymupdf4llm`, ou `--ocr force` (relit toutes les pages par OCR). |
| PDF : colonnes mélangées, tableau aplati | `--compare` ; installer `pymupdf4llm` ; sinon `--engines pdfplumber` pour les tableaux. |
| PDF scanné sans OCR | Installer tesseract (+ langue) ; sinon lecture visuelle guidée (`vision-protocol.md`). |
| Page OCR avec fautes de chiffres | Normal sous 90 % de confiance : compare avec l'image (`--render`). |
| « fichier protégé par mot de passe » | Office/PDF chiffré : demander à l'utilisateur de retirer le mot de passe (ou d'exporter un PDF non protégé). |
| Fichier `.xls`/`.doc` qui est en fait du HTML | Détecté par le contenu et converti comme HTML (avertissement d'extension). |
| Texte accentué déformé dans un `.txt/.csv` ancien | Encodage deviné (cp1252, cp1251, cp1250, CJK…) ; forcer n'est pas nécessaire pour les cas courants — signaler l'exemple si erreur. |
| Sortie trop volumineuse pour le contexte | `--chunk-tokens 2000` ; lire `INDEX.md`, puis seulement les fichiers utiles. |
| Lot lent | `-j 8`, `--no-external` si les moteurs externes ne servent à rien, `--include` pour cibler. |

Toujours possible en dernier recours : demander à l'utilisateur d'exporter le fichier depuis son application d'origine (PDF, DOCX, CSV) — et le dire au lieu de fabriquer du contenu.
