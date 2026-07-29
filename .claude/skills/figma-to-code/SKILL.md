---
name: figma-to-code
description: Convertit une maquette Figma en code HTML/CSS, React ou Vue pixel-perfect. Utilise ce skill dès que l'utilisateur partage un lien Figma et veut du code. Déclencher pour : "convertis ma maquette Figma en code", "génère le HTML de ce Figma", "transforme ce design en React", "code ce composant Figma", "exporte en HTML", "traduis ma maquette en code", "figma to code", "figma to html", "figma to react", "implémente ce design", "code cette maquette", "donne-moi le code de ce Figma". Toujours utiliser ce skill plutôt qu'une réponse générique dès qu'un lien Figma est fourni et que l'utilisateur veut du code en sortie.
---

# Figma → Code (Pixel-Perfect)

Convertit n'importe quelle frame ou composant Figma en code production-ready via le MCP Figma (`get_design_context`). Supporte HTML/CSS vanilla, React + Tailwind, React + CSS Modules, Vue.

---

## Étape 0 — Prérequis

Avant de commencer, s'assurer d'avoir :
1. **Un lien Figma** avec un `node-id` dans l'URL
   - Format : `https://www.figma.com/design/FILEKEY/nom?node-id=123-456`
   - Si pas de `node-id` → appeler `get_metadata` pour lister les pages et demander à l'utilisateur de sélectionner un nœud
2. **Le format de sortie souhaité** — si non précisé, demander :
   - HTML/CSS vanilla (défaut)
   - React + Tailwind
   - React + CSS Modules
   - Vue 3 + CSS

Si le lien est fourni sans `node-id`, utiliser `get_metadata` pour explorer la structure et guider l'utilisateur.

---

## Étape 1 — Extraire le contexte Figma

### Appel principal
```
Figma:get_design_context({
  fileKey: "<extrait de l'URL>",
  nodeId: "<extrait du node-id>",
  clientFrameworks: "html,css" | "react" | "vue",
  clientLanguages: "html,css" | "javascript,typescript"
})
```

