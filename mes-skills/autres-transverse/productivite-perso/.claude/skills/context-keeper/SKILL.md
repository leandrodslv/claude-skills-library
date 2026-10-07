---
name: context-keeper
description: >
  Crée, met à jour et restaure un fichier de contexte maître qui capture l'état
  complet de tous les projets en cours — agents IA, workflows, décisions techniques,
  prochaines étapes — pour reprendre instantanément dans n'importe quelle conversation.

  Déclencher dès que l'utilisateur dit : "mets à jour mon contexte", "sauvegarde où j'en
  suis", "génère mon fichier de contexte", "reprends là où on était", "résume notre
  avancement", "crée mon context file", "je veux pouvoir reprendre plus tard",
  "qu'est-ce qu'on a fait jusqu'ici", "fais le point", "donne-moi un résumé de tout
  ce qu'on a construit". Aussi déclencher en fin de longue conversation quand
  l'utilisateur semble vouloir conclure ou a beaucoup de projets en cours.
  Toujours utiliser ce skill plutôt qu'un simple résumé conversationnel.
---

# Context Keeper — Mémoire externe de projets

## Rôle

Tu maintiens un fichier Markdown structuré qui capture l'état complet de tous
les projets de l'utilisateur. Ce fichier est conçu pour être collé en début de
n'importe quelle conversation afin de reprendre exactement là où on s'est arrêté.

---

## DEUX MODES D'UTILISATION

### MODE GÉNÉRATION — "sauvegarde mon contexte"
L'utilisateur veut capturer l'état actuel de la conversation / ses projets.
→ Tu génères ou mets à jour le fichier CONTEXT.md

### MODE RESTAURATION — "reprends là où on était" ou l'utilisateur colle son CONTEXT.md
L'utilisateur colle son fichier de contexte en début de conversation.
→ Tu lis le fichier, tu fais un brief de reprise, et tu proposes la prochaine action

---

## STRUCTURE DU FICHIER CONTEXT.md

```markdown
# CONTEXT — [Prénom/Pseudo]
Dernière mise à jour : [date et heure]
Conversation source : [résumé en 1 phrase de ce qui vient d'être fait]

---

## 🧠 QUI JE SUIS
[Profil professionnel en 2-3 phrases : métier, spécialités, contexte de travail]
[Outils connectés : Notion, Figma, n8n, etc.]
[Stack technique : Claude Code, React, Vercel, etc.]

---

## 🤖 MES AGENTS IA

### [Nom de l'agent] — [état : ✅ Terminé / 🔄 En cours / 💡 Idée]
- **Rôle** : [ce que fait l'agent en 1 phrase]
- **Fichier** : [nom du .zip ou dossier]
- **Stack** : [CLAUDE.md + références + scripts / Skill Claude.ai / n8n workflow]
- **Outils connectés** : [Notion, Figma, Excel, etc.]
- **État actuel** : [phase, ce qui marche, ce qui manque]
- **Prochaine étape** : [action concrète à faire]

[répéter pour chaque agent]

---

## 📁 FICHIERS GÉNÉRÉS
[liste des fichiers créés avec leur usage]
- `echo-workbench.zip` — Interface React pour ECHO, déployer sur Vercel
- `lens-agent.zip` — Agent audit LENS Claude Code
- `uxr-agent-echo-final.zip` — Agent ECHO complet
- etc.

---

## 🔧 STACK & INFRASTRUCTURE
[Outils, comptes, configurations importantes à se rappeler]
- Claude Code : utilisé pour faire tourner les agents
- Vercel : déploiement du workbench (gratuit)
- Clé API Anthropic : dans .env.local
- Notion MCP : connecté (url: https://mcp.notion.com/mcp)
- Figma MCP : connecté (url: https://mcp.figma.com/mcp)
- n8n : en place pour les workflows Alfred et veille

---

## 📌 DÉCISIONS IMPORTANTES PRISES
[Les choix structurants qui ne doivent pas être remis en question]
- Architecture : agents séparés (ECHO + LENS) plutôt qu'un seul agent monolithique
- Modèle : Sonnet 4.6 pour ECHO/LENS (qualité > coût pour UXR)
- Backend workbench : Vercel API Routes (pas de Supabase, pas de n8n)
- etc.

---

## ⏳ PROCHAINES ÉTAPES (priorisées)

### Priorité 1 — À faire maintenant
- [ ] [action concrète]
- [ ] [action concrète]

### Priorité 2 — Cette semaine
- [ ] [action concrète]

### Idées à explorer
- [ ] [idée]

---

## 💬 CONTEXTE DE LA DERNIÈRE CONVERSATION
[Résumé des 5-10 points clés discutés — ce qu'il faut absolument se rappeler]
- On a construit X parce que Y
- La décision Z a été prise pour la raison W
- Le problème N n'est pas encore résolu
- etc.
```

---

## MODE GÉNÉRATION — CE QUE TU FAIS

1. **Scanner la conversation entière** — extraire tous les projets, décisions, fichiers créés, problèmes rencontrés, prochaines étapes mentionnées

2. **Vérifier si un CONTEXT.md existe déjà** dans la conversation — si oui, le mettre à jour plutôt que repartir de zéro

3. **Générer le fichier complet** en suivant la structure ci-dessus

4. **Présenter le fichier** dans un bloc de code Markdown copiable

5. **Dire exactement comment l'utiliser** :
   ```
   ✅ Fichier généré. Pour reprendre dans une nouvelle conversation :
   1. Copier tout le contenu du bloc ci-dessus
   2. Coller en début de message dans une nouvelle conversation
   3. Ajouter : "Reprends le contexte et dis-moi où on en est"
   ```

---

## MODE RESTAURATION — CE QUE TU FAIS

Quand l'utilisateur colle son CONTEXT.md en début de conversation :

1. **Lire et absorber** tout le fichier silencieusement

2. **Faire un brief de reprise** en VOIX naturelle et engagée :
   ```
   Contexte chargé. Voilà où on en est :

   [2-3 phrases sur l'état global des projets]

   Agents actifs : ECHO ✅ LENS ✅ [autres]
   Prochaine étape recommandée : [la première action de la liste]

   On continue ?
   ```

3. **Ne pas réécrire tout le contexte** — juste le brief, puis attendre l'instruction

4. **Proposer la prochaine action** basée sur la liste des priorités du fichier

---

## RÈGLES DE QUALITÉ

- **Précis et actionnable** — chaque "prochaine étape" doit être faisable immédiatement
- **Pas de redondance** — si une info est dans "agents", elle n'est pas dans "contexte conversation"
- **Daté** — toujours mettre la date et heure de mise à jour
- **Évolutif** — à chaque mise à jour, ne pas effacer l'ancien, enrichir
- **Copiable** — le fichier doit tenir dans un seul message (< 4000 mots)

Si le fichier devient trop long : condenser "contexte conversation" en gardant uniquement ce qui est structurellement important (décisions, blocages, découvertes), pas le détail des échanges.
