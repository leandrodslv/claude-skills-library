# 📚 Bibliothèque de Skills

> Bibliothèque personnelle de skills Claude Code — design/UX, branding, animation GSAP, automatisation n8n, revue de code, économie de tokens, et frameworks de référence (BMAD), prêts à installer.

> Mon espace personnel pour **Claude Code** : un dépôt unique où je centralise les skills et profils `CLAUDE.md` que j'utilise ou développe.
>
> **Objectif :** ne rien perdre entre les projets, partager facilement des composants réutilisables et disposer d'une bibliothèque prête à l'emploi partout.

---

# 🗂️ Trois types de ressources

Cette bibliothèque contient trois catégories distinctes.

## ⚡ Skills

**Emplacement :**

```text
.claude/skills/<nom>/SKILL.md
```

Les skills sont des commandes directement utilisables dans Claude Code :

```text
/<nom-du-skill>
```

Dès qu'un projet contient ce dossier, Claude Code détecte automatiquement le skill et le rend disponible.

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

## 🧠 Agents & Tests

| Skill | Description | Source |
|---------|-------------|--------|
| `test-agent` | Framework de test pour agents IA avec génération automatique de scénarios, exécution sandboxée et rapport détaillé. | Original (aucun dépôt public identifié) |
| `context-keeper` | Crée, met à jour et restaure un fichier de contexte maître capturant l'état de tous les projets en cours pour reprendre instantanément dans n'importe quelle conversation. | Original (skill personnel) |
| `brainstorming` | Facilitation de sessions de brainstorming/idéation (HMW, SCAMPER, Crazy 8s, brainwriting...), sélection automatique de la méthode adaptée. | Original (skill personnel) |
| `naming` | Naming créatif pour projets, artistes IA/musicaux, agents IA et workflows — shortlist commentée avec taglines. | Original (skill personnel) |

---

## 🔎 Découverte de skills

