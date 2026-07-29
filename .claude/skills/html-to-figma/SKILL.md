---
name: html-to-figma
description: Convertit des fichiers HTML/CSS en maquette Figma pixel-perfect via le MCP Figma. Utilise ce skill dès que l'utilisateur fournit du code HTML et/ou CSS et veut le voir dans Figma, le transférer en maquette, créer des frames Figma depuis son code, importer un design Claude dans Figma, ou "pousser" son HTML vers Figma. Déclencher aussi pour : "transfère dans Figma", "crée la maquette Figma de", "converti mon HTML en Figma", "importe dans Figma", "met dans Figma", "exporte vers Figma", "html to figma", "crée les frames", "maquette à partir de mon code". Toujours utiliser ce skill plutôt qu'une réponse générique dès que HTML/CSS + Figma sont impliqués ensemble.
---

# HTML → Figma (Pixel-Perfect)

Convertit du HTML/CSS vanilla en frames Figma fidèles, en utilisant le MCP Figma (`use_figma`) pour écrire directement dans le fichier via l'API Plugin.

---

## Étape 0 — Prérequis

Avant de commencer, vérifier que :
1. L'utilisateur a fourni le code HTML (et le CSS associé — inline, `<style>`, ou fichier séparé)
2. L'utilisateur a fourni un **lien Figma** vers le fichier cible (ex. `https://www.figma.com/design/XXXXX/...`)
3. Si l'URL ne contient pas de `node-id`, on travaillera sur la page courante

Si l'un de ces éléments manque, le demander avant de continuer.

---

## Étape 1 — Parser le HTML/CSS

Analyser le code fourni pour extraire **tous** les éléments visuels dans l'ordre du DOM :

### Extraction CSS
Pour chaque règle CSS, extraire :
- `background-color` / `background` → fill de la frame
- `color` → fill du texte
- `font-family`, `font-size`, `font-weight`, `line-height`, `letter-spacing` → style texte
- `width`, `height`, `min-width`, `max-width` → dimensions (convertir `%` en px si le conteneur parent est connu)
- `padding`, `margin` → espacement (utiliser `itemSpacing` + `paddingTop/Right/Bottom/Left` dans Figma)
- `border-radius` → `cornerRadius`
- `border` → `strokeWeight` + `strokeColor`
- `box-shadow` → `effects` de type `DROP_SHADOW`
- `display: flex` → `layoutMode: "HORIZONTAL"` ou `"VERTICAL"` selon `flex-direction`
- `gap` → `itemSpacing`
- `align-items` / `justify-content` → `primaryAxisAlignItems` / `counterAxisAlignItems`
- `opacity` → `opacity`
- `position: absolute` + `top/left/right/bottom` → positionnement absolu dans la frame parente

### Extraction des éléments
- `<div>`, `<section>`, `<header>`, etc. → **FRAME** ou **RECTANGLE**
- `<p>`, `<h1>`–`<h6>`, `<span>`, `<a>` → **TEXT**
- `<img>` → **RECTANGLE** avec fill image (si src disponible) ou placeholder gris
- `<button>` → **FRAME** avec texte enfant
- `<input>`, `<textarea>` → **FRAME** avec stroke border
- `<hr>` → **LINE** ou rectangle fin
- `<ul>/<li>` → groupe de TEXT nodes avec bullet
- `<svg>` → utiliser `figma.createNodeFromSvg()` avec le SVG inline

---

## Étape 2 — Résoudre les unités CSS

Avant de passer au code Figma, convertir toutes les unités :

| CSS | Figma |
|-----|-------|
| `px` | valeur directe (1px = 1 unité Figma) |
| `rem` | multiplier par 16 (base par défaut) |
| `em` | multiplier par la font-size parente |
| `%` | calculer par rapport au conteneur parent connu |
| `vw` / `vh` | utiliser la largeur/hauteur de la frame racine |
| `auto` | ignorer ou utiliser `"HUG"` si c'est width/height |
| `inherit` | remonter à la valeur parente |

Pour les couleurs :
- `hex` → décomposer en `{ r, g, b }` (valeurs 0–1 : diviser par 255)
- `rgb()` / `rgba()` → même chose + `opacity` pour le `a`
- `hsl()` → convertir en RGB d'abord
- `var(--custom-prop)` → résoudre la variable CSS si elle est définie dans le code fourni

---

## Étape 3 — Générer le code Plugin Figma

Construire un script JavaScript complet pour `use_figma`. Structure type :

