# Format de sortie

## Arborescence

```text
md/                                  ← dossier de sortie (-o), défaut ./markdown_output
├── rapport.md                       ← un .md par fichier source, même arborescence que l'entrée
├── rapport_assets/                  ← images extraites, CSV complets, pièces jointes, PNG de pages à lire
│   ├── img-01.png
│   └── page-003.png
├── tableaux/
│   └── chiffres.md
├── mail.md
├── mail_attachments/                ← pièces jointes converties à leur tour (.md + assets), liées depuis mail.md
├── lot/                             ← contenu d'une archive lot.zip : chaque membre converti, arborescence gardée
│   └── a.md
├── long_chunks/                     ← seulement avec --chunk-tokens : part-01.md … part-NN.md + index.json
├── combined.md                      ← seulement avec --combined / --only-combined
├── INDEX.md                         ← tableau de tous les fichiers, statuts, éléments à lire visuellement, non convertis
├── RAPPORT.md                       ← compte rendu lisible : fiable / à relire (pourquoi) / lecture visuelle / non converti
├── _report.json                     ← rapport machine (voir ci-dessous)
└── .mdconv-cache.json               ← cache incrémental (peut être supprimé)
```

- **Nom** : `<nom-source>.md`. Deux sources de même nom dans le même dossier (`note.docx`, `note.pdf`) donnent `note.docx.md` et `note.pdf.md` : rien n'est écrasé. `--flat` met tout à plat, `--in-place` écrit à côté de chaque source.
- **Assets** : `<nom-du-md>_assets/`. Les liens du Markdown sont **relatifs** au `.md` et fonctionnent tels quels dans un éditeur, GitHub ou un chargeur de documents. `combined.md` réécrit les chemins d'images depuis sa propre racine.
- Le dossier de sortie n'est jamais reconverti s'il se trouve dans le dossier d'entrée.

## En-tête YAML (`--frontmatter`)

`min` (défaut) :

```yaml
---
source: rapports/2024/bilan.pptx
format: pptx
title: Bilan annuel
slides: 24            # pages / slides / feuilles / chapitres selon le format
words: 3120
tokens: ~5480         # estimation grossière (≈ 3,7 caractères par jeton ; 1 jeton par caractère CJK)
converter: mdconv/native
quality: 0.93         # seulement si < 0,995
warnings:             # seulement s'il y en a
  - 2 diapositive(s) masquée(s) (incluses, signalées)
needs_vision: 3       # seulement s'il reste des éléments à lire visuellement
---
```

`full` ajoute `size`, `sha256`, `author`, `created`, `modified`, `language`, `converted_at`. `none` : aucun en-tête (idéal pour la sortie standard ou pour coller dans un prompt).

## Conventions du Markdown produit

| Élément | Rendu |
|---|---|
| Titre du document | `# Titre` (métadonnées si elles existent et diffèrent du premier titre) |
| Pages PDF | `<!-- page N -->` avant chaque page ; `<!-- page N (OCR 87 %) -->` si lue par OCR |
| Diapositives | `## Slide N — titre` (`### …` sous des `## Section` du diaporama) ; `*(masquée)*` ; notes : `**Notes du présentateur :**` + citation ; commentaires : `**Commentaires :**` |
| Feuilles Excel | `## <nom de la feuille>` (`*(masquée)*`) ; un tableau par bloc de données |
| Notes de bas de page | `texte[^1]` … `[^1]: note` |
| Commentaires Word | `commenté[^c1]` … `[^c1]: **Auteur (date)** sur « texte commenté » : …` (réponses à la suite) |
| Modifications suivies | acceptées par défaut ; `--track-changes mark` → `<ins>…</ins>` / `<del>…</del>` |
| Tableaux | tableaux Markdown ; cellule multiligne → `<br>` ; `\|` échappé ; liste dans une cellule → `• a<br>• b` ; tronqué à `--table-rows` avec la mention « … N ligne(s) de plus » et le CSV complet en asset |
| Formules | `$…$` (ligne) et `$$…$$` (bloc), LaTeX |
| Diagrammes | ` ```mermaid ` `flowchart TD/LR` (nœuds `n1["libellé"]`, liens `-->`, `-->|étiquette|`, sous-graphes) |
| Code | blocs clôturés avec langage ; contenu jamais réécrit |
| Images | `![texte alternatif](<nom>_assets/img-01.png)` |
| Contenu illisible par script | `> **[À COMPLÉTER : lecture visuelle]** page 3 — aucun texte extractible …` (PDF) ou `> **[À COMPLÉTER : description visuelle]** …` |
| Dates, pourcentages, booléens Excel | ISO `2024-01-15`, `12%`, `TRUE`/`FALSE` |

Échappements : le texte est échappé pour ne pas être pris pour du balisage (`*`, `_`, `#` en début de ligne, `|` dans les tableaux, `<` …) ; l'italique s'écrit `_x_` (et `*x*` au milieu d'un mot).

