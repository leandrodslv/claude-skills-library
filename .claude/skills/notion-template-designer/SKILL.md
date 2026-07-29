---
name: notion-template-designer
description: "Crée des templates Notion visuellement soignés en combinant recherche d'inspiration web, patterns de design éprouvés et création directe via MCP Notion. Utilise ce skill dès que l'utilisateur veut créer, designer, améliorer ou recopier quoi que ce soit dans Notion — même si le mot template n'est pas utilisé. Déclenche sur — template Notion, page Notion, workspace Notion, belle page dans Notion, dashboard Notion, rends ma page Notion plus belle, design ma Notion, inspire-toi de ce Pinterest, refais-moi ce template, base de données Notion, tracker Notion, journal Notion, portfolio Notion, roadmap Notion, setup Notion, organise ma Notion. Aussi quand l'utilisateur partage une capture de template ou un lien Pinterest/Dribbble/Notion gallery. Combine web_search, image_search, la bibliothèque de patterns design incluse, et le MCP Notion pour livrer des templates prêts à l'emploi. Toujours utiliser ce skill plutôt qu'une création ex-nihilo."
---

# Notion Template Designer

Transforme une demande vague ("je veux un beau journal Notion") en template structuré, visuellement cohérent, et directement utilisable — créé dans le Notion de l'utilisateur ou livré en markdown.

## Quand utiliser ce skill

Déclencher dès que l'utilisateur veut créer/améliorer quelque chose dans Notion. Si le brief est vague, **ne jamais inventer de zéro** : toujours passer par la phase de recherche d'inspiration d'abord.

## Pipeline en 5 phases

Suis ces phases dans l'ordre. Tu peux parfois compresser 2 phases si le brief est très précis, mais **ne saute jamais la phase 1** (recherche).

### Phase 1 — Cadrage (30 sec)

Pose **au maximum 2 questions** pour clarifier :
- **L'intention** : qu'est-ce que la page doit permettre de faire au quotidien ?
- **Le style visuel** : minimaliste / coloré / moody-dark / pastel / aesthetic / pro-corporate ?

Si l'utilisateur a déjà donné ces infos, ne redemande pas. Si l'utilisateur a partagé une capture d'écran ou un lien, considère que le style est défini et passe à la phase 2.

### Phase 2 — Recherche d'inspiration (obligatoire)

**Toujours combiner 2 types de recherches en parallèle** :

1. **Recherche d'images** via `image_search` :
   - Query type : `"[thème] notion template aesthetic"`, `"notion [thème] dashboard design"`, `"notion [thème] layout minimalist"`
   - Exemples : `"notion habit tracker aesthetic"`, `"notion portfolio UX designer"`, `"notion second brain minimalist"`
   - Demande 4 images pour avoir du choix

2. **Recherche web** via `web_search` :
   - Cible les sources de qualité : Notionry, Notion Template Gallery, Thomas Frank, Easlo, Prototion, Reddit r/Notion, Gridfiti
   - Exemples de queries : `"best notion [thème] template 2026"`, `"notion [thème] template gridfiti"`, `"notion [thème] easlo"`

**Présente 2-3 directions visuelles à l'utilisateur** en 1 phrase chacune (ex: "Direction A : minimaliste noir/blanc avec emojis monochromes — inspiré de Thomas Frank"). Laisse-le choisir.

Si l'utilisateur a partagé une image ou un lien : saute la présentation, analyse directement la référence (palette, emojis utilisés, structure des blocs) et annonce la direction retenue.

### Phase 3 — Architecture du template

Avant d'écrire quoi que ce soit, décide de la structure. Utilise les patterns de `references/design-patterns.md` pour :
- Le choix des blocs (callouts, toggles, colonnes, synced blocks)
- Les emojis (cohérence sémantique — voir `references/emoji-system.md`)
- Les covers (URL Unsplash testées — voir `references/covers-library.md`)
- Les bases de données et leurs vues (voir `references/database-patterns.md`)

Livre un **plan en 5-10 lignes** avec :
- Titre + emoji + cover proposé
- Liste hiérarchique des sections
- Bases de données à créer (avec leurs propriétés principales)
- Vues suggérées par base

### Phase 4 — Création

Deux modes disponibles. **Propose toujours les deux** à l'utilisateur sauf si sa préférence est déjà connue.

#### Mode A — Création directe via MCP Notion (préféré)

Si le MCP Notion est disponible (`Notion:notion-create-pages`, `Notion:notion-update-page`, `Notion:notion-create-database`) :

