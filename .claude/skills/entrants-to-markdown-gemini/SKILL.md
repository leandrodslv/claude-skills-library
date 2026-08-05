---
name: entrants-to-markdown-gemini
description: >
  Convertit en masse un dossier d'entrants hétérogènes (SVG, PPTX, PDF, DOCX, XLSX, images, schémas, captures d'écran, HTML, CSV, JSON, ZIP, audio...) en fichiers Markdown, avec une barre de progression dans le terminal. Variante de `entrants-to-markdown` qui automatise entièrement la lecture des fichiers visuels (SVG, images, schémas) via l'API Gemini au lieu de l'outil de vision de Claude — utile pour de gros volumes de visuels sans consommer le contexte de la conversation. Utilise ce skill dès que l'utilisateur veut convertir, transformer ou exporter un dossier de fichiers variés en Markdown en s'appuyant sur Gemini pour les visuels — même s'il ne mentionne qu'un seul format ou un dossier "d'entrants". Déclenche sur "convertis ce dossier en markdown avec Gemini", "batch convert to markdown via gemini", "j'ai un gros dossier d'images/schémas à décrire automatiquement", "utilise l'API Gemini pour décrire mes visuels", "génère un .md pour chaque fichier sans que tu regardes chaque image toi-même".
---

# Entrants → Markdown (via Gemini)

Convertit un dossier de fichiers d'entrée hétérogènes en Markdown, fichier par fichier, avec une barre de progression dans le terminal (style tqdm). Variante de [`entrants-to-markdown`](../entrants-to-markdown/SKILL.md) : la phase de lecture des fichiers **visuels** (SVG, images, schémas) est déléguée à l'**API Gemini** (multimodale) plutôt qu'à l'outil `view` de Claude.

**Pourquoi cette variante :** sur un dossier avec des dizaines/centaines de visuels, faire lire chaque image par Claude via `view` consomme énormément de contexte de conversation. En déléguant cette étape à l'API Gemini (appelée directement par le script Python, hors du contexte de Claude), la conversion reste scalable même sur de très gros dossiers.

## Vue d'ensemble du workflow

Le processus se fait en **deux phases automatiques**, gérées par un seul script, plus une phase manuelle résiduelle :

