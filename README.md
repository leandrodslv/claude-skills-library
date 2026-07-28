# Bibliothèque de skills

C'est mon espace personnel pour Claude Code — un dépôt unique où je range les
skills et les profils `CLAUDE.md` que j'utilise ou que je construis, pour ne
pas les perdre d'un projet à l'autre et pouvoir les réutiliser n'importe où.

Deux types de contenu, pas la même mécanique :

- **Skills** (`.claude/skills/<nom>/SKILL.md`) — invocables via `/<nom>` dans
  Claude Code. C'est la convention standard : n'importe quel projet qui
  embarque ce dossier rend le skill disponible.
- **Profils `CLAUDE.md`** (`claude-md-profiles/`) — pas des skills, pas de
  commande. Ce sont des fichiers à copier **à la racine** d'un projet (ou dans
  `~/.claude/CLAUDE.md` pour un effet global) : Claude Code les lit
  automatiquement à chaque message, sans rien invoquer.

---

## Skills dans la bibliothèque

| Skill | Ce qu'il fait | Télécharger |
|---|---|---|
| [`test-agent`](.claude/skills/test-agent/SKILL.md) | Banc d'essai pour agent IA. Analyse en profondeur le prompt d'un agent visé, se spécialise pour lui en générant des scénarios de test taillés sur mesure, le lance pour de vrai dans un bac à sable (Claude Code, Gemini CLI, ou toute commande), dialogue avec lui tour par tour, et produit un rapport ✅ / ❌ / recommandations plus un tableau de bord local. Inclut un exemple complet de bout en bout (analyse, profil, 8 scénarios) construit sur l'agent ECHO. | [.zip](archives/test-agent.zip) |
| [`academic-pptx-skill`](.claude/skills/academic-pptx-skill/SKILL.md) | Structure et contenu de présentations académiques (colloques, soutenances, comités de financement, séminaires) — gouverne le fond et l'organisation, pas la mise en forme technique du `.pptx`. | [.zip](archives/academic-pptx-skill.zip) |
| [`speech-script`](.claude/skills/speech-script/SKILL.md) | Transforme des idées ou un plan en script de discours narratif, prêt à être prononcé — pour présentations orales, conférences, discours d'entreprise. | [.zip](archives/speech-script.zip) |
| [`ui-ux-pro-max`](.claude/skills/ui-ux-pro-max/SKILL.md) | Base de données consultable d'intelligence UI/UX : 84 styles, 192 palettes, 74 associations de polices, 98 règles UX, 104 icônes, presets d'animation GSAP, sur 22 stacks techniques. Génère un design system complet et argumenté à partir d'une description de produit. |  [.zip](archives/ui-ux-pro-max.zip) |
| [`banner-design`](.claude/skills/banner-design/SKILL.md) | Conception de bannières (réseaux sociaux, pubs, hero de site, print) avec plusieurs pistes de direction artistique et visuels générés par IA. | [.zip](archives/banner-design.zip) |
| [`brand`](.claude/skills/brand/SKILL.md) | Voix de marque, identité visuelle, cadres de messages, cohérence de marque sur les contenus et assets marketing. | [.zip](archives/brand.zip) |
| [`design`](.claude/skills/design/SKILL.md) | Skill de design large : identité de marque, tokens, logos, kit d'identité corporate, présentations HTML, bannières, icônes, visuels sociaux. | [.zip](archives/design.zip) |
| [`design-system`](.claude/skills/design-system/SKILL.md) | Architecture de tokens à trois couches (primitif → sémantique → composant), spécifications de composants, génération stratégique de slides. | [.zip](archives/design-system.zip) |
| [`slides`](.claude/skills/slides/SKILL.md) | Présentations HTML stratégiques avec Chart.js, tokens de design, mise en page responsive, formules de copywriting. | [.zip](archives/slides.zip) |
| [`ui-styling`](.claude/skills/ui-styling/SKILL.md) | Interfaces accessibles avec shadcn/ui (Radix + Tailwind), thèmes, dark mode, composants accessibles (dialogs, formulaires, tableaux). | [.zip](archives/ui-styling.zip) |
| [`impeccable`](.claude/skills/impeccable/SKILL.md) | Guidance de design frontend pour agents IA : 23 commandes (`polish`, `audit`, `critique`, `distill`, `animate`, `bolder`, `quieter`…), itération live dans le navigateur, 60 règles de détection déterministes contre les tics visuels génériques des IA (Inter partout, dégradés violet-bleu, cartes imbriquées…). | [.zip](archives/impeccable.zip) |
| [`think`](.claude/skills/think/SKILL.md) | Avant de construire quoi que ce soit : challenge le problème, presse-teste la conception, produit un plan complet qu'un autre agent peut implémenter. | [.zip](archives/think.zip) |
| [`ui`](.claude/skills/ui/SKILL.md) | Interfaces frontend distinctives, avec itération esthétique pilotée par capture d'écran — direction assumée plutôt que défauts génériques. | [.zip](archives/ui.zip) |
| [`check`](.claude/skills/check/SKILL.md) | Revue de diff après une tâche, avant merge ou release : contraintes propres au projet, suivi de release/publish/push, vérification par preuves. | [.zip](archives/check.zip) |
| [`hunt`](.claude/skills/hunt/SKILL.md) | Debug systématique de bug ou régression — cause racine confirmée avant tout correctif, surtout quand quelque chose fonctionnait avant. | [.zip](archives/hunt.zip) |
| [`write`](.claude/skills/write/SKILL.md) | Réécrit la prose pour sonner naturel en français comme en anglais (chinois/anglais dans la version source), coupe les formulations rigides. | [.zip](archives/write.zip) |
| [`learn`](.claude/skills/learn/SKILL.md) | Workflow de recherche en 6 phases pour un domaine inconnu : collecter, digérer, structurer, compléter, affiner, relire et publier. | [.zip](archives/learn.zip) |
| [`read`](.claude/skills/read/SKILL.md) | Lit URLs et PDF avec routage spécifique par plateforme — résumé concis en lecture simple, sortie Markdown si conversion/citation/sauvegarde demandée. | [.zip](archives/read.zip) |
| [`health`](.claude/skills/health/SKILL.md) | Audit de santé d'agent IA : vérifie Codex, Claude Code, les instructions de projet, la sortie du vérificateur, la maintenabilité — avec un passage résumé avant l'inspection profonde. | [.zip](archives/health.zip) |
| [`build-graph`](.claude/skills/build-graph/SKILL.md) ⚠️ | Construit ou met à jour le graphe de connaissance du code (SQLite, `.code-review-graph/graph.db`) — préalable aux 6 autres skills de ce groupe. | [.zip](archives/build-graph.zip) |
| [`debug-issue`](.claude/skills/debug-issue/SKILL.md) ⚠️ | Debug systématique via navigation du code par le graphe de dépendances. | [.zip](archives/debug-issue.zip) |
| [`explore-codebase`](.claude/skills/explore-codebase/SKILL.md) ⚠️ | Navigue et comprend la structure d'une codebase via le graphe de connaissance. | [.zip](archives/explore-codebase.zip) |
| [`refactor-safely`](.claude/skills/refactor-safely/SKILL.md) ⚠️ | Planifie et exécute un refactoring sûr via analyse de dépendances. | [.zip](archives/refactor-safely.zip) |
| [`review-changes`](.claude/skills/review-changes/SKILL.md) ⚠️ | Revue de code structurée via détection de changements et analyse d'impact. | [.zip](archives/review-changes.zip) |
| [`review-delta`](.claude/skills/review-delta/SKILL.md) ⚠️ | Revue des seuls changements depuis le dernier commit, économe en tokens, avec détection automatique du rayon d'impact. | [.zip](archives/review-delta.zip) |
| [`review-pr`](.claude/skills/review-pr/SKILL.md) ⚠️ | Revue d'une PR ou d'un diff de branche avec le contexte structurel complet du graphe, analyse du rayon d'impact incluse. | [.zip](archives/review-pr.zip) |

