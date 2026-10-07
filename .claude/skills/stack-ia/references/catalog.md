# Catalogue des skills de la bibliothèque

Référence interne pour le skill `stack-ia`. Générée à partir du README
principal — une ligne par skill installé dans `.claude/skills/`, groupée
par origine (mes skills / skills importés) puis par métier et catégorie.
Si un skill récemment ajouté n'apparaît pas ici, se rabattre sur un scan
direct de `.claude/skills/*/SKILL.md`.

**Total : 97 skills.**

> ℹ️ Les skills d'automatisation n8n (15) et d'animation Motion/GSAP (8)
> vivent dans le dépôt privé séparé `claude-skills-n8n-motion` — absents
> de ce catalogue, qui ne couvre que `claude-skills-library`.

## 🧑 Mes skills

### 🎨 Design — UI / Product Design
- **`notion-template-designer`** — Crée des templates Notion visuellement soignés (dashboards, trackers, portfolios...) via recherche d'inspiration et le MCP Notion. _(source : Original (skill personnel))_

### 🎨 Design — Accessibilité
- **`color-contrast-checker`** — Analyse le contraste de couleurs d'une image (maquette, capture d'écran) et produit un rapport d'accessibilité WCAG/RGAA. _(source : Original (skill personnel))_

### 🤝 Handoff Design↔Dev
- **`figma-to-code`** — Convertit une maquette Figma en code HTML/CSS, React ou Vue pixel-perfect. _(source : Original (skill personnel))_
- **`html-to-figma`** — Convertit des fichiers HTML/CSS en maquette Figma pixel-perfect via le MCP Figma. _(source : Original (skill personnel))_

### 💻 Dev — QA / Agents
- **`test-agent`** — Framework de test pour agents IA avec génération automatique de scénarios, exécution sandboxée et rapport détaillé. _(source : Original (aucun dépôt public identifié))_

### 🔁 Autres / Transverse
- **`git-github`** — Automatisation Git & GitHub de bout en bout : commits conventionnels, push/pull, branches, PR, issues, Actions, Dependabot, releases. Pensé pour rendre Git accessible à qui ne le maîtrise pas (designers, PM...), pas seulement aux devs. _(source : Original (skill personnel))_
- **`context-keeper`** — Crée, met à jour et restaure un fichier de contexte maître capturant l'état de tous les projets en cours pour reprendre instantanément dans n'importe quelle conversation. _(source : Original (skill personnel))_
- **`stack-ia`** — Compose une "stack" de skills à partir de cette bibliothèque pour un projet donné. _(source : Original (skill personnel))_
- **`brainstorming`** — Facilitation de sessions de brainstorming/idéation (HMW, SCAMPER, Crazy 8s, brainwriting...), sélection automatique de la méthode adaptée. _(source : Original (skill personnel))_
- **`naming`** — Naming créatif pour projets, artistes IA/musicaux, agents IA et workflows — shortlist commentée avec taglines. _(source : Original (skill personnel))_

## 🌐 Skills importés

### 🎨 Design — UX Research
- **`ux-research`** — Génère des guides d'entretien utilisateur et questionnaires UX complets en français. _(source : Compte Claude (pas de dépôt public identifié))_
- **`uxr-preparation`** — Prépare des entretiens UXR semi-directifs de A à Z et écrit dans Notion. _(source : Compte Claude (pas de dépôt public identifié))_
- **`uxr-synthese`** — Analyse et synthétise des notes d'entretiens (Dit/Fait/Ressent/Besoin, affinity mapping, insights, persona). _(source : Compte Claude (pas de dépôt public identifié))_
- **`uxr-recherche-secondaire`** — Mène une recherche secondaire UX (desk research) rigoureuse, sources notées par fiabilité. _(source : Compte Claude (pas de dépôt public identifié))_

### 🎨 Design — UI / Product Design
> ⚠️ `ui-ux-pro-max` est une base de connaissances générale ; `taste-skill`,
> `taste-skill-v1`, `gpt-tasteskill`, `soft-skill`, `minimalist-skill` et
> `brutalist-skill` sont 6 variantes du même bundle (Leonxlnx/taste-skill)
> pour des directions esthétiques différentes — choisir celle qui
> correspond au projet plutôt que tout installer.