| Skill | Description | Source |
|---------|-------------|--------|
| `find-skills` | Aide à découvrir et installer des skills de l'écosystème open (via `npx skills find`), avec vérification de la réputation/popularité avant recommandation. | [vercel-labs/skills](https://github.com/vercel-labs/skills) (officiel Vercel Labs) |
| `frontend-design` | Design frontend distinctif et haut de gamme (direction artistique, typographie, choix qui évitent l'esthétique générique IA). | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |
| `web-design-guidelines` | Revue de code UI selon les Web Interface Guidelines (accessibilité, performance, UX — 100+ règles). | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (officiel Vercel Labs) |

---

## 🧭 Composition de stack

| Skill | Description | Source |
|---------|-------------|--------|
| `stack-ia` | Compose une "stack" de skills à partir de **cette bibliothèque** (pas de l'écosystème externe, voir `find-skills` pour ça) pour un projet donné — appli, site, logiciel, workflow n8n, branding... Analyse le projet, consulte le catalogue interne (`references/catalog.md`), et recommande un sous-ensemble pertinent organisé par phase. | Original (skill personnel) |

---

## 🪨 Caveman (économie de tokens)

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

---

## 🎤 Présentation & Communication

| Skill | Description | Source |
|---------|-------------|--------|
| `academic-pptx-skill` | Structure des présentations académiques et de recherche. | [Gabberflast/academic-pptx-skill](https://github.com/Gabberflast/academic-pptx-skill) |
| `speech-script` | Génération de scripts de discours naturels et fluides. | [sgharlow/claude-code-recipes](https://github.com/sgharlow/claude-code-recipes) — Recipe #40 |
| `slides` | Présentations HTML stratégiques avec design system intégré. | ClaudeKit Marketing Kit (produit payant, [docs](https://docs.claudekit.cc/docs/marketing/skills/) — pas de dépôt public) |

---

## 🎨 Design & Branding

| Skill | Description | Source |
|---------|-------------|--------|
| `brand` | Positionnement, voix et cohérence de marque. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `design` | Branding complet : logos, identité, assets marketing. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `design-system` | Architecture de design systems et bibliothèques de composants. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `brandkit` | Génération de kits de marque complets. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `banner-design` | Création de bannières marketing et visuels promotionnels. | ClaudeKit Marketing Kit (payant, pas de dépôt public) |
| `canvas-design` | Production d'œuvres visuelles, affiches et posters. | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |
| `brand-guidelines` | Application de la charte visuelle officielle Anthropic. | [anthropics/skills](https://github.com/anthropics/skills) (officiel Anthropic) |
| `notion-template-designer` | Crée des templates Notion visuellement soignés (dashboards, trackers, portfolios...) via recherche d'inspiration et le MCP Notion. | Original (skill personnel) |

---

## 💎 UI / UX

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

---

## 🖼️ Génération visuelle

| Skill | Description | Source |
|---------|-------------|--------|
| `imagegen-frontend-web` | Génération de maquettes web de référence. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `imagegen-frontend-mobile` | Génération de références mobiles iOS/Android. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `image-to-code-skill` | Pipeline image → analyse → implémentation frontend. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |

---

## 💻 Développement

| Skill | Description | Source |
|---------|-------------|--------|
| `figma-design-to-code` | Transformation rigoureuse de designs Figma en composants réels. | [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide) (officiel Figma) |
| `stitch-skill` | Workflow compatible Google Stitch. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `output-skill` | Force des livrables complets sans placeholders. | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) |
| `figma-to-code` | Convertit une maquette Figma en code HTML/CSS, React ou Vue pixel-perfect. | Original (skill personnel) |
| `html-to-figma` | Convertit des fichiers HTML/CSS en maquette Figma pixel-perfect via le MCP Figma. | Original (skill personnel) |

---

## ♿ Accessibilité

| Skill | Description | Source |
|---------|-------------|--------|
| `color-contrast-checker` | Analyse le contraste de couleurs d'une image (maquette, capture d'écran) et produit un rapport d'accessibilité WCAG/RGAA. | Original (skill personnel) |

---

## 🧠 Méthodologie & discipline dev (Superpowers)

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

---

## 🔄 Automatisation (n8n)

> Skills [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) (Romuald Członkowski, auteur de [n8n-mcp](https://github.com/czlonkowski/n8n-mcp)), sous licence MIT.
> ⚠️ Pensés pour accompagner le serveur MCP **n8n-mcp** — le contenu reste
> utile seul, mais l'usage complet (validation live, recherche de nœuds)
> nécessite ce MCP configuré dans le projet cible. Voir le `NOTES.md` de
> `using-n8n-mcp-skills`.

| Skill | Description | Source |
|---------|-------------|--------|
| `using-n8n-mcp-skills` | Skill routeur : oriente vers le bon skill spécialiste pour toute tâche n8n via le MCP n8n-mcp. | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-mcp-tools-expert` | Guide d'utilisation des outils MCP n8n-mcp (recherche de nœuds, validation, credentials, audit de sécurité). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-workflow-patterns` | Patterns d'architecture de workflows éprouvés (webhook, API, DB, agents IA, batch, tâches planifiées). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-expression-syntax` | Syntaxe des expressions n8n `{{ }}` et pièges classiques (structure des données webhook). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-node-configuration` | Configuration des nœuds selon l'opération (champs requis, displayOptions, édition chirurgicale). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-code-javascript` | Écrire du JavaScript dans les nœuds Code n8n (syntaxe $input/$json, dates, patterns de production). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-code-python` | Écrire du Python dans les nœuds Code n8n (limitations, bibliothèque standard disponible). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-code-tool` | Écrire le Code Tool appelable par un agent IA (contrat d'entrée/sortie différent du nœud Code classique). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-agents` | Concevoir des agents IA n8n (AI Agent, LLM chain, mémoire, RAG, sorties structurées, human-in-the-loop). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-error-handling` | Gestion d'erreurs robuste (branches d'erreur, retries, Error Trigger, codes de réponse webhook). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-validation-expert` | Interprétation des erreurs/avertissements de validation, faux positifs, auto-fix. | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-binary-and-data` | Gestion des fichiers/données binaires (images, PDF, base64, vision multimodale). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-subworkflows` | Construction de sous-workflows réutilisables et composables. | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-multi-instance` | Gestion de plusieurs instances n8n (prod/staging, plusieurs clients) via le MCP. | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |
| `n8n-self-hosting` | Déploiement d'un n8n auto-hébergé en production (Docker Compose, Caddy, HTTPS, mode queue). | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) |

---

## 🔍 Analyse, Recherche & Productivité

> Skills [Waza](https://github.com/tw93/Waza) (Tw93), sous licence MIT.

| Skill | Description | Source |
|---------|-------------|--------|
| `think` | Remise en question du problème et planification stratégique. | [tw93/Waza](https://github.com/tw93/Waza) |
| `read` | Lecture de pages web et PDF. | [tw93/Waza](https://github.com/tw93/Waza) |
| `learn` | Recherche structurée en plusieurs phases. | [tw93/Waza](https://github.com/tw93/Waza) |
| `write` | Réécriture de textes naturels et fluides. | [tw93/Waza](https://github.com/tw93/Waza) |
| `check` | Revue de livraison avant merge ou release. | [tw93/Waza](https://github.com/tw93/Waza) |
| `hunt` | Recherche systématique de causes racines. | [tw93/Waza](https://github.com/tw93/Waza) |
| `health` | Audit de santé d'agents IA. | [tw93/Waza](https://github.com/tw93/Waza) |

---

## 📥 Conversion de fichiers (entrants → Markdown)

| Skill | Description | Source |
|---------|-------------|--------|
| `to-markdown` | Convertit n'importe quel fichier — Word, PowerPoint, Excel, OpenDocument, RTF, PDF (texte et scans, OCR), SVG et diagrammes (draw.io, Graphviz → Mermaid), HTML, EPUB, e-mails, notebooks, JSON/XML/YAML, images, archives, dossiers entiers — en Markdown fiable pour l'IA. Contrôle qualité automatique, moteurs externes optionnels (LibreOffice, poppler, tesseract, pandoc…) testés avant usage, lecture visuelle guidée pour ce qu'un script ne sait pas lire. 100 % local. | Original (skill personnel) |
| `prd-from-sources` | Rédige un PRD au format BMAD officiel à partir de documents déjà convertis en Markdown : chaque exigence cite sa source, un vérificateur (`check_prd.py`) contrôle sources, orphelins et références, rien n'est inventé. | Skill original (suite de `to-markdown`) |

---

## 🎬 Animation (GSAP)

> Skills officiels [GSAP](https://github.com/greensock/gsap-skills) (GreenSock), sous licence MIT.

| Skill | Description | Source |
|---------|-------------|--------|
| `gsap-core` | API de base — `gsap.to()`, `from()`, `fromTo()`, easing, stagger, `matchMedia()`. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-timeline` | Séquencement d'animations avec `gsap.timeline()`, paramètre de position, imbrication. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-react` | Intégration React/Next.js — hook `useGSAP`, refs, `gsap.context()`, cleanup. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-frameworks` | Intégration Vue, Nuxt, Svelte, SvelteKit — cycle de vie, cleanup au démontage. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-scrolltrigger` | Animations liées au scroll — pinning, scrub, triggers, parallax. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-plugins` | Plugins GSAP — ScrollToPlugin, Flip, Draggable, SplitText, CustomEase, etc. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-utils` | Utilitaires `gsap.utils` — clamp, mapRange, random, snap, toArray, wrap. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |
| `gsap-performance` | Optimisation des animations — transforms, will-change, 60fps. | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) |

---

## 🌐 Graphe de connaissance du code

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

### Installation

```bash
pip install code-review-graph
code-review-graph install
```

Sans cette étape, ces skills ne pourront pas fonctionner.

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

Copie simplement son dossier :

```text
MonProjet/
└── .claude/
    └── skills/
        └── <nom-du-skill>/
```

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

### 1. Créer le dossier

```text
.claude/skills/<nom>/
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

### 4. Commit et push

Le skill est désormais intégré à la bibliothèque.

> ⚠️ Le nom du dossier doit être strictement identique à la valeur du champ `name:`. C'est ce nom qui détermine la commande `/mon-skill`.

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
