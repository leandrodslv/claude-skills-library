# 📚 Bibliothèque de Skills

> Bibliothèque personnelle de skills Claude Code — design/UX, branding, revue de code, économie de tokens, et frameworks de référence (BMAD), prêts à installer.

> Mon espace personnel pour **Claude Code** : un dépôt unique où je centralise les skills et profils `CLAUDE.md` que j'utilise ou développe.
>
> **Objectif :** ne rien perdre entre les projets, partager facilement des composants réutilisables et disposer d'une bibliothèque prête à l'emploi partout.
>
> ℹ️ Les skills d'**automatisation n8n** (15), d'**animation Motion/GSAP** (8) et `notion-template-designer` ont été déplacés vers un dépôt privé dédié (`claude-skills-n8n-motion`), car ils ne concernent que mon usage personnel.

---

# 🗂️ Trois types de ressources

Cette bibliothèque contient trois catégories distinctes.

## ⚡ Skills

**Emplacement dans cette bibliothèque** (origine → métier → catégorie) :

```text
<origine>/<métier>/<catégorie>/.claude/skills/<nom>/SKILL.md
```

```text
mes-skills/   ou   importes/
└── design/ · handoff-design-dev/ · dev/ · autres-transverse/
    └── <catégorie>/
        └── .claude/skills/<nom>/SKILL.md
```

**Emplacement dans un projet où tu l'utilises** (inchangé) :

```text
.claude/skills/<nom>/SKILL.md
```

Les skills sont des commandes directement utilisables dans Claude Code :

```text
/<nom-du-skill>
```

Pour utiliser **un seul skill**, copie uniquement son dossier `<nom>/` (voir « Installer un skill dans un autre projet »).

