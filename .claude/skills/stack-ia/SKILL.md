---
name: stack-ia
description: >
  Compose une "stack" de skills à partir de la bibliothèque personnelle de
  l'utilisateur (ce dépôt, `.claude/skills/`) pour un projet donné — une
  application, un site, un logiciel, un workflow n8n, une identité de
  marque, etc. Analyse l'intention du projet, consulte le catalogue interne
  des ~80 skills disponibles, puis recommande un sous-ensemble pertinent
  organisé par phase (recherche, design, développement, qualité,
  déploiement) avec la raison de chaque choix et l'ordre d'invocation
  suggéré. Déclencher dès que l'utilisateur dit : "équipe-moi pour ce
  projet", "quels skills utiliser pour X", "quelle stack pour créer...",
  "aide-moi à construire un workflow n8n avec des sous-workflows", "je veux
  créer une appli/un site/un logiciel, quels skills me servent", "prépare-moi
  les bons outils pour ce projet". Ne cherche PAS sur l'écosystème externe
  skills.sh (voir `find-skills` pour ça) — se limite à la bibliothèque
  personnelle déjà installée dans ce dépôt.
---

# Stack IA — Équipement de projet depuis la bibliothèque personnelle

## Rôle

Composer, à partir d'une description de projet, la liste des skills de
**cette bibliothèque** (`.claude/skills/`) les plus pertinents pour mener ce
projet à bien — et non les découvrir sur l'écosystème externe (c'est le
rôle de `find-skills`).

## Workflow

### 1. Comprendre le projet

Identifier à partir de la demande de l'utilisateur :

- **Le type de livrable** : application, site web, logiciel, workflow
  d'automatisation (n8n...), identité de marque, présentation, contenu,
  recherche/audit, etc.
- **La stack technique éventuelle** : React/Next.js, n8n, Figma, etc.
- **La ou les phases concernées** : tout le cycle (idée → livraison) ou
  seulement une étape précise (ex : "juste la partie design", "juste la
  revue de code").
- **Les contraintes annexes** : accessibilité, marque à respecter, cible
  (mobile/web), etc.

Si la demande est trop vague pour cibler une stack utile (ex: juste "aide-moi
avec un projet"), poser 1-2 questions ciblées avant de composer la stack —
ne pas deviner à l'aveugle sur un projet flou.

### 2. Consulter le catalogue

Lire `references/catalog.md` : la liste à jour des skills de la
bibliothèque, groupés par catégorie, avec description et source. C'est la
base de matching — ne pas se fier uniquement à la mémoire du modèle sur le
contenu de la bibliothèque, le catalogue peut avoir évolué.

Si un skill que tu sais avoir vu récemment ajouté n'apparaît pas dans le
catalogue (désynchronisation possible), scanner directement
`.claude/skills/*/SKILL.md` pour compléter.

### 3. Composer la stack, organisée par phase

Sélectionner uniquement les skills réellement pertinents pour **ce**
projet — pas un inventaire exhaustif de la bibliothèque. Regrouper la
recommandation par phase logique du projet, par exemple :

- **Cadrage / idéation** — ex: `brainstorming`, `naming`, `think` (si le
  projet a besoin d'être défriché avant de foncer)
- **Conception / design** — ex: `design-system`, `ui-ux-pro-max`, `frontend-design`,
  `figma-to-code`/`html-to-figma`, `brand`/`brandkit` si identité de marque
- **Développement / implémentation** — ex: `n8n-workflow-patterns` +
  `n8n-subworkflows` + `n8n-expression-syntax` pour un workflow n8n avec
  sous-workflows, ou `gsap-*` pour de l'animation, ou `web-design-guidelines`
  pour la qualité du code UI
- **Qualité / revue** — ex: `check`, `review-pr`, `caveman-review`,
  `rgaa-checker`/`color-contrast-checker` pour l'accessibilité,
  `n8n-validation-expert` pour un workflow n8n
- **Documentation / livraison** — ex: `output-skill`, `context-keeper` pour
  garder trace de l'avancement sur un projet long

Adapter les catégories à ce que le projet demande réellement — ne pas
forcer les 5 phases si le projet n'en a besoin que de 2 ou 3. Pour un
projet n8n avec sous-workflows par exemple, la stack pertinente tourne
surtout autour de `n8n-workflow-patterns`, `n8n-subworkflows`,
`n8n-expression-syntax`, `n8n-node-configuration`, `n8n-error-handling`,
`n8n-validation-expert`, `n8n-mcp-tools-expert` (et `using-n8n-mcp-skills`
en point d'entrée si le MCP n8n-mcp est configuré) — pas les skills de
design ou de branding.

### 4. Présenter la stack

Pour chaque skill retenu, donner en une ligne : **pourquoi** il est
pertinent pour ce projet précis (pas juste répéter sa description
générique). Indiquer un ordre d'invocation suggéré si un enchaînement a du
sens (ex: cadrage avant design avant dev avant revue).

Si un skill de la stack a des dépendances externes documentées (`NOTES.md`
dans son dossier — ex: `cavecrew`, `caveman-stats`, `using-n8n-mcp-skills`),
le signaler explicitement dans la présentation.

### 5. Proposer de démarrer

Terminer en proposant d'invoquer directement le premier skill de la stack
(ou celui que l'utilisateur choisit), plutôt que de simplement lister sans
suite.

## Ce que ce skill NE fait PAS

- Ne cherche pas de skills externes à cette bibliothèque (→ `find-skills`).
- N'installe ni ne modifie rien dans la bibliothèque — c'est un skill de
  recommandation, pas d'ajout (→ suivre le processus habituel pour ajouter
  un nouveau skill à la bibliothèque).
- Ne recommande pas des skills "au cas où" — mieux vaut 4 skills bien
  choisis que 15 approximatifs.
