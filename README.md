# 📚 Bibliothèque de Skills

> Mon espace personnel pour **Claude Code** : un dépôt unique où je centralise les skills et profils `CLAUDE.md` que j'utilise ou développe.
>
> **Objectif :** ne rien perdre entre les projets, partager facilement des composants réutilisables et disposer d'une bibliothèque prête à l'emploi partout.

---

# 🗂️ Deux types de ressources

Cette bibliothèque contient deux catégories distinctes.

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

## 🎬 Animation (GSAP)

> Skills officiels [GSAP](https://github.com/greensock/gsap-skills) (GreenSock), sous licence MIT.

| Skill | Description |
|---------|-------------|
| `gsap-core` | API de base — `gsap.to()`, `from()`, `fromTo()`, easing, stagger, `matchMedia()`. |
| `gsap-timeline` | Séquencement d'animations avec `gsap.timeline()`, paramètre de position, imbrication. |
| `gsap-react` | Intégration React/Next.js — hook `useGSAP`, refs, `gsap.context()`, cleanup. |
| `gsap-frameworks` | Intégration Vue, Nuxt, Svelte, SvelteKit — cycle de vie, cleanup au démontage. |
| `gsap-scrolltrigger` | Animations liées au scroll — pinning, scrub, triggers, parallax. |
| `gsap-plugins` | Plugins GSAP — ScrollToPlugin, Flip, Draggable, SplitText, CustomEase, etc. |
| `gsap-utils` | Utilitaires `gsap.utils` — clamp, mapRange, random, snap, toArray, wrap. |
| `gsap-performance` | Optimisation des animations — transforms, will-change, 60fps. |

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
