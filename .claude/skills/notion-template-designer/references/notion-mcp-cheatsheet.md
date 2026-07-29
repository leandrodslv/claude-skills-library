# Notion MCP Cheatsheet

Exemples concrets d'utilisation du MCP Notion pour créer des templates. Les noms de paramètres exacts doivent être confirmés via `tool_search` au moment de l'exécution — les formats varient légèrement selon la version du MCP.

---

## Checklist avant de créer

1. **Vérifier que le MCP Notion est connecté** — si `Notion:notion-create-pages` apparaît dans les deferred tools, c'est bon.
2. **Trouver la page parente** — utiliser `Notion:notion-search` avec le nom de la page parente si l'utilisateur donne un nom. Sinon demander un lien Notion.
3. **Charger le tool** — appeler `tool_search` avec la query "notion create page" pour obtenir le schema exact avant le premier appel.

---

## Création d'une page simple

Via `notion-create-pages`. Paramètres typiques (confirmer via tool_search) :

```
parent: { page_id: "[UUID ou URL de la page parente]" }
properties: {
  title: "🎯 Ma nouvelle page"
}
icon: {
  type: "emoji",
  emoji: "🎯"
}
cover: {
  type: "external",
  external: {
    url: "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?q=80&w=1920&auto=format&fit=crop"
  }
}
content: "[markdown complet de la page — voir section suivante]"
```

---

## Syntaxe markdown supportée dans le MCP Notion

Le MCP Notion convertit le markdown en blocs Notion natifs. Formats supportés :

### Titres
```markdown
# H1 (converti en Heading 1)
## H2
### H3
```

### Paragraphes
Texte simple séparé par des lignes vides.

### Listes
```markdown
- bullet
- bullet
1. numbered
2. numbered
- [ ] todo
- [x] todo done
```

### Callouts
```markdown
> [!info] Titre optionnel
> Contenu du callout
```

Types supportés : `info`, `warning`, `error`, `success`, `tip`. Certains MCP acceptent aussi `> [!callout emoji="💡" color="blue"]`.

### Toggles
```markdown
▸ Titre du toggle
  Contenu caché
```

Ou selon le MCP :
```markdown
<details>
<summary>Titre du toggle</summary>
Contenu caché
</details>
```

### Colonnes
Pas de syntaxe markdown native. Le MCP peut avoir une convention custom :
```markdown
:::columns
::: column
Contenu colonne 1
:::
::: column
Contenu colonne 2
:::
:::
```

Si le MCP ne gère pas les colonnes : créer en séquentiel puis faire un update manuel (ou laisser l'utilisateur les créer en drag-and-drop).

### Dividers
```markdown
---
```

### Code
```markdown
\`\`\`javascript
const x = 1;
\`\`\`
```

### Citations
```markdown
> Texte en citation
```

### Images
```markdown
![alt](https://url.com/image.png)
```

### Liens
```markdown
[texte](https://url)
```

### Tables
```markdown
| Col 1 | Col 2 |
|-------|-------|
| A     | B     |
```

---

## Création d'une base de données

Via `notion-create-database`. Structure typique :

```
parent: { page_id: "[UUID page parente]" }
title: [{ type: "text", text: { content: "🎯 Tasks" } }]
icon: { type: "emoji", emoji: "🎯" }
properties: {
  "Task": { title: {} },
  "Status": {
    status: {
      options: [
        { name: "Not started", color: "gray" },
        { name: "In progress", color: "blue" },
        { name: "Done", color: "green" }
      ]
    }
  },
  "Priority": {
    select: {
      options: [
        { name: "🔴 High", color: "red" },
        { name: "🟡 Medium", color: "yellow" },
        { name: "🟢 Low", color: "green" }
      ]
    }
  },
  "Due": { date: {} },
  "Tags": { multi_select: { options: [...] } }
}
```

**Pièges fréquents** :
- `Status` est un type différent de `Select` (plus récent, avec groupes). Confirmer que le MCP le supporte, sinon fallback sur `Select`.
- Les options de Select/Multi-select doivent toutes avoir une `color` valide : `default`, `gray`, `brown`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink`, `red`.
- Les `Relation` nécessitent le `database_id` de la BDD cible.

---

## Création d'une vue

Via `notion-create-view` ou `notion-update-view`. Structure :

```
parent_database_id: "[UUID BDD]"
name: "This week"
type: "timeline"
filter: {
  property: "Due",
  date: { past_week: {} }
}
sort: [
  { property: "Priority", direction: "descending" }
]
```

Types de vues : `table`, `board`, `timeline`, `calendar`, `list`, `gallery`.

---

## Workflow type : créer un template complet

Ordre optimal pour créer un workspace complet :

1. **Créer les BDD en premier** (sans relations entre elles) → on obtient leurs IDs
2. **Ajouter les relations** entre BDD via `notion-update-data-source`
3. **Créer la page principale** avec le markdown complet
4. **Ajouter les linked views** vers les BDD créées (via update de la page)
5. **Ajouter les sous-pages** (projets, templates de BDD)
6. **Configurer les vues personnalisées** de chaque BDD

---

## Fallback : recréer manuellement ce que le MCP ne gère pas

Certains éléments Notion ne passent pas bien via le MCP. Pour chacun, donner des instructions manuelles claires à l'utilisateur en fin de réponse :

- **Synced blocks** → créer dans l'UI : `/synced` puis copier-coller sur les autres pages
- **Buttons (boutons automation)** → UI uniquement : `/button`
- **Custom icons uploadés** → UI : clic sur l'icône → "Upload"
- **Embed externe (Figma, Loom, etc.)** → UI : `/embed`
- **Templates de BDD** → UI : clic sur ▾ à côté de "New" dans la BDD → "New template"
- **Vues avec regroupement complexe** → parfois plus simple dans l'UI

Format recommandé pour les instructions manuelles :

```markdown
## ⚙️ Setup manuel (3 min)

Ces éléments ne sont pas créés par Notion MCP. À faire dans l'UI :

1. **Synced nav bar** — Sur la page d'accueil, tape `/synced`, crée une barre avec les liens vers les 4 pages principales. Copie-la (clic droit → "Copy") et colle-la en haut de chaque page enfant.
2. **Template "Daily note"** — Dans la BDD "Journal", clique sur ▾ à côté de "New" → "+ New template" → crée le template avec la structure fournie.
3. **Cover custom** — Si tu préfères un cover personnalisé, upload depuis [URL Canva/Figma] via "Change cover" → "Upload".
```

---

## Debug : messages d'erreur fréquents

- **"Invalid parent"** → vérifier que le page_id est bien un UUID valide (pas une URL)
- **"Property X does not exist"** → le type de propriété attendu ne matche pas, vérifier le schema exact
- **"Color not supported"** → utiliser uniquement les 10 couleurs Notion (voir plus haut)
- **"Rate limit"** → Notion limite à ~3 req/sec. Ajouter un délai si beaucoup de pages à créer en batch.

Si une erreur persiste, fallback sur le mode B (livrer un markdown) et laisser l'utilisateur le coller manuellement.