1. **Formats "texte/structure"** (PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML, ZIP, audio...) → convertis automatiquement via `markitdown`.
2. **Formats "visuels"** (SVG, PNG, JPG, GIF, WEBP, BMP, TIFF, schémas, captures...) → envoyés automatiquement à l'**API Gemini** (modèle multimodal) qui rédige directement la description Markdown. Pour les SVG, c'est le XML brut qui est envoyé en texte (pas de rendu image).
3. **Formats binaires propriétaires illisibles hors-ligne** (`.fig` de Figma) → ni `markitdown` ni Gemini ne peuvent les lire. Il faut passer par le MCP Figma (ou demander à l'utilisateur le lien de partage du fichier) — cette étape reste manuelle, à la charge de Claude.

Si l'API Gemini n'est pas configurée, échoue, ou est explicitement désactivée (`--skip-gemini`), le script **dégrade proprement** : les fichiers visuels concernés retombent dans une liste `vision_needed`, exactement comme dans le skill `entrants-to-markdown` d'origine, pour que Claude les traite lui-même avec `view`. Ne saute jamais cette liste silencieusement si elle n'est pas vide.

## Étape 1 — Vérifier les dépendances

```bash
pip install markitdown tqdm google-genai --break-system-packages
```

(Sur la machine locale de l'utilisateur en VS Code / Claude Code, l'option `--break-system-packages` n'est utile que sous Linux géré en externe ; sinon un simple `pip install markitdown tqdm google-genai` suffit.)

## Étape 2 — Configurer la clé API Gemini

Le script a besoin d'une clé API Gemini, récupérable gratuitement sur [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
export GEMINI_API_KEY="ta-clé-ici"
```

(`GOOGLE_API_KEY` fonctionne aussi comme alternative, et `--api-key` en ligne de commande permet de la passer explicitement.)

Si aucune clé n'est disponible, informe l'utilisateur que la phase 2 sera traitée manuellement par toi (Claude), ou lance le script avec `--skip-gemini` pour retrouver le comportement du skill `entrants-to-markdown` d'origine.

## Étape 3 — Lancer la conversion

```bash
python scripts/batch_convert_gemini.py --input <dossier_entrant> --output <dossier_sortie>
```

Options utiles :
- `--combined` : produit en plus un `combined.md` qui concatène tous les fichiers convertis (en plus des .md individuels)
- `--only-combined` : ne produit QUE le fichier combiné, pas de .md par fichier
- `--model <nom>` : modèle Gemini à utiliser (défaut : `gemini-2.5-flash`)
- `--delay <secondes>` : pause entre deux appels Gemini pour respecter les limites de débit du tier gratuit (défaut : 4.5s)
- `--skip-gemini` : désactive l'appel à Gemini, tous les visuels remontent dans `vision_needed` (comportement du skill d'origine)
- Par défaut (aucune option) : un `.md` par fichier d'entrée, dans `<dossier_entrant>/markdown_output/` si `--output` n'est pas précisé

Le script affiche une barre de progression pour la phase d'auto-conversion (markitdown), puis une seconde barre pour la phase de description visuelle (Gemini), et enfin un résumé :
- nombre de fichiers convertis automatiquement
- nombre de visuels décrits automatiquement par Gemini
- liste des visuels qui ont malgré tout besoin d'une lecture par Claude (échec Gemini, pas de clé, `--skip-gemini`, ou fichier `.fig`)
- erreurs éventuelles

Il écrit aussi `_conversion_report.json` dans le dossier de sortie avec toutes ces listes en structuré.

## Étape 4 — Traiter ce qui reste (fallback vision + `.fig`)

Lis `_conversion_report.json`.

- **Champ `vision_needed`** (non vide seulement si Gemini a échoué / pas de clé / `--skip-gemini`) : pour chaque fichier, applique exactement la procédure du skill `entrants-to-markdown` d'origine — SVG lu en XML brut, images ouvertes avec l'outil `view` — et crée `<nom_du_fichier>.md` dans le dossier de sortie.
- **Champ `api_needed`** (fichiers `.fig`) : vérifie si le MCP Figma est disponible dans la session.
  - Si oui : demande le lien Figma si besoin, utilise `Figma:get_design_context` (et `Figma:get_screenshot` si utile) pour extraire structure/textes/composants, puis rédige le Markdown.
  - Si non : explique à l'utilisateur que le `.fig` est illisible hors-ligne et demande soit le lien Figma, soit un export (PDF/PNG/SVG) à redéposer dans le dossier d'entrants.
  - Ne bloque jamais toute la conversion pour un `.fig` manquant — traite-le à part et signale-le dans le résumé final.

Si `--combined`/`--only-combined` était demandé, ajoute les nouvelles sections traitées manuellement à la fin de `combined.md`, dans le même style que les autres sections.

## Étape 5 — Résumé final

Une fois toutes les phases terminées, donne un court résumé à l'utilisateur :
- X fichiers convertis automatiquement (markitdown)
- Y visuels décrits automatiquement par Gemini
- Z visuels traités manuellement par toi (fallback)
- W fichiers `.fig` traités via Figma (ou en attente d'un lien/export)
- V erreurs (le cas échéant, avec la raison)
- où trouver les fichiers de sortie

## Notes

- Le script ne recrée jamais un `.md` pour un fichier déjà présent dans le dossier de sortie s'il est relancé — il écrase simplement (pas de gestion incrémentale pour l'instant).
- Les descriptions générées par Gemini sont écrites telles quelles ; si l'utilisateur signale une description visiblement fausse ou incomplète sur un fichier précis, relis ce fichier toi-même avec `view` et corrige son `.md`.
- Le `--delay` par défaut (4.5s) vise le tier gratuit de l'API Gemini (~15 requêtes/minute pour les modèles `flash`) ; augmente-le si le script renvoie des erreurs de quota, ou réduis-le si l'utilisateur a un tier payant.
- Les formats non reconnus par `markitdown`, absents de la liste des extensions visuelles, remontent dans `errors` du rapport — décide au cas par cas s'il faut les lire toi-même ou les ignorer.
- Le dossier de sortie n'est jamais reconverti même s'il se trouve à l'intérieur du dossier d'entrée.