> ⚠️ **Ces 7 skills (`build-graph` à `review-pr`) ne fonctionnent pas seuls.**
> Contrairement à tous les autres skills de cette bibliothèque, ils ne
> contiennent que des instructions qui appellent des **outils MCP**
> (`list_graph_stats_tool`, `build_or_update_graph_tool`…) — aucun script,
> aucune donnée embarquée. Ces outils sont fournis par un serveur MCP externe,
> le moteur d'analyse Python `code-review-graph`, à installer et configurer
> **avant** que ces skills ne servent à quoi que ce soit :
> ```bash
> pip install code-review-graph
> code-review-graph install   # detecte l'outil IA et configure le MCP
> ```
> Sans cette étape, copier ces dossiers ne fait rien — les outils qu'ils
> appellent n'existent pas.

**Les 7 skills `build-graph` à `review-pr` viennent d'un dépôt tiers** :
[tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)
(licence MIT, incluse dans chacun de ces dossiers via `LICENSE.txt`).

**Les 8 skills `think` à `health` viennent d'un dépôt tiers** :
[tw93/Waza](https://github.com/tw93/Waza) (licence MIT, incluse dans chacun de
ces dossiers via `LICENSE.txt`). Aucun correctif nécessaire à l'import :
chaque skill est autonome, sans référence croisée vers un autre skill du
même dépôt ni variable d'environnement de plugin. Ils sont conçus pour
s'enchaîner en flux de travail (`think` → `check`, `hunt` → `check`, `read` →
`learn` → `write`…), mais chaque transition reste une étape manuelle
déclenchée par le pilote — aucune dépendance technique entre eux.