Cet appel retourne :
- **`code`** : code de référence généré par Figma (point de départ, à adapter)
- **`screenshot`** : image du design (vérité visuelle — s'y référer en priorité)
- **`metadata`** : structure des nœuds, propriétés, dimensions

### Si les variables de design sont importantes
```
Figma:get_variable_defs({
  fileKey: "<fileKey>",
  nodeId: "<nodeId>"
})
```
Retourne les tokens de design (couleurs, espacements, typographie) → les transformer en variables CSS ou tokens JS.

### Si la structure est complexe
```
Figma:get_metadata({
  fileKey: "<fileKey>",
  nodeId: "<nodeId>"
})
```
Pour obtenir l'arbre des nœuds enfants et leur hiérarchie.

---

## Étape 2 — Analyser le design

À partir du screenshot et des métadonnées, identifier :

### Structure visuelle
- Quelles sont les **sections principales** ? (header, hero, cards, footer...)
- Quel est le **layout** de chaque section ? (flex row, flex column, grille...)
- Y a-t-il des **composants réutilisables** ? (boutons, badges, avatars...)

### Propriétés CSS à extraire
| Propriété Figma | CSS équivalent |
|-----------------|----------------|
| Fill (solid) | `background-color` / `color` |
| Fill (gradient) | `background: linear-gradient(...)` |
| Font name + size + weight | `font-family` + `font-size` + `font-weight` |
| Line height | `line-height` |
| Letter spacing | `letter-spacing` |
| Corner radius | `border-radius` |
| Stroke | `border` |
| Drop shadow | `box-shadow` |
| Auto layout (horizontal) | `display: flex; flex-direction: row` |
| Auto layout (vertical) | `display: flex; flex-direction: column` |
| Gap | `gap` |
| Padding | `padding` |
| Opacity | `opacity` |
| Blend mode | `mix-blend-mode` |

### Couleurs
Extraire en hex depuis les fills Figma (r, g, b sont en 0–1 → multiplier par 255 → convertir en hex).

---

## Étape 3 — Générer le code

### FORMAT : HTML/CSS Vanilla

Structure à respecter :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Nom du design]</title>
  <!-- Importer les fonts Google utilisées dans Figma -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=[Font]&display=swap" rel="stylesheet">
  <style>
    /* Variables CSS depuis les tokens Figma */
    :root {
      --color-primary: #[hex];
      --color-bg: #[hex];
      --font-heading: '[FontFamily]', sans-serif;
      --font-body: '[FontFamily]', sans-serif;
      --radius-md: [val]px;
      --spacing-sm: [val]px;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    /* Styles globaux */
    body {
      font-family: var(--font-body);
      background-color: var(--color-bg);
      color: #[text-color];
    }

    /* Styles par composant — un bloc par frame Figma */
    .section-[nom] { ... }
    .component-[nom] { ... }
  </style>
</head>
<body>
  <!-- Structure HTML miroir de la hiérarchie Figma -->
  <section class="section-[nom]">
    <div class="component-[nom]">
      ...
    </div>
  </section>
</body>
</html>
```

### FORMAT : React + Tailwind

```jsx
// [ComponentName].jsx
// Extrait depuis Figma : [frame name]

export default function [ComponentName]() {
  return (
    <div className="flex flex-col w-[Xpx] bg-[#hex] rounded-[Xpx] p-[Xpx] gap-[Xpx]">
      <h1 className="text-[Xpx] font-[weight] text-[#hex] leading-[X]">
        Titre
      </h1>
      {/* ... */}
    </div>
  );
}
```

Pour les valeurs non-standard Tailwind, utiliser les classes arbitraires : `w-[347px]`, `text-[#1a1a2e]`, `rounded-[12px]`.

### FORMAT : React + CSS Modules

```jsx
// [ComponentName].jsx
import styles from './[ComponentName].module.css';

export default function [ComponentName]() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Titre</h1>
    </div>
  );
}
```

```css
/* [ComponentName].module.css */
.container {
  display: flex;
  flex-direction: column;
  width: [X]px;
  background-color: #[hex];
  border-radius: [X]px;
  padding: [X]px;
  gap: [X]px;
}

.title {
  font-family: '[Font]', sans-serif;
  font-size: [X]px;
  font-weight: [W];
  color: #[hex];
  line-height: [X];
}
```

---

## Étape 4 — Règles de fidélité

### Toujours respecter
1. **Les dimensions exactes** en px depuis Figma (width, height, padding, gap)
2. **Les couleurs exactes** converties depuis les fills Figma
3. **La hiérarchie des nœuds** → structure HTML imbriquée identique
4. **Les fonts** — chercher l'équivalent Google Fonts si la font Figma n'est pas disponible sur le web
5. **Le screenshot** est la référence visuelle absolue — si le code généré par Figma diverge du screenshot, se fier au screenshot

### Gestion des cas spéciaux
| Cas Figma | Traitement code |
|-----------|-----------------|
| Image fill | `<img>` avec `object-fit: cover` ou `background-image` |
| Icône SVG | Copier le SVG inline ou créer un `<svg>` équivalent |
| Composant avec variantes | Props en React, classes CSS conditionnelles en HTML |
| Texte tronqué | `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` |
| Overlay / modal | `position: fixed` + `z-index` |
| Scroll container | `overflow-y: auto` + hauteur fixe |
| Grid Figma | `display: grid; grid-template-columns: repeat([n], 1fr); gap: [x]px` |

---

## Étape 5 — Post-traitement

### Optimisations systématiques
- **Variables CSS** pour toutes les couleurs et espacements répétés
- **Classes réutilisables** pour les composants qui apparaissent plusieurs fois
- **Commentaires** indiquant le nom de la frame Figma correspondante
- **Responsive** : si le design est mobile/desktop, générer les deux avec media queries

### Accessibilité minimale
- `alt` sur toutes les `<img>`
- Hiérarchie `<h1>` → `<h2>` → `<h3>` respectée
- `role` et `aria-label` sur les éléments interactifs sans texte visible
- Contraste suffisant (signaler si une couleur Figma ne passe pas le WCAG AA)

---

## Étape 6 — Livraison

### Format de réponse
```
✅ Code généré depuis : "[Nom de la frame Figma]"
Format : [HTML/CSS | React + Tailwind | React + CSS Modules | Vue]
Dimensions : [W]×[H]px
Fonts utilisées : [liste]
Couleurs extraites : [palette hex]

[code dans un artifact]

⚠️ Points d'attention :
- [Font X] n'est pas sur Google Fonts → remplacée par [Font Y]
- [Image Y] → placeholder, remplacer par la vraie image
- [Element Z] → comportement interactif à implémenter
```

### Si le design est très large (page entière)
Découper en sections et générer section par section :
1. Confirmer la découpe avec l'utilisateur
2. Générer section 1, demander validation
3. Continuer jusqu'à la page complète
4. Assembler le tout dans un fichier final

---

## Workflow résumé

```
Lien Figma fourni
       ↓
get_design_context (screenshot + code de référence)
       ↓
Analyser screenshot + métadonnées
       ↓
Identifier layout, couleurs, fonts, composants
       ↓
Générer code dans le format demandé
       ↓
Livrer dans un artifact avec points d'attention
```