## `_report.json`

```json
{
  "tool": "mdconv", "version": "1.0.0", "generated_at": "…", "inputs": ["entrants/"], "output_dir": "/abs/md",
  "summary": {"files": 12, "by_status": {"ok": 9, "needs_vision": 2, "unsupported": 1},
              "words": 41200, "tokens_est": 72100, "seconds": 8.4},
  "vision_needed": [
    {"source": "scan.pdf", "kind": "page", "path": "/abs/md/scan_assets/page-001.png", "reason": "page 1 : aucun texte extractible (page scannée ou image)"},
    {"source": "brochure.pdf", "kind": "page", "path": "/abs/brochure.pdf", "pages": "1-3,7", "reason": "aucun texte extractible (page scannée ou image)"}
  ],
  "files": [
    {"source": "rapport.docx", "format": "docx", "status": "ok", "output": "rapport.md", "engine": "native",
     "score": 1.0, "recall": 1.0, "words": 5230, "tokens_est": 8800, "title": "Rapport", "assets": 4,
     "warnings": ["…"], "vision": [ … ], "previews": ["/abs/md/rapport_assets/apercu-001.png"],
     "attempts": [{"engine": "native", "status": "ok", "score": 1.0, "words": 5230, "seconds": 0.04}],
     "seconds": 0.05}
  ]
}
```

`status` ∈ `ok · warn · needs_vision · unsupported · error · unchanged`. Les champs vides sont omis. Pour un fichier échoué : `error` explique pourquoi et quoi faire. `vision_needed[].path` est un chemin **absolu** directement ouvrable.

## `RAPPORT.md`

Écrit à chaque conversion (sauf `--in-place` et `-o -`). Sections : **Non convertis**, **À lire visuellement**, **Non lus volontairement** (`--no-vision`), **À relire** (avec la raison en clair : texte manquant, fidélité sous 90 %, avertissements), **Fiables, avec remarques**, **Fiables** (tableau). `--check` l'ignore. `_report.json` porte en plus la clé `unread` (éléments non lus sous `--no-vision`).

## `INDEX.md`

Tableau `Fichier source | Markdown | Format | Mots | Jetons | Statut`, suivi des sections « À traiter par lecture visuelle », « Non convertis » et « Avertissements ». C'est le point d'entrée pour un lot : le lire (ou `_report.json`) avant d'ouvrir les `.md` individuels.

## Découpage (`--chunk-tokens N`)

Pour chaque `.md` de plus de N jetons : dossier `<nom>_chunks/` avec `part-01.md`… (en-tête de commentaire `<!-- source: … · partie 2/5 · section: Titre > Sous-titre -->`) et `index.json` (`file`, `tokens`, `section`). Coupures aux titres, jamais au milieu d'un tableau ou d'un bloc de code (un tableau trop long est coupé par lignes avec son en-tête répété).

## Codes de retour

`0` : au moins un fichier converti (ou rien d'échoué) · `1` : aucun fichier converti / aucun fichier trouvé / `--check` a trouvé des problèmes · `2` : erreur d'usage (arguments, `-o -` avec plusieurs fichiers, dossier `--check` introuvable).