> 💡 **Comment ça se charge ici.** Claude Code ne lit qu'un niveau sous un dossier `.claude/skills/`,
> mais il en accepte un dans chaque sous-dossier du dépôt (testé jusqu'à 5 niveaux de profondeur).
> Dans cette bibliothèque, les skills d'une catégorie se chargent la première fois que Claude lit ou
> modifie un fichier de ce dossier, ou tout de suite avec `/add-dir <dossier-de-la-catégorie>`.
> Si deux skills portent le même nom, la commande qualifiée est `/<chemin>:<nom>`.

---

## 📄 Profils `CLAUDE.md`

**Emplacement :**

```text
claude-md-profiles/
```

Les profils **ne sont pas des skills** et ne créent aucune commande.

Ils doivent être copiés :

### À la racine du projet

```text
MonProjet/
└── CLAUDE.md
```

### Ou globalement

```text
~/.claude/CLAUDE.md
```

Claude Code les charge automatiquement à chaque message.

---

## 🧩 Frameworks de référence

**Emplacement :**

```text
frameworks/<nom>/
```

Certains outils de l'écosystème agent ne sont **pas des skills autonomes**
mais des frameworks complets avec leur propre installeur (ils créent leur
propre infrastructure de projet — config, scripts, catalogues — au moment de
l'installation). Les copier tels quels dans `.claude/skills/` produirait des
skills cassés. Pour ceux-là, ce dossier contient une fiche de référence
(README d'origine vendorisé + notes) plutôt qu'un skill installable.

| Framework | Description | Source |
|---------|-------------|--------|
| `bmad-method` | Développement agile piloté par agents IA — 12+ agents experts (PM, Architecte, Dev, UX...), workflows structurés de l'analyse à l'implémentation. S'installe par projet via `npx bmad-method@next install`. | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) |

---

# 🚀 Skills disponibles

La bibliothèque regroupe actuellement plusieurs familles de skills.

> 💡 Chaque skill importé d'un dépôt externe contient désormais son propre
> `README.md` (le README d'origine, vendorisé tel quel) directement dans son
> dossier `.claude/skills/<nom>/` — c'est la meilleure source pour comprendre
> un skill en détail. Quand aucun dépôt public n'existe, un `SOURCE.md`
> explique la provenance à la place. La colonne **Source** ci-dessous pointe
> vers le dépôt d'origine de chaque skill.

# 🧑 Mes skills (créés par moi)

Skills que j'ai écrits moi-même, sans dépôt externe derrière. Classés par
**métier** puis par **catégorie**.

## 🎨 Design

### Accessibilité

📁 `mes-skills/design/accessibilite/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `color-contrast-checker` | Analyse le contraste de couleurs d'une image (maquette, capture d'écran) et produit un rapport d'accessibilité WCAG/RGAA. | Original (skill personnel) |

---

## 🤝 Handoff Design↔Dev

📁 `mes-skills/handoff-design-dev/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `figma-to-code` | Convertit une maquette Figma en code HTML/CSS, React ou Vue pixel-perfect. | Original (skill personnel) |
| `html-to-figma` | Convertit des fichiers HTML/CSS en maquette Figma pixel-perfect via le MCP Figma. | Original (skill personnel) |

---

## 💻 Dev

### QA / Agents

📁 `mes-skills/dev/qa-agents/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `test-agent` | Framework de test pour agents IA avec génération automatique de scénarios, exécution sandboxée et rapport détaillé. | Original (aucun dépôt public identifié) |

---

## 🔁 Autres / Transverse

Utile à tous les métiers utilisant Claude Code, pas seulement aux devs.

### Git & GitHub accessible aux non-devs

📁 `mes-skills/autres-transverse/git-github-accessible-aux-non-devs/.claude/skills/<nom>/`

> 💡 `git-github` n'est pas un skill "pour les devs qui savent déjà faire
> ça" — il existe pour que quelqu'un sans compétence Git (designer, PM...)
> puisse quand même commit/push/gérer une PR via Claude.

| Skill | Description | Source |
|---------|-------------|--------|
| `git-github` | Automatisation Git & GitHub de bout en bout : commits conventionnels, push/pull, branches, PR (création et revue), issues, GitHub Actions, Dependabot, releases via release-please. | Original (skill personnel) |

### Productivité perso

📁 `mes-skills/autres-transverse/productivite-perso/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `context-keeper` | Crée, met à jour et restaure un fichier de contexte maître capturant l'état de tous les projets en cours pour reprendre instantanément dans n'importe quelle conversation. | Original (skill personnel) |
| `stack-ia` | Compose une "stack" de skills à partir de **cette bibliothèque** (pas de l'écosystème externe, voir `find-skills` pour ça) pour un projet donné — appli, site, logiciel, workflow n8n, branding... Analyse le projet, consulte le catalogue interne (`references/catalog.md`), et recommande un sous-ensemble pertinent organisé par phase. | Original (skill personnel) |

### Idéation / créativité

📁 `mes-skills/autres-transverse/ideation-creativite/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `brainstorming` | Facilitation de sessions de brainstorming/idéation (HMW, SCAMPER, Crazy 8s, brainwriting...), sélection automatique de la méthode adaptée. | Original (skill personnel) |
| `naming` | Naming créatif pour projets, artistes IA/musicaux, agents IA et workflows — shortlist commentée avec taglines. | Original (skill personnel) |

---

# 🌐 Skills importés d'internet

Skills importés depuis des dépôts publics, des marketplaces officielles ou
des produits tiers — voir la colonne **Source** pour l'origine exacte de
chacun. Classés par **métier** puis par **catégorie**.

## 🎨 Design

### UX Research

📁 `importes/design/ux-research/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `ux-research` | Génère des guides d'entretien utilisateur et questionnaires UX complets en français, adaptés à un contexte entreprise (clients et conseillers internes). | Compte Claude (pas de dépôt public identifié) |
| `uxr-preparation` | Prépare des entretiens UXR semi-directifs de A à Z (cadrage, profil participant, guide en 5 phases, checklist, grille de notes, biais à surveiller) et écrit dans Notion. | Compte Claude (pas de dépôt public identifié) |
| `uxr-synthese` | Analyse et synthétise des notes d'entretiens (grille Dit/Fait/Ressent/Besoin, affinity mapping, insights priorisés, persona, patterns cross-entretiens) et écrit dans Notion. | Compte Claude (pas de dépôt public identifié) |
| `uxr-recherche-secondaire` | Mène une recherche secondaire UX (desk research) rigoureuse : sources notées par fiabilité, triangulation, insights avec niveau de confiance, restitution exportable en Word. | Compte Claude (pas de dépôt public identifié) |

### UI / Product Design

📁 `importes/design/ui-product-design/.claude/skills/<nom>/`

> ⚠️ `taste-skill`, `taste-skill-v1`, `gpt-tasteskill`, `soft-skill`,
> `minimalist-skill` et `brutalist-skill` sont 6 variantes du même bundle
> ([Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)) pour
> des directions esthétiques différentes — choisir celle qui correspond
> au projet plutôt que toutes les installer.

| Skill | Description | Source |
|---------|-------------|--------|
| `ui-ux-pro-max` | Base de connaissances massive UI/UX (styles, palettes, typographies, règles UX...). | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| `ui-styling` | Interfaces accessibles avec shadcn/ui et Tailwind. | [mrgoonie/claudekit-skills](https://github.com/mrgoonie/claudekit-skills) |
| `ui` | Création d'interfaces distinctives orientées direction artistique. | [tw93/Waza](https://github.com/tw93/Waza) |
| `soft-skill` | UI premium, épurée et haut de gamme. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `minimalist-skill` | Design éditorial inspiré de Notion et Linear. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `brutalist-skill` | Interfaces radicales à inspiration brutaliste. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `taste-skill` | Anti-slop frontend pour IA. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `taste-skill-v1` | Version 1 du skill anti-slop frontend. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `gpt-tasteskill` | Variante optimisée pour GPT/Codex. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `redesign-skill` | Audit et amélioration d'interfaces existantes. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `impeccable` | Ensemble de commandes de critique, polish et amélioration frontend. | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) |

### Génération visuelle

📁 `importes/design/generation-visuelle/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `imagegen-frontend-web` | Génération de maquettes web de référence. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `imagegen-frontend-mobile` | Génération de références mobiles iOS/Android. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `image-to-code-skill` | Pipeline image → analyse → implémentation frontend. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |

### Branding & Identité

📁 `importes/design/branding-identite/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `brand` | Positionnement, voix et cohérence de marque. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `design` | Branding complet : logos, identité, assets marketing. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `design-system` | Architecture de design systems et bibliothèques de composants. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `brandkit` | Génération de kits de marque complets. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `banner-design` | Création de bannières marketing et visuels promotionnels. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `canvas-design` | Production d'œuvres visuelles, affiches et posters. | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |
| `brand-guidelines` | Application de la charte visuelle officielle Anthropic. | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |

---

## 🤝 Handoff Design↔Dev

### Design → Code

📁 `importes/handoff-design-dev/design-code/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `figma-design-to-code` | Transformation rigoureuse de designs Figma en composants réels. | [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide) (officiel Figma) |
| `stitch-skill` | Workflow compatible Google Stitch. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `slides` | Présentations HTML stratégiques avec design system intégré. | ClaudeKit Marketing Kit (produit payant, [docs](https://docs.claudekit.cc/docs/marketing/skills/) — pas de dépôt public) |

### Revue / direction artistique code

📁 `importes/handoff-design-dev/revue-direction-artistique-code/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `web-design-guidelines` | Revue de code UI selon les Web Interface Guidelines (accessibilité, performance, UX — 100+ règles). | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (officiel Vercel Labs) |
| `frontend-design` | Design frontend distinctif et haut de gamme (direction artistique, typographie, choix qui évitent l'esthétique générique IA). | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |

---

## 💻 Dev

### Méthodologie & discipline dev (Superpowers)

📁 `importes/dev/methodologie-discipline-dev-superpowers/.claude/skills/<nom>/`

> Skills [obra/superpowers-skills](https://github.com/obra/superpowers-skills) (Jesse Vincent, 200K+ ⭐, accepté au marketplace officiel Anthropic), sous licence MIT — plus `karpathy-guidelines` (auteur distinct, voir en bas de tableau).
> ⚠️ `superpowers-brainstorming` est le skill `brainstorming` d'origine du dépôt, renommé pour éviter la collision avec le skill personnel `brainstorming` déjà présent dans cette bibliothèque.

| Skill | Description | Source |
|---------|-------------|--------|
| `using-skills` | Point d'entrée du wiki de skills — workflows obligatoires, outil de recherche, déclencheurs de brainstorming. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `superpowers-brainstorming` | Affinage interactif d'idées par méthode socratique, avant tout code ou plan d'implémentation. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `writing-plans` | Rédige des plans d'implémentation détaillés, en tâches digestes, pour un développeur sans contexte du code. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `executing-plans` | Exécute un plan détaillé par lots, avec points de contrôle de revue. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `subagent-driven-development` | Exécute un plan en dispatchant un sous-agent frais par tâche, avec revue de code entre chaque tâche. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `dispatching-parallel-agents` | Utilise plusieurs agents en parallèle pour investiguer/corriger des problèmes indépendants. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `requesting-code-review` | Dispatch un sous-agent reviewer pour vérifier une implémentation avant de continuer. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `receiving-code-review` | Traite les retours de revue avec rigueur technique, sans accord de façade ni application aveugle. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `using-git-worktrees` | Crée des worktrees git isolés avec sélection intelligente du répertoire et vérifications de sécurité. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `finishing-a-development-branch` | Options structurées pour merge/PR/nettoyage une fois l'implémentation terminée et testée. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `remembering-conversations` | Recherche sémantique/texte dans l'historique des conversations Claude Code passées. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `systematic-debugging` | Framework de debug en 4 phases — jamais de correctif avant d'avoir investigué la cause racine. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `root-cause-tracing` | Remonte systématiquement la pile d'appels pour trouver le déclencheur d'origine d'un bug. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `defense-in-depth` | Valide à chaque couche que traversent les données pour rendre les bugs impossibles. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `verification-before-completion` | Exécute les commandes de vérification et confirme le résultat avant d'annoncer un travail terminé. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `test-driven-development` | Écrit le test d'abord, le regarde échouer, puis écrit le minimum de code pour le faire passer. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `testing-anti-patterns` | Ne jamais tester le comportement d'un mock, ni ajouter des méthodes test-only au code de prod. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `condition-based-waiting` | Remplace les timeouts arbitraires par du polling de condition pour des tests async fiables. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `when-stuck` | Redirige vers la bonne technique de résolution de problème selon le type de blocage. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `collision-zone-thinking` | Force le rapprochement de concepts sans rapport pour révéler des propriétés émergentes. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `inversion-exercise` | Inverse les hypothèses de base pour révéler des contraintes cachées et d'autres approches. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `meta-pattern-recognition` | Repère les motifs qui apparaissent dans 3+ domaines pour trouver des principes universels. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `scale-game` | Teste aux extrêmes (1000x plus grand/petit, instantané/annuel) pour exposer des vérités fondamentales. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `simplification-cascades` | Cherche l'insight unique qui élimine plusieurs composants d'un coup. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `preserving-productive-tensions` | Reconnaît quand un désaccord révèle un contexte précieux, plutôt que de forcer une résolution prématurée. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `tracing-knowledge-lineages` | Comprend comment une idée a évolué dans le temps pour éviter de répéter d'anciens échecs. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `writing-skills` | TDD appliqué à la documentation de process — teste avec des sous-agents avant d'écrire un skill. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `testing-skills-with-subagents` | RED-GREEN-REFACTOR pour la documentation de process — vérifie qu'un skill résiste à la pression. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `gardening-skills-wiki` | Maintient la santé du wiki de skills — liens, naming, références croisées, couverture. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `sharing-skills` | Contribue un skill en amont via branche et PR vers le dépôt upstream. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `pulling-updates-from-skills-repository` | Synchronise la bibliothèque locale avec les changements upstream du dépôt superpowers-skills. | [obra/superpowers-skills](https://github.com/obra/superpowers-skills) |
| `karpathy-guidelines` | 4 principes comportementaux dérivés des observations d'Andrej Karpathy pour réduire les erreurs classiques des agents de code IA (réfléchir avant de coder, simplicité, changements chirurgicaux, critères de succès). | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) |

### Graphe de code / Review

📁 `importes/dev/graphe-de-code-review/.claude/skills/<nom>/`

> ⚠️ Ces skills nécessitent l'installation préalable du moteur **code-review-graph**.
> Skills [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) (Tirth Kanani), sous licence MIT.

| Skill | Description | Source |
|---------|-------------|--------|
| `build-graph` | Construction du graphe de connaissance. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `debug-issue` | Débogage guidé par le graphe. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `explore-codebase` | Exploration structurelle du code. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `refactor-safely` | Refactoring piloté par les dépendances. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `review-changes` | Revue d'impact des modifications. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `review-delta` | Revue des changements depuis le dernier commit. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |
| `review-pr` | Revue complète de Pull Request. | [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) |

**Installation du moteur :**

```bash
pip install code-review-graph
code-review-graph install
```

Sans cette étape, ces skills ne pourront pas fonctionner.

### Discipline de livraison

📁 `importes/dev/discipline-de-livraison/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `output-skill` | Force des livrables complets sans placeholders. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |

---

## 🔁 Autres / Transverse

Utile à tous les métiers utilisant Claude Code, pas seulement aux devs.

### Productivité tokens (caveman)

📁 `importes/autres-transverse/productivite-tokens-caveman/.claude/skills/<nom>/`

> Skills [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman), sous licence MIT.
> ⚠️ `cavecrew` référence 3 sous-agents (`agents/`) et `caveman-stats` référence
> un hook Claude Code (`hooks/`) — voir le `NOTES.md` de chacun pour les
> activer pleinement, une simple copie du dossier skill ne suffit pas.

| Skill | Description | Source |
|---------|-------------|--------|
| `caveman` | Mode de communication ultra-compressé (-65% de tokens en sortie), plusieurs niveaux d'intensité (lite/full/ultra). | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `caveman-commit` | Génère des messages de commit ultra-compressés au format Conventional Commits. | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `caveman-review` | Commentaires de revue de code ultra-compressés, un par ligne : emplacement, problème, correctif. | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `caveman-compress` | Compresse des fichiers mémoire (CLAUDE.md, todos, préférences) en format caveman pour économiser des tokens d'entrée. | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `caveman-help` | Carte de référence rapide de tous les modes/skills/commandes caveman. | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `caveman-stats` | Affiche l'usage réel de tokens et les économies estimées de la session (via un hook, pas de calcul par le modèle). | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `cavecrew` | Guide de délégation à 3 sous-agents caveman-compressés (investigator/builder/reviewer) pour économiser le contexte principal. | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |

### Recherche & productivité générale

📁 `importes/autres-transverse/recherche-productivite-generale/.claude/skills/<nom>/`

> Skills [Waza](https://github.com/tw93/Waza) (Tw93), sous licence MIT.

| Skill | Description | Source |
|---------|-------------|--------|
| `think` | Remise en question du problème et planification stratégique. | [tw93/Waza](https://github.com/tw93/Waza) |
| `read` | Lecture de pages web et PDF. | [tw93/Waza](https://github.com/tw93/Waza) |
| `learn` | Recherche structurée en plusieurs phases. | [tw93/Waza](https://github.com/tw93/Waza) |
| `write` | Réécriture de textes naturels et fluides. | [tw93/Waza](https://github.com/tw93/Waza) |

### Recherche & productivité (orientée dev)

📁 `importes/autres-transverse/recherche-productivite-orientee-dev/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `check` | Revue de livraison avant merge ou release. | [tw93/Waza](https://github.com/tw93/Waza) |
| `hunt` | Recherche systématique de causes racines. | [tw93/Waza](https://github.com/tw93/Waza) |
| `health` | Audit de santé d'agents IA. | [tw93/Waza](https://github.com/tw93/Waza) |

### Présentation & communication

📁 `importes/autres-transverse/presentation-communication/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `academic-pptx-skill` | Structure des présentations académiques et de recherche. | [Gabberflast/academic-pptx-skill](https://github.com/Gabberflast/academic-pptx-skill) |
| `speech-script` | Génération de scripts de discours naturels et fluides. | [sgharlow/claude-code-recipes](https://github.com/sgharlow/claude-code-recipes) — Recipe #40 |

### Découverte de skills (méta)

📁 `importes/autres-transverse/decouverte-de-skills-meta/.claude/skills/<nom>/`

| Skill | Description | Source |
|---------|-------------|--------|
| `find-skills` | Aide à découvrir et installer des skills de l'écosystème open (via `npx skills find`), avec vérification de la réputation/popularité avant recommandation. | [vercel-labs/skills](https://github.com/vercel-labs/skills) (officiel Vercel Labs) |

---

# 📦 Télécharger un skill

Chaque skill dispose de sa propre archive dans :

```text
archives/
```

Pour récupérer un seul skill :

1. Ouvre son lien `.zip`.
2. Clique sur **Download**.
3. Décompresse le contenu dans :

```text
.claude/skills/<nom-du-skill>/
```

Les archives sont régénérées à chaque mise à jour du skill.

---

# 📄 Profils `CLAUDE.md`

Ces profils visent à réduire la verbosité et le coût en tokens selon différents cas d'usage.

| Profil | Usage |
|----------|-----------|
| `CLAUDE.md` | Profil général recommandé. |
| `CLAUDE.agents.md` | Automatisation et agents. |
| `CLAUDE.analysis.md` | Analyse de données et reporting. |
| `CLAUDE.benchmark.md` | Benchmarks et tests. |
| `CLAUDE.coding.md` | Développement logiciel. |
| `CLAUDE.compressed.md` | Optimisation extrême des coûts en tokens. |

## Utilisation

Télécharge le profil souhaité puis renomme-le :

```text
CLAUDE.md
```

Ensuite, place-le à la racine du projet :

```text
MonProjet/
├── CLAUDE.md
├── src/
└── ...
```

> ⚠️ Un seul profil peut être actif à la fois.

---

# 📥 Installer un skill dans un autre projet

Copie uniquement le dossier du skill voulu (c'est le dossier `<nom-du-skill>/`, pas toute la catégorie) :

```text
# depuis cette bibliothèque
importes/design/ux-research/.claude/skills/uxr-synthese/

# vers ton projet
MonProjet/
└── .claude/
    └── skills/
        └── uxr-synthese/
```

Le chemin exact de chaque skill est indiqué (📁) sous le titre de sa catégorie, plus haut dans ce README.

Au prochain lancement de Claude Code, la commande :

```text
/<nom-du-skill>
```

sera disponible.

---

# 🌍 Installation globale

Pour rendre un skill disponible dans tous tes projets :

```text
~/.claude/skills/<nom-du-skill>/
```

Une seule installation suffit ensuite pour l'ensemble de ton environnement.

---

# ➕ Ajouter un skill à la bibliothèque

### 1. Choisir la place du skill, puis créer le dossier

Origine (`mes-skills/` ou `importes/`), métier (`design/`, `handoff-design-dev/`, `dev/`, `autres-transverse/`) et catégorie (un dossier existant, ou un nouveau) :

```text
<origine>/<métier>/<catégorie>/.claude/skills/<nom>/
```

### 2. Ajouter un fichier

```text
SKILL.md
```

avec un frontmatter contenant :

```yaml
name: mon-skill
description: Description du skill
```

### 3. Ajouter les ressources nécessaires

Ajoute les éventuels :

- scripts
- templates
- documents de référence
- assets

dans le même dossier.

### 4. Référencer le skill

Ajoute sa ligne dans le tableau de sa catégorie du README, dans le catalogue de `stack-ia` (`mes-skills/autres-transverse/productivite-perso/.claude/skills/stack-ia/references/catalog.md`), et crée son archive `archives/<nom>.zip` (le contenu du dossier, sans dossier parent).

### 5. Commit et push

Le skill est désormais intégré à la bibliothèque.

> ⚠️ Pour un skill que tu crées, garde le même nom pour le dossier et pour le champ `name:` : c'est le plus simple.
>
> **Vérifié** (documentation de Claude Code et test avec le CLI) : quand les deux diffèrent, le champ `name:` donne la commande affichée dans le menu `/`, et **le nom du dossier fonctionne toujours en repli**. 42 skills importés sont dans ce cas, conservés tels quels pour rester fidèles à leur source : par exemple le dossier `taste-skill` a pour nom `design-taste-frontend`, et les deux `/taste-skill` et `/design-taste-frontend` marchent. Les noms du type `Root Cause Tracing` (31 skills Superpowers) sont plus pénibles à saisir : utilise alors le nom du dossier, `/root-cause-tracing`. Aucune collision entre ces noms dans la bibliothèque.

---

# 📊 En un coup d'œil

- ✅ Skills réutilisables entre projets
- ✅ Archives ZIP individuelles
- ✅ Profils `CLAUDE.md` prêts à l'emploi
- ✅ Documentation des licences et origines
- ✅ Installation locale ou globale
- ✅ Bibliothèque centralisée et pérenne

---

> **Une organisation simple : un dépôt, tous les skills, tous les profils, réutilisables partout. 🚀**