```javascript
// Helper : convertit hex en RGB normalisé
function hexToRgb(hex) {
  const r = parseInt(hex.slice(1,3), 16) / 255;
  const g = parseInt(hex.slice(3,5), 16) / 255;
  const b = parseInt(hex.slice(5,7), 16) / 255;
  return { r, g, b };
}

// Helper : charge et attend une font
async function loadFont(family, style) {
  try {
    await figma.loadFontAsync({ family, style });
  } catch(e) {
    await figma.loadFontAsync({ family: "Inter", style: "Regular" });
  }
}

// Frame racine (représente le <body> ou le conteneur principal)
const frame = figma.createFrame();
frame.name = "Page – [nom du composant]";
frame.resize(1440, 900); // adapter à la vraie taille
frame.fills = [{ type: 'SOLID', color: hexToRgb('#ffffff') }];
frame.x = 0;
frame.y = 0;

// Pour chaque enfant…
// (générer récursivement)
```

### Règles impératives pour le code généré

1. **Toujours charger les fonts** avec `await figma.loadFontAsync()` avant de manipuler du texte — sinon l'API crashe
2. **Nommer les nodes** selon la structure HTML : `"div.card"`, `"h1 – Titre"`, `"button – CTA"`, etc.
3. **Appender dans le bon ordre** : toujours `parent.appendChild(child)` après avoir créé le nœud
4. **Auto-layout** : si le CSS contient `display: flex`, utiliser `layoutMode` + `primaryAxisSizingMode` + `counterAxisSizingMode`
5. **Effets** : `box-shadow` → créer un objet `{ type: "DROP_SHADOW", color: {..., a: opacity}, offset: {x, y}, radius: blur, visible: true, blendMode: "NORMAL" }`
6. **Coins arrondis** : `cornerRadius` accepte un seul nombre ; pour des coins différents, utiliser `topLeftRadius`, `topRightRadius`, etc.
7. **Stroke** : `strokeWeight` + `strokes = [{ type: 'SOLID', color: ... }]` + `strokeAlign: "INSIDE" | "OUTSIDE" | "CENTER"`
8. **Images** : créer un rectangle et utiliser `figma.createImage()` avec une URL si disponible, ou un placeholder `fills = [{ type: 'SOLID', color: { r: 0.9, g: 0.9, b: 0.9 } }]`
9. **SVG inline** : utiliser `figma.createNodeFromSvg(svgString)` — le seul moyen correct
10. **Wrap dans `(async () => { ... })()`** si des `await` sont utilisés (ce qui est presque toujours le cas pour les fonts)

---

## Étape 4 — Appeler `use_figma`

Une fois le script généré :

```
Figma:use_figma({
  fileKey: "<extrait de l'URL>",
  description: "Création pixel-perfect de [nom] depuis HTML/CSS",
  code: "<le script généré>"
})
```

Si le code est très long (>300 lignes), le découper en appels successifs :
1. D'abord la frame racine + les sections principales
2. Ensuite les composants enfants section par section

---

## Étape 5 — Vérification & corrections

Après l'appel, informer l'utilisateur du résultat et proposer :
- **"Les couleurs sont décalées"** → re-vérifier la conversion hex/rgb
- **"Le texte est trop grand/petit"** → re-vérifier la conversion `rem`/`em`
- **"Les espacements ne correspondent pas"** → vérifier `padding` vs `itemSpacing` (auto-layout) vs positionnement absolu
- **"Une section manque"** → relancer un appel `use_figma` pour l'ajouter

---

## Limites connues & workarounds

| Limitation | Workaround |
|------------|------------|
| `background: linear-gradient()` | Figma supporte les gradients : utiliser `{ type: "GRADIENT_LINEAR", gradientStops: [...], gradientTransform: [[...]] }` |
| `background-image: url(...)` | Créer l'image via `figma.createImage()` si l'URL est accessible, sinon placeholder |
| `clip-path` | Non supporté nativement — utiliser une mask layer |
| `transform: rotate()` | `node.rotation = angle` (en degrés, sens antihoraire dans Figma) |
| `::before / ::after` | Créer un nœud Figma séparé représentant le pseudo-élément |
| `overflow: hidden` | `node.clipsContent = true` |
| Fonts non Google | Fallback sur Inter si la font n'est pas dispo dans Figma |
| `position: sticky` | Traiter comme `position: relative` pour la maquette statique |
| `animation / transition` | Ignorer — les maquettes sont statiques |
| `calc()` | Résoudre manuellement avant de passer la valeur |

---

## Format de réponse attendu

Après chaque import réussi :
1. Confirmer que les frames ont été créées
2. Indiquer le nom exact des frames dans Figma
3. Proposer des ajustements si des éléments n'ont pas pu être convertis fidèlement
4. Rappeler à l'utilisateur d'ouvrir Figma pour voir le résultat (le MCP ne fournit pas de preview)
