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

## 🧠 Agents & Tests

| Skill | Description |
|---------|-------------|
| `test-agent` | Framework de test pour agents IA avec génération automatique de scénarios, exécution sandboxée et rapport détaillé. |

---

## 🎤 Présentation & Communication

| Skill | Description |
|---------|-------------|
| `academic-pptx-skill` | Structure des présentations académiques et de recherche. |
| `speech-script` | Génération de scripts de discours naturels et fluides. |
| `slides` | Présentations HTML stratégiques avec design system intégré. |

---

## 🎨 Design & Branding

| Skill | Description |
|---------|-------------|
| `brand` | Positionnement, voix et cohérence de marque. |
| `design` | Branding complet : logos, identité, assets marketing. |
| `design-system` | Architecture de design systems et bibliothèques de composants. |
| `brandkit` | Génération de kits de marque complets. |
| `banner-design` | Création de bannières marketing et visuels promotionnels. |
| `canvas-design` | Production d'œuvres visuelles, affiches et posters. |
| `brand-guidelines` | Application de la charte visuelle officielle Anthropic. |

---

## 💎 UI / UX

| Skill | Description |
|---------|-------------|
| `ui-ux-pro-max` | Base de connaissances massive UI/UX (styles, palettes, typographies, règles UX...). |
| `ui-styling` | Interfaces accessibles avec shadcn/ui et Tailwind. |
| `ui` | Création d'interfaces distinctives orientées direction artistique. |
| `soft-skill` | UI premium, épurée et haut de gamme. |
| `minimalist-skill` | Design éditorial inspiré de Notion et Linear. |
| `brutalist-skill` | Interfaces radicales à inspiration brutaliste. |
| `taste-skill` | Anti-slop frontend pour IA. |
| `gpt-tasteskill` | Variante optimisée pour GPT/Codex. |
| `redesign-skill` | Audit et amélioration d'interfaces existantes. |
| `impeccable` | Ensemble de commandes de critique, polish et amélioration frontend. |

---

## 🖼️ Génération visuelle

| Skill | Description |
|---------|-------------|
| `imagegen-frontend-web` | Génération de maquettes web de référence. |
| `imagegen-frontend-mobile` | Génération de références mobiles iOS/Android. |
| `image-to-code-skill` | Pipeline image → analyse → implémentation frontend. |

---

## 💻 Développement

| Skill | Description |
|---------|-------------|
| `figma-design-to-code` | Transformation rigoureuse de designs Figma en composants réels. |
| `stitch-skill` | Workflow compatible Google Stitch. |
| `output-skill` | Force des livrables complets sans placeholders. |

---

## 🔍 Analyse, Recherche & Productivité

| Skill | Description |
|---------|-------------|
| `think` | Remise en question du problème et planification stratégique. |
| `read` | Lecture de pages web et PDF. |
| `learn` | Recherche structurée en plusieurs phases. |
| `write` | Réécriture de textes naturels et fluides. |
| `check` | Revue de livraison avant merge ou release. |
| `hunt` | Recherche systématique de causes racines. |
| `health` | Audit de santé d'agents IA. |

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

| Skill | Description |
|---------|-------------|
| `build-graph` | Construction du graphe de connaissance. |
| `debug-issue` | Débogage guidé par le graphe. |
| `explore-codebase` | Exploration structurelle du code. |
| `refactor-safely` | Refactoring piloté par les dépendances. |
| `review-changes` | Revue d'impact des modifications. |
| `review-delta` | Revue des changements depuis le dernier commit. |
| `review-pr` | Revue complète de Pull Request. |

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