- **`ui-ux-pro-max`** — Base de connaissances massive UI/UX (styles, palettes, typographies, règles UX...). _(source : [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill))_
- **`ui-styling`** — Interfaces accessibles avec shadcn/ui et Tailwind. _(source : [mrgoonie/claudekit-skills](https://github.com/mrgoonie/claudekit-skills))_
- **`ui`** — Création d'interfaces distinctives orientées direction artistique. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`soft-skill`** — UI premium, épurée et haut de gamme. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`minimalist-skill`** — Design éditorial inspiré de Notion et Linear. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`brutalist-skill`** — Interfaces radicales à inspiration brutaliste. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`taste-skill`** — Anti-slop frontend pour IA. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`taste-skill-v1`** — Version 1 du skill anti-slop frontend. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`gpt-tasteskill`** — Variante optimisée pour GPT/Codex. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`redesign-skill`** — Audit et amélioration d'interfaces existantes. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`impeccable`** — Ensemble de commandes de critique, polish et amélioration frontend. _(source : [pbakaus/impeccable](https://github.com/pbakaus/impeccable))_
- **`imagegen-frontend-web`** — Génération de maquettes web de référence. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`imagegen-frontend-mobile`** — Génération de références mobiles iOS/Android. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`image-to-code-skill`** — Pipeline image → analyse → implémentation frontend. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_

### 🎨 Design — Branding & Identité
- **`brand`** — Positionnement, voix et cohérence de marque. _(source : ClaudeKit Marketing Kit (payant, pas de dépôt public))_
- **`design`** — Branding complet : logos, identité, assets marketing. _(source : ClaudeKit Marketing Kit (payant, pas de dépôt public))_
- **`design-system`** — Architecture de design systems et bibliothèques de composants. _(source : ClaudeKit Marketing Kit (payant, pas de dépôt public))_
- **`brandkit`** — Génération de kits de marque complets. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`banner-design`** — Création de bannières marketing et visuels promotionnels. _(source : ClaudeKit Marketing Kit (payant, pas de dépôt public))_
- **`canvas-design`** — Production d'œuvres visuelles, affiches et posters. _(source : [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic))_
- **`brand-guidelines`** — Application de la charte visuelle officielle Anthropic. _(source : [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic))_

### 🤝 Handoff Design↔Dev
- **`figma-design-to-code`** — Transformation rigoureuse de designs Figma en composants réels. _(source : [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide) (officiel Figma))_
- **`stitch-skill`** — Workflow compatible Google Stitch. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_
- **`slides`** — Présentations HTML stratégiques avec design system intégré. _(source : ClaudeKit Marketing Kit (produit payant, pas de dépôt public))_
- **`web-design-guidelines`** — Revue de code UI selon les Web Interface Guidelines (accessibilité, performance, UX — 100+ règles). _(source : [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (officiel Vercel Labs))_
- **`frontend-design`** — Design frontend distinctif et haut de gamme (direction artistique, typographie, choix qui évitent l'esthétique générique IA). _(source : [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic))_

### 💻 Dev — Méthodologie & discipline dev (Superpowers)
> Skills [obra/superpowers-skills](https://github.com/obra/superpowers-skills), sous licence MIT — plus `karpathy-guidelines` (auteur distinct).
> ⚠️ `superpowers-brainstorming` est le skill `brainstorming` d'origine du dépôt, renommé pour éviter la collision avec le skill personnel `brainstorming`.

- **`using-skills`** — Point d'entrée du wiki de skills — workflows obligatoires, outil de recherche, déclencheurs de brainstorming.
- **`superpowers-brainstorming`** — Affinage interactif d'idées par méthode socratique, avant tout code ou plan d'implémentation.
- **`writing-plans`** — Rédige des plans d'implémentation détaillés, en tâches digestes.
- **`executing-plans`** — Exécute un plan détaillé par lots, avec points de contrôle de revue.
- **`subagent-driven-development`** — Exécute un plan en dispatchant un sous-agent frais par tâche, avec revue de code entre chaque tâche.
- **`dispatching-parallel-agents`** — Utilise plusieurs agents en parallèle pour investiguer/corriger des problèmes indépendants.
- **`requesting-code-review`** — Dispatch un sous-agent reviewer pour vérifier une implémentation avant de continuer.
- **`receiving-code-review`** — Traite les retours de revue avec rigueur technique, sans accord de façade.
- **`using-git-worktrees`** — Crée des worktrees git isolés avec sélection intelligente du répertoire et vérifications de sécurité.
- **`finishing-a-development-branch`** — Options structurées pour merge/PR/nettoyage une fois l'implémentation terminée et testée.
- **`remembering-conversations`** — Recherche sémantique/texte dans l'historique des conversations Claude Code passées.
- **`systematic-debugging`** — Framework de debug en 4 phases — jamais de correctif avant d'avoir investigué la cause racine.
- **`root-cause-tracing`** — Remonte systématiquement la pile d'appels pour trouver le déclencheur d'origine d'un bug.
- **`defense-in-depth`** — Valide à chaque couche que traversent les données pour rendre les bugs impossibles.
- **`verification-before-completion`** — Exécute les commandes de vérification et confirme le résultat avant d'annoncer un travail terminé.
- **`test-driven-development`** — Écrit le test d'abord, le regarde échouer, puis écrit le minimum de code pour le faire passer.
- **`testing-anti-patterns`** — Ne jamais tester le comportement d'un mock, ni ajouter des méthodes test-only au code de prod.
- **`condition-based-waiting`** — Remplace les timeouts arbitraires par du polling de condition pour des tests async fiables.
- **`when-stuck`** — Redirige vers la bonne technique de résolution de problème selon le type de blocage.
- **`collision-zone-thinking`** — Force le rapprochement de concepts sans rapport pour révéler des propriétés émergentes.
- **`inversion-exercise`** — Inverse les hypothèses de base pour révéler des contraintes cachées et d'autres approches.
- **`meta-pattern-recognition`** — Repère les motifs qui apparaissent dans 3+ domaines pour trouver des principes universels.
- **`scale-game`** — Teste aux extrêmes (1000x plus grand/petit) pour exposer des vérités fondamentales.
- **`simplification-cascades`** — Cherche l'insight unique qui élimine plusieurs composants d'un coup.
- **`preserving-productive-tensions`** — Reconnaît quand un désaccord révèle un contexte précieux, plutôt que de forcer une résolution prématurée.
- **`tracing-knowledge-lineages`** — Comprend comment une idée a évolué dans le temps pour éviter de répéter d'anciens échecs.
- **`writing-skills`** — TDD appliqué à la documentation de process.
- **`testing-skills-with-subagents`** — RED-GREEN-REFACTOR pour la documentation de process.
- **`gardening-skills-wiki`** — Maintient la santé du wiki de skills — liens, naming, références croisées, couverture.
- **`sharing-skills`** — Contribue un skill en amont via branche et PR vers le dépôt upstream.
- **`pulling-updates-from-skills-repository`** — Synchronise la bibliothèque locale avec les changements upstream.
- **`karpathy-guidelines`** — 4 principes comportementaux dérivés des observations d'Andrej Karpathy. _(source : [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills))_

### 💻 Dev — Graphe de code / Review
> ⚠️ Nécessitent l'installation préalable du moteur **code-review-graph** ([tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)).

- **`build-graph`** — Construction du graphe de connaissance.
- **`debug-issue`** — Débogage guidé par le graphe.
- **`explore-codebase`** — Exploration structurelle du code.
- **`refactor-safely`** — Refactoring piloté par les dépendances.
- **`review-changes`** — Revue d'impact des modifications.
- **`review-delta`** — Revue des changements depuis le dernier commit.
- **`review-pr`** — Revue complète de Pull Request.

### 💻 Dev — Discipline de livraison
- **`output-skill`** — Force des livrables complets sans placeholders. _(source : [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill))_

### 🔁 Autres / Transverse
- **`caveman`** — Mode de communication ultra-compressé (-65% de tokens en sortie), plusieurs niveaux d'intensité. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`caveman-commit`** — Génère des messages de commit ultra-compressés au format Conventional Commits. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`caveman-review`** — Commentaires de revue de code ultra-compressés, un par ligne. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`caveman-compress`** — Compresse des fichiers mémoire (CLAUDE.md, todos, préférences) en format caveman. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`caveman-help`** — Carte de référence rapide de tous les modes/skills/commandes caveman. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`caveman-stats`** — Affiche l'usage réel de tokens et les économies estimées de la session. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`cavecrew`** — Guide de délégation à 3 sous-agents caveman-compressés. _(source : [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman))_
- **`think`** — Remise en question du problème et planification stratégique. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`read`** — Lecture de pages web et PDF. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`learn`** — Recherche structurée en plusieurs phases. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`write`** — Réécriture de textes naturels et fluides. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`check`** — Revue de livraison avant merge ou release. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`hunt`** — Recherche systématique de causes racines. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`health`** — Audit de santé d'agents IA. _(source : [tw93/Waza](https://github.com/tw93/Waza))_
- **`academic-pptx-skill`** — Structure des présentations académiques et de recherche. _(source : [Gabberflast/academic-pptx-skill](https://github.com/Gabberflast/academic-pptx-skill))_
- **`speech-script`** — Génération de scripts de discours naturels et fluides. _(source : [sgharlow/claude-code-recipes](https://github.com/sgharlow/claude-code-recipes))_
- **`find-skills`** — Aide à découvrir et installer des skills de l'écosystème open. _(source : [vercel-labs/skills](https://github.com/vercel-labs/skills) (officiel Vercel Labs))_