1. Demande la page parente où créer (ou recherche via `Notion:notion-search` si l'utilisateur donne un nom)
2. Crée la page principale avec `notion-create-pages` — inclure `emoji`, `cover`, et le `content` markdown complet
3. Crée les bases de données enfants avec `notion-create-database`
4. Update les vues avec `notion-update-view` si besoin de board/gallery/timeline

**Toujours créer en une seule passe** quand possible — Notion API supporte des pages complètes avec bases de données imbriquées.

#### Mode B — Fallback markdown

Si MCP indisponible ou si l'utilisateur préfère : génère un **fichier markdown** prêt à coller dans Notion, avec :
- En-tête clair : `# 🗂️ [Titre]` + ligne de citation pour la tagline
- Instructions de mise en forme en commentaires HTML `<!-- ... -->` quand Notion ne gère pas un élément en markdown pur (ex: colonnes, synced blocks)
- Section "Setup instructions" en fin de fichier avec les étapes manuelles (cover à uploader, vues de BDD à configurer)

Utilise `create_file` puis `present_files` pour livrer le `.md`.

### Phase 5 — Guide de style

À la fin, livre toujours un **mini guide de style visuel** (5-8 lignes) récapitulant :
- Palette emoji utilisée (ex: "🟢 🟡 🔴 pour priorités, 📝 ✨ 🎯 pour types de contenu")
- Logique des covers (ex: "Unsplash nature tons chauds")
- Convention de nommage (ex: "Titres en Title Case, sous-titres en lowercase")

Ce guide permet à l'utilisateur de **créer d'autres pages cohérentes** plus tard sans retomber dans le générique.

## Règles de design à ne jamais violer

Ces règles viennent de l'analyse des meilleurs templates Notion publics. Les respecter = éviter l'effet "template généré par IA".

1. **Jamais plus de 3 couleurs de callout par page.** Les templates surchargés en couleurs paraissent amateurs. Préfère : une couleur dominante + une accent + du gris.
2. **Les emojis sont sémantiques, pas décoratifs.** Un 🎯 = objectif, un 📝 = note, un ✨ = important. Garde la même logique partout dans le workspace.
3. **Toujours un cover.** Une page Notion sans cover paraît vide. Utilise `references/covers-library.md` pour des URLs Unsplash directes.
4. **Toggle pour tout ce qui est > 3 lignes et secondaire.** Les toggles pliés donnent une page aérée.
5. **Colonnes > listes pour les dashboards.** 2 ou 3 colonnes avec callouts donnent instantanément un look "dashboard pro".
6. **Synced blocks pour la navigation.** Une barre de nav synced en haut de chaque page principale = workspace qui semble conçu, pas improvisé.
7. **Bases de données : toujours au moins 2 vues.** Une table par défaut + au moins une vue filtrée (Board par statut, Calendar par date, Gallery par cover).

## Cas particulier : l'utilisateur partage une référence visuelle

Si l'utilisateur upload une capture d'écran ou envoie un lien Pinterest/Dribbble/Notion :

1. **Analyse la référence** : palette de couleurs, emojis utilisés, type de blocs (colonnes ? callouts ? gallery ?), densité d'information
2. **Décris ce que tu vois** en 3-4 points pour que l'utilisateur confirme
3. **Adapte au contenu demandé** sans copier littéralement (droits d'auteur) — capture l'esprit, pas le contenu
4. Passe directement à la phase 3

## Cas particulier : amélioration d'une page existante

Si l'utilisateur dit "ma page Notion est moche, rends-la belle" :

1. Demande le lien ou utilise `Notion:notion-fetch` pour récupérer le contenu
2. Diagnostic en 3-5 points (ex: "Pas de cover, callouts tous de la même couleur, pas de hiérarchie visuelle")
3. Propose 2 directions de refonte
4. Update avec `Notion:notion-update-page` une fois la direction choisie

## Référentiels à consulter

Ce SKILL.md est volontairement court. Pour les détails, lis ces fichiers au bon moment :

- **`references/design-patterns.md`** — Patterns de layout (dashboards, journaux, trackers, portfolios). Lire en phase 3.
- **`references/emoji-system.md`** — Conventions emoji par domaine (productivité, créatif, pro). Lire en phase 3.
- **`references/covers-library.md`** — URLs Unsplash directes par thème/mood. Lire en phase 3.
- **`references/database-patterns.md`** — Schémas de BDD types (tasks, projets, CRM, habits, reading list). Lire en phase 3.
- **`references/notion-mcp-cheatsheet.md`** — Exemples concrets d'appels MCP Notion pour créer pages/BDD/vues. Lire en phase 4 Mode A.
- **`references/style-directions.md`** — Les 6 directions visuelles prédéfinies (minimaliste, pastel, dark, etc.) avec leur palette complète. Lire en phase 2 pour présenter les options.

## Exemples de bons vs mauvais outputs

**Mauvais exemple** (ne fais pas ça) :
> "Voici ton template habit tracker ! Je l'ai créé avec des titres et une liste des habitudes. Tu peux l'adapter."

→ Trop vague, pas de recherche, pas de cover, pas de BDD, pas de style défini.

**Bon exemple** (fais ça) :
> J'ai cherché des templates habit tracker inspirants. Voici 3 directions :
> - **A — Minimaliste Thomas Frank** : monochrome noir/blanc, emojis discrets, focus sur la streak
> - **B — Aesthetic pastel** : tons pêche/lavande, covers illustrées, gallery view
> - **C — Dashboard data-driven** : progress bars, stats, vues multiples
>
> Laquelle te parle le plus ? Ou tu veux un mix ?

→ Recherche effectuée, choix offert, directions claires.