**`impeccable` vient d'un dépôt tiers** :
[pbakaus/impeccable](https://github.com/pbakaus/impeccable) (licence Apache
2.0, incluse via `LICENSE.txt` ; `NOTICE.md` copié aussi — deux fichiers de
référence de ce skill, `reference/ios.md` et `reference/android.md`, sont
eux-mêmes distillés d'un troisième projet sous licence MIT, crédité dans
`NOTICE.md`). Aucun correctif nécessaire à l'import : les chemins sont déjà
écrits en relatif au projet, sans dépendre d'une variable d'environnement de
plugin. Un script fait référence à `react` comme dépendance externe — sans
incidence hors d'un projet React qui l'a déjà dans son `node_modules`.

**Les 7 skills `ui-ux-pro-max` à `ui-styling` viennent d'un dépôt tiers** :
[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(licence MIT, incluse dans chacun de ces dossiers via `LICENSE.txt`). Un
correctif leur a été apporté à l'import : leur `SKILL.md` appelait son script
via `${CLAUDE_PLUGIN_ROOT}`, une variable que Claude Code ne définit que pour
une installation via `/plugin install` — remplacée par un chemin relatif qui
fonctionne aussi en copie manuelle (le mode d'installation de cette
bibliothèque). Le reste du code (`core.py`) résolvait déjà ses données via son
propre chemin de fichier, sans dépendre de cette variable.

À savoir : `banner-design` mentionne dans sa description des skills
compagnons (`frontend-design`, `ai-artist`, `ai-multimodal`) qui ne font
**pas** partie de ce dépôt tiers et ne sont donc pas dans cette bibliothèque —
il fonctionnera, mais sans ces capacités additionnelles.

---

## Télécharger un seul skill

Chaque skill a sa propre archive dans `archives/` — pas besoin de cloner tout
le dépôt pour en récupérer un seul :

1. Clique sur le lien `.zip` de la table ci-dessus (ou ouvre directement
   `archives/<nom-du-skill>.zip` sur GitHub).
2. Bouton **Download** (ou **⋯ → Download**) sur la page du fichier.
3. Dézippe dans `.claude/skills/<nom-du-skill>/` du projet où tu veux
   l'utiliser — le zip contient directement `SKILL.md` et les fichiers
   annexes à la racine, sans dossier parasite au-dessus.

Ces archives sont régénérées à chaque modification d'un skill : si le
contenu d'un dossier change, retélécharge son `.zip` pour rester à jour.

---

## Profils `CLAUDE.md`

Des fichiers `CLAUDE.md` prêts à l'emploi pour réduire la verbosité et le
coût en tokens de sortie — à déposer tels quels à la racine d'un projet.
**Pas des skills** : rien à installer dans `.claude/skills/`, aucune commande
`/`, Claude Code les charge automatiquement dès qu'ils sont présents.
Source : [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient)
(licence MIT, `LICENSE.txt` inclus).

| Profil | Pour quoi | Fichier |
|---|---|---|
| `CLAUDE.md` (principal) | Profil universel — le point de départ recommandé | [ouvrir](claude-md-profiles/CLAUDE.md) |
| `CLAUDE.agents.md` | Pipelines d'automatisation, systèmes multi-agents, bots, tâches planifiées | [ouvrir](claude-md-profiles/CLAUDE.agents.md) |
| `CLAUDE.analysis.md` | Analyse de données, recherche, analyse financière, reporting | [ouvrir](claude-md-profiles/CLAUDE.analysis.md) |
| `CLAUDE.benchmark.md` | Benchmarks code — minimise l'overhead en préservant le taux de réussite | [ouvrir](claude-md-profiles/CLAUDE.benchmark.md) |
| `CLAUDE.coding.md` | Projets de dev, revue de code, debug, refactoring | [ouvrir](claude-md-profiles/CLAUDE.coding.md) |
| `CLAUDE.compressed.md` | Workloads à fort volume de sortie où le coût en tokens domine (mesuré : -62% Opus, -32% Sonnet, -22% Haiku vs baseline) | [ouvrir](claude-md-profiles/CLAUDE.compressed.md) |

**Utilisation** : télécharge le fichier voulu (bouton Download sur sa page
GitHub) et dépose-le à la racine du projet cible sous le nom `CLAUDE.md` —
un seul profil actif à la fois, ils ne se combinent pas. N'en mets un que sur
des workflows à fort volume de sortie (pipelines, automatisation) : sur des
échanges courts et ponctuels, le fichier coûte plus de tokens en entrée qu'il
n'en économise en sortie — l'auteur le dit lui-même dans son README.

Le dépôt source contient aussi 3 dossiers d'expérimentation versionnés
(`J/K/M-drona23-v5/v6/v8`, variantes de test du benchmark) volontairement
laissés de côté ici — pas des profils prêts à l'emploi.

## Utiliser un skill d'ici dans un autre projet

Copie le dossier du skill dans le nouveau projet :

```
MonProjet/
└── .claude/
    └── skills/
        └── <nom-du-skill>/    ← copié depuis ce dépôt
```

Claude Code le découvre automatiquement au lancement suivant — la commande
`/<nom-du-skill>` devient disponible.

Pour le rendre disponible **partout**, sans le copier projet par projet, place-le
plutôt dans le dossier utilisateur global :

```
~/.claude/skills/<nom-du-skill>/
```

## Ajouter un skill à la bibliothèque

1. Crée `.claude/skills/<nom>/SKILL.md` avec un bloc frontmatter `name` +
   `description` en tête de fichier.
2. Ajoute les fichiers annexes dont le skill a besoin (scripts, gabarits,
   références) dans le même dossier.
3. Commit et push.

Le nom du dossier **doit** être exactement celui utilisé dans `name:` — c'est
lui qui détermine la commande slash.
