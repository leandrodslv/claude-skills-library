# Lecture visuelle — comment compléter ce qu'aucun script ne sait lire

Un script extrait le texte ; il ne « voit » pas. Scans, photos, captures d'écran, schémas dessinés, graphiques collés en image, écriture manuscrite : c'est **toi** qui lis l'image (outil Read sur un PNG ou un PDF). L'outil fait le tri : il n'affiche un marqueur que lorsqu'il est certain de ne pas avoir pu extraire le contenu, et il te prépare l'image à ouvrir.

**Règle d'or : ne rien inventer.** Une valeur, un nom ou une date qu'on ne lit pas avec certitude s'écrit `[illisible]` ou `[?]`. Mieux vaut un trou signalé qu'un chiffre plausible et faux.

## 1. Où sont les éléments à lire

- Dans le Markdown : un marqueur `> **[À COMPLÉTER : lecture visuelle]** …` (pages de PDF) ou `> **[À COMPLÉTER : description visuelle]** …` (image, diapositive, SVG). `convert.py --check` les recense.
- Dans `_report.json` : `vision_needed[]`, une entrée par élément :

  | Champ | Contenu |
  |---|---|
  | `source` | fichier d'origine |
  | `kind` | `page` (PDF), `slide` (diapositive), `image`, `svg` |
  | `path` | **fichier à ouvrir** : PNG rendu (page, diapositive, SVG) ou fichier original |
  | `pages` | plages de pages quand `path` est un PDF sans rendu (ex. `1-3,7`) |
  | `reason` | pourquoi (« aucun texte extractible », « OCR peu fiable », « SVG sans texte »…) |

- Le résumé affiché en fin de conversion liste les mêmes éléments sous « À TRAITER PAR LECTURE VISUELLE ».

## 2. Marche à suivre, élément par élément

1. **Ouvrir** `path` avec Read (image : directement ; PDF : paramètre `pages`, 20 pages maximum par appel).
2. **Décrire ou transcrire** selon le gabarit du § 3, dans la langue du document.
3. **Remplacer le marqueur** dans le `.md` avec Edit (le texte du marqueur est unique par page/diapositive : `… page 3 — aucun texte extractible …`). Conserve le repère `<!-- page N -->` ; ajoute `<!-- lu visuellement -->` juste avant ta transcription pour que la provenance reste traçable.
4. Quand tout est traité : `convert.py --check <dossier>` → « aucun problème détecté ».
5. Dans ta réponse à l'utilisateur, **dis ce qui a été lu visuellement** (fichiers, pages) : ces passages viennent de ta lecture, pas d'une extraction exacte.

Beaucoup d'éléments (plus d'une trentaine) : commence par ceux dont dépend la demande de l'utilisateur, traite le reste par lots, et dis clairement ce qui n'a pas été fait plutôt que de tout survoler.

## 3. Gabarits par type de contenu

**Page scannée / document photographié** — transcris fidèlement, dans l'ordre de lecture : titres en `##`, paragraphes, listes, tableaux en Markdown. Rien de tes commentaires dans le texte ; les éléments non textuels entre crochets : `[tampon : REÇU LE 12/03/2024]`, `[signature]`, `[logo ACME]`, `[manuscrit : « à rappeler »]`, `[illisible]`.

**Tableau en image** — un vrai tableau Markdown, mêmes en-têtes, mêmes nombres (séparateurs décimaux tels quels), cellules vides laissées vides, cellules fusionnées répétées.

**Graphique (barres, courbes, camembert…)** — une phrase de nature (« Histogramme des ventes par trimestre, en k€ ») puis un tableau des valeurs **lues** ; si tu estimes d'après la position d'une barre, préfixe par `≈` ; ne fabrique pas de précision. Reprends titre, axes, unités, légende.

**Schéma, organigramme, architecture, logigramme** — un bloc ` ```mermaid ` (`flowchart TD`/`LR`) fidèle aux boîtes et aux flèches (sens compris), libellés recopiés tels quels ; si la structure est trop libre, une liste hiérarchique. Ajoute une ligne de contexte (« Architecture de déploiement, 3 couches »).

**Capture d'écran** — texte visible de l'interface qui compte (titres, boutons, messages, valeurs), état (onglet actif, erreur affichée), et pour du code : le code dans un bloc ` ``` ` avec son langage.

**Photo, illustration** — description factuelle courte (sujet, cadre, texte visible), sans interprétation : `> *Photo : deux techniciens devant une armoire électrique ouverte ; étiquette « QE-3 » lisible.*` Pas de description de personnes au-delà de ce que la tâche exige.

**Logo, icône** — une ligne : `> *Logo : « ACME » en lettres bleues.*` / `> *Icône : engrenage.*`

**Formule** — LaTeX : `$E = mc^2$` en ligne, `$$…$$` en bloc.

**Manuscrit** — transcription, `[incertain : …]` pour les mots douteux ; signale que c'est un manuscrit.

## 4. Autres images à regarder (sans marqueur)

Les images d'un Word, d'un HTML, d'un EPUB… sont **extraites et référencées** (`![texte alternatif](x_assets/img-01.png)`). Quand leur contenu compte pour la tâche (graphique collé en image, capture, schéma) et que le texte alternatif est vide ou vague, ouvre-les : l'outil ajoute alors l'avertissement « N image(s) sans texte alternatif ». Une fois lue, complète le texte alternatif ou ajoute une ligne de description sous l'image.

## 5. Vérifier un texte OCR

Une page lue par OCR porte `<!-- page N (OCR 87 %) -->` et l'avertissement de confiance moyenne. Sous 60 % l'outil la marque pour lecture visuelle. Au-dessus, **compare quand même chiffres, montants, dates, noms propres et numéros** avec l'image (`--render` ou le PNG de la page) : l'OCR confond `0/O`, `1/l`, `5/S`, et perd les colonnes de tableaux.

## 6. Vérifier une conversion qui « semble bonne »

Diaporama plein de schémas, mise en page très travaillée, tableau qui paraît aplati : `convert.py fichier --render` écrit un PNG par page/diapositive dans le dossier d'assets (`apercu-001.png`…, listés dans `_report.json → previews`, jamais insérés dans le Markdown). Ouvre les pages douteuses et corrige le `.md` (Edit). Les diapositives masquées ne figurent pas dans les aperçus.
