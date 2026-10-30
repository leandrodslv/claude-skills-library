# Batterie « cas extrêmes »

86 cas pour trouver où le skill casse, par **la vraie ligne de commande** (un processus par cas, plafonds de temps et de mémoire). Complète `benchmark/hard/` (documents *difficiles à bien restituer*) : ici on cherche les **plantages, fuites, blocages et pertes silencieuses**.

| Série | Cas |
|---|---|
| A — échelle | Excel 25 000 lignes, Word 4 000 paragraphes, PDF 400 pages, CSV 200 000 lignes, PowerPoint 200 diapositives, texte de 8 Mo sur une ligne, JSON 25 Mo, EPUB 600 chapitres, mbox 4 000 messages, SVG 700 nœuds, cellule de 1,5 Mo, 300 colonnes |
| B — hostilité | bombe zip (2 Go), « milliard de rires » (entités XML), XXE fichier local et réseau, zip avec `../` et chemin absolu, 14 zips imbriqués, HTML/XML/RTF/JSON profonds de 3 000 à 6 000 niveaux, bombe PNG de 1,6 milliard de pixels, consignes cachées dans un document, HTML actif, PDF à mot de passe |
| C — fichiers abîmés | 17 formats à 0 octet, tronqués à 50 %, octets aléatoires, mauvaise extension, sans extension, octets NUL, PDF à annuaire détruit, XML mal formé |
| D — Unicode | arabe, hébreu, CJK, emoji, combinants, BOM, CR/CRLF, UTF-16 sans BOM, charset HTML faux, substitut isolé, CSV français |
| E — noms de fichiers | accents, espaces, tiret initial, emoji, 180 caractères, mêmes noms dans deux dossiers |
| F — pièges Markdown | `\|` dans les cellules, clôtures ``` dans le contenu, listes à 12 niveaux, tableaux imbriqués, gras/italique collés |
| G — anciens formats | .xls 2 000 lignes, .ppt 80 diapositives, .doc 1 500 lignes |
| H — images | 1×1, animée, CMYK, tronquée, image de 1,6 Gpixel dans un docx |

```bash
python3 gen_extreme.py            # écrit ≈ 55 Mo dans _corpus/ (non versionné) + cases.json (les attentes)
python3 run_extreme.py --report EXTREME_RESULTS.md
python3 run_extreme.py --only B   # une série (préfixe de l'identifiant)
python3 run_extreme.py --extra --no-external   # même batterie, lecteurs natifs seuls
python3 gen_extreme.py ../../_c --only BCDF   # corpus réduit (≈ 10 Mo, quelques secondes) : celui de la CI
```

**En CI** (`.github/workflows/skills-ci.yml`, tâche `extreme-reduit`) : séries B, C, D et F, une exécution par série. La batterie complète reste manuelle (≈ 55 Mo, une à deux minutes).

Pillow et LibreOffice sont facultatifs pour la génération (sans eux, les cas « images », la bombe PNG, le PDF chiffré et les anciens formats volumineux sont omis). Un cas échoue sur : plantage non rattrapé, dépassement de temps ou de mémoire, statut inattendu, repère de contenu absent (sauf troncature **signalée**), contenu interdit présent (le secret d'une attaque XXE par exemple), clôtures ``` déséquilibrées, écriture hors du dossier de sortie.

## Ce que cette batterie a trouvé (et qui est corrigé)

- JSON contenant un substitut Unicode isolé : le programme plantait sans rapport et perdait tout le lot.
- HTML déclaré en UTF-8 mais encodé en latin-1 : accents faux, statut « ok ».
- Texte UTF-16 sans BOM, ou parsemé d'octets NUL : déclaré « binaire non reconnu ».
- Word, PowerPoint ou Excel tronqué ou au XML cassé : refusé en entier ; le moteur « secours » en récupère maintenant le texte (statut `warn`).
- Message d'erreur d'un outil externe qui recopiait un bout de traceback : une ligne utile seulement, le détail complet avec `--verbose`.
- Troncatures (tableau coupé à 1 000 lignes…) absentes de `_report.json` : maintenant `warnings` + champ `truncated`.
- Essais sur de vrais PDF (arXiv, IRS) : le lecteur natif plantait sur tout PDF moderne à flux d'objets (un entier lu comme un numéro d'objet). Couvert par `tests/test_extreme_fixes.py`.

## Lecteurs natifs seuls (`--extra --no-external`) : 85 / 86

C'est la configuration de la CI (aucun outil externe ; elle ne lance que les séries B, C, D, F : 86/86 y compris B8 et B10). Deux cas passent par un **refus propre** plutôt que par la lecture du contenu : **B8** (XML à 6 000 niveaux) et **B10** (JSON à 5 000 niveaux) — le lecteur natif répond « imbrication trop profonde pour ce moteur » (statut `error`, aucun plantage) ; avec les outils externes, markitdown prend le relais et lit le contenu.

Le cas qui échoue : **A3** (PDF de 400 pages). Avec pdftotext il passe ; avec le seul lecteur natif, la première ligne de chaque page (« PAGE-NNNN suite de mots ») est prise pour un en-tête courant (même position, même forme à un nombre près, sur plus de la moitié des pages) et retirée. Artefact d'un document fabriqué, mais un vrai texte répétitif peut subir la même chose. Pour le vérifier : `python3 run_extreme.py --only A3 --extra --no-external`.

## Limites

Cas fabriqués : ils ne remplacent pas vos documents réels. Les troncatures volontaires (1 000 lignes de tableau dans le Markdown, jeu complet en CSV annexe) sont attendues ; la batterie vérifie seulement qu'elles sont **signalées**. Le rapport `_report.json` n'en fait pas état dans ses avertissements (seul le Markdown le dit).
