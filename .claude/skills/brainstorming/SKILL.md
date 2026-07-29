---
name: brainstorming
description: |
  Expert en facilitation de brainstorming et idéation créative. Utilise ce skill dès que l'utilisateur veut générer des idées, explorer un problème, trouver un nom, chercher des angles créatifs, débloquer une réflexion, ou structurer une session d'idéation. Déclenche sur : "brainstorming", "idées pour", "comment on pourrait", "je cherche des idées", "aidez-moi à réfléchir", "explore des pistes", "HMW", "SCAMPER", "génère des idées", "naming", "quelles solutions", "pistes créatives", "fais-moi un brainstorming", "j'ai un problème à résoudre", "j'ai besoin d'inspiration", "comment améliorer". Sélectionne automatiquement la méthode la plus adaptée parmi HMW, SCAMPER, Crazy 8s, Brainwriting, SWOT créatif, Analogies, Reverse Brainstorming, et bien d'autres. Toujours utiliser ce skill plutôt qu'une simple liste d'idées : le résultat est un canvas structuré, actionnable, visuellement organisé.
---

# Brainstorming Skill

## Objectif

Transformer n'importe quelle demande d'idéation en une **session de brainstorming structurée** avec un canvas exploitable. Claude choisit la méthode la plus adaptée selon le contexte, produit un livrable clair, et propose des prolongements actionnables.

---

## Étape 1 — Diagnostic du contexte

Avant de choisir une méthode, analyser :

| Signal | Méthode(s) recommandée(s) |
|--------|--------------------------|
| Problème utilisateur flou | HMW (How Might We) |
| Améliorer un produit / service existant | SCAMPER |
| Trouver un nom / slogan | Naming Canvas |
| Générer un max d'idées brutes | Brainwriting / Round-robin simulé |
| Débloquer une impasse créative | Reverse Brainstorming |
| Analyser forces/faiblesses + idées | SWOT créatif |
| Explorer un sujet ouvert | Mind Map + Analogies |
| Urgence / contrainte forte | Crazy 8s (8 idées en structure rapide) |
| Problème stratégique ou business | Jobs-to-be-done + Opportunités |

> Si le contexte est ambigu, combiner 2 méthodes complémentaires.

---

## Étape 2 — Sélection et annonce de la méthode

Annoncer brièvement :
1. La méthode choisie et **pourquoi** elle convient ici
2. La structure du canvas qui va suivre
3. Inviter l'utilisateur à préciser ou valider avant de lancer si besoin (sauf si la demande est claire — dans ce cas, foncer directement)

---

## Étape 3 — Génération du Canvas

Produire le canvas complet selon la méthode. Voir `/references/methodes.md` pour le détail de chaque template.

### Règles de génération

- **Quantité d'abord** : générer au minimum 8 idées par section, viser 12-15
- **Diversité obligatoire** : couvrir des angles radicaux, réalistes, analogiques, contra-intuitifs
- **Pas de filtre prématuré** : inclure les idées audacieuses, même celles qui semblent impraticables
- **Niveau de détail** : chaque idée = 1 phrase d'action claire (pas juste un mot-clé)
- **Mise en forme** : utiliser des blocs visuels distincts par section (titres, séparateurs, emojis de section)

### Format du canvas

```
╔══════════════════════════════════════╗
║  🧠 [NOM DE LA MÉTHODE]              ║
║  Sujet : [reformulation du sujet]    ║
╚══════════════════════════════════════╝

[SECTION 1 — Titre]
──────────────────
• Idée 1 : [description actionnable]
• Idée 2 : ...
...

[SECTION 2 — Titre]
──────────────────
• ...

[SECTION N]
──────────
• ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TOP 3 idées à creuser en priorité
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [Idée] — Pourquoi : [justification courte]
2. ...
3. ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Prochaines étapes suggérées
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ [Action concrète 1]
→ [Action concrète 2]
→ [Action concrète 3]
```

---

## Étape 4 — Rebond et approfondissement

Après le canvas, **toujours proposer** au moins une de ces options :
- Approfondir une idée spécifique (prototypage rapide, user story, plan d'action)
- Lancer une 2ème méthode complémentaire
- Voter / prioriser les idées (matrice Impact/Effort)
- Exporter vers Notion ou FigJam si les MCPs sont disponibles

---

## Comportements clés

- **Ne jamais** produire une simple liste à puces sans structure de canvas
- **Ne jamais** se limiter à 3-5 idées génériques
- **Toujours** reformuler le problème avant de lancer le canvas (reformulation = meilleur cadrage)
- **Si le sujet est sensible** (RH, conflits, etc.) : brainstorming orienté solutions positives uniquement
- **Si c'est du naming** : utiliser le Naming Canvas dédié (voir références)
- **Adapter la langue** : répondre dans la langue de la demande

---

## Intégrations MCP disponibles

Si les MCPs suivants sont connectés, proposer l'export :
- **Notion** (`mcp.notion.com`) → Créer une page "Brainstorming — [sujet]" avec le canvas
- **FigJam** (`mcp.figma.com`) → Générer un board FigJam via le skill `figjam-ux-toolkit`

---

## Références

- Détail des méthodes et templates : `references/methodes.md`
