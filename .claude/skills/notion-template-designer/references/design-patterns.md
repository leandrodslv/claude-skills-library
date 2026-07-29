# Design Patterns Notion

Patterns de layout éprouvés pour différents types de pages. Chaque pattern inclut la structure markdown exacte à utiliser + les spécificités Notion à respecter.

---

## Pattern 1 — Dashboard home (page d'accueil workspace)

**Quand** : la page racine d'un workspace, point d'entrée quotidien.

**Structure** :
```markdown
[COVER : Unsplash cohérent avec la direction]
[ICÔNE : emoji principal du workspace]

# [Titre du workspace]
> *[Tagline courte — 1 phrase qui résume l'ambition]*

---

## Aujourd'hui

[3 COLONNES]

Col 1 — 📋 **Focus du jour**
[callout bleu avec les 3 priorités]

Col 2 — 📅 **Agenda**
[linked view de la BDD Events, filtrée sur aujourd'hui]

Col 3 — ✅ **Tasks**
[linked view de la BDD Tasks, filtrée "Due today OR Overdue"]

---

## Navigation

[SYNCED BLOCK avec toggles organisés]

▸ 🎯 Projets
  → lien page Projets
▸ 📚 Knowledge
  → lien page Notes
▸ 💼 Pro
  → lien page Work

---

## Métriques rapides

[3 COLONNES de callouts]
- 🔥 Streak actuelle : X jours
- 📊 Tasks cette semaine : X / Y
- 📖 Livres en cours : X
```

**Règles** :
- Toujours un synced block pour la navigation (sert dans toutes les pages enfants)
- Max 3 colonnes, sinon illisible sur mobile
- Les linked views doivent être filtrées, pas la BDD complète

---

## Pattern 2 — Journal / Daily note

**Quand** : page de journal quotidien, reprend la même structure chaque jour.

**Structure** :
```markdown
[COVER : Unsplash paysage doux / neutre]
[ICÔNE : emoji cohérent, ex 📔]

# [Date en format long, ex: Samedi 18 avril 2026]
> *Humeur : [ ] ☀️ [ ] ⛅ [ ] 🌧️ [ ] ⚡*

---

## Matin

> [!callout gris]
> **Intention du jour** : [...]

🙏 **Gratitude** (3 choses)
1. 
2. 
3. 

🎯 **3 priorités**
- [ ] 
- [ ] 
- [ ] 

---

## Soir

📝 **Debrief** (dans toggle pour garder la page propre)
▸ Ce qui a bien marché
▸ Ce qui m'a bloqué
▸ Ce que je retiens

---

## Notes flottantes

[zone libre pour capter au fil de la journée]
```

**Règles** :
- Ce pattern doit être **un template de BDD** (une BDD "Daily Notes" avec ce pattern comme template par défaut)
- Propriétés BDD à créer : Date (date), Humeur (select), Tags (multi-select), Lien projet (relation)

---

## Pattern 3 — Habit tracker

**Quand** : suivi quotidien d'habitudes.

**Structure** : uniquement une BDD avec vues.

**BDD "Habits Log"** :
- Date (date) — primary
- Sport (checkbox)
- Lecture (checkbox)
- Méditation (checkbox)
- Eau 2L (checkbox)
- Note du jour (text)

**Vues à créer** :
1. **Table** (défaut) — tri par date desc
2. **Gallery "Cette semaine"** — filtre Date is within "Past 7 days"
3. **Calendar** — vue calendrier
4. **Board "Par habitude"** — optionnel, groupé par nombre de checks

**Sur la page parent** :
```markdown
# 🔥 Habits

> *Progresser par défaut, pas par motivation.*

[linked view "Cette semaine" en gallery]

---

▸ 📊 Stats du mois
  [linked view filtrée sur le mois en cours, avec calcul des % de réussite par habitude]

▸ 📝 Notes & apprentissages
  [zone libre pour les réflexions sur les habits]
```

---

## Pattern 4 — Projet (projet unique)

**Quand** : page dédiée à un projet (ex: "Alfred", "EDF Personas").

**Structure** :
```markdown
[COVER : cohérent avec le projet — screenshot, moodboard, ou Unsplash thématique]
[ICÔNE : emoji du projet]

# [Nom du projet]
> *[Tagline du projet en 1 phrase]*

[callout bleu — "propriétés du projet"]
📅 Deadline · [date]
🎯 Statut · [En cours / Livré / Pause]
🔗 Lien démo · [URL]
👥 Stakeholders · [noms]

---

## 🎯 Contexte & objectifs

[2-3 paragraphes courts]

---

## 📋 Tasks

[linked view de la BDD Tasks, filtrée sur ce projet, groupée par statut (board)]

---

## 📝 Journal du projet

[liste inversée chronologique, une entrée = un toggle avec la date]

▸ 18 avril — Début du POC
  [notes]

▸ 17 avril — Cadrage avec stakeholders
  [notes]

---

## 📎 Ressources

[colonnes ou liste avec les liens utiles, specs, maquettes]
```

**Règles** :
- La BDD Tasks est partagée avec le workspace (relation avec la BDD Projets)
- Journal en toggle pour garder la page courte
- Callout "propriétés" en haut = info essentielle en 1 coup d'œil

---

## Pattern 5 — Portfolio (pour postuler)

**Quand** : page publique ou semi-publique pour montrer son travail (ex: postuler en alternance).

**Structure** :
```markdown
[COVER : moodboard personnel ou photo pro]
[ICÔNE : initiale ou emoji signature]

# [Prénom Nom]
> *[Titre pro court — ex: "UX Designer & Product Builder"]*

[3 COLONNES]

Col 1 — 🎯 **Ce que je fais**
[bullet points de 3-4 expertises]

Col 2 — 🛠️ **Stack**
[tags des outils/techs]

Col 3 — 📬 **Contact**
[email, LinkedIn, site]

---

## ✨ Projets phares

[GALLERY VIEW d'une BDD "Projects"]
Propriétés à afficher :
- Cover (image)
- Titre
- Rôle
- Stack (tags)
- Année

Chaque projet = une page enfant avec le Pattern 4 adapté.

---

## 📝 À propos

[1 paragraphe perso — histoire, valeurs, motivations]

---

## 📄 CV & liens

[boutons / liens vers CV PDF, LinkedIn, GitHub, etc.]
```

**Règles** :
- La gallery des projets est LE focus visuel — les covers des projets doivent être soignées
- Si partagée publiquement : utiliser notion.site custom domain si possible
- Toujours un "à propos" humain en fin — évite l'effet CV robotique

---

## Pattern 6 — Base de connaissances (second brain léger)

**Quand** : système de notes, learning hub, research archive.

**Structure** :
```markdown
# 🧠 Knowledge

> *Ce que j'apprends, capture, connecte.*

---

## 🔎 Quick capture

[bouton qui crée une nouvelle entrée dans la BDD "Notes" avec template "Quick note"]

---

## 📚 Par domaine

[3 COLONNES avec emojis thématiques]

🎨 **Design**
[linked view filtrée tag=design, galerie]

⚙️ **Tech**
[linked view filtrée tag=tech, galerie]

🧠 **Thinking**
[linked view filtrée tag=thinking, galerie]

---

## 🕸️ Toutes les notes

[linked view complète en table, avec filtres/sorts disponibles]
```

**BDD "Notes"** :
- Titre (text)
- Tags (multi-select)
- Source (URL)
- Date (created_time)
- Statut (select : raw / processed / archived)
- Liens (relations vers d'autres notes)

---

## Règles transversales (à respecter dans tous les patterns)

1. **Hiérarchie visuelle** : H1 = titre de page uniquement. H2 = sections majeures. H3 = sous-sections. Ne pas sauter de niveau.
2. **Dividers** (`---`) : entre sections majeures uniquement. Pas entre chaque sous-partie.
3. **Callouts** : max 3 par page, sinon ça devient du bruit.
4. **Toggles** : pour tout contenu > 3 lignes qui n'est pas essentiel "above the fold".
5. **Colonnes** : 2 ou 3 max. Au-delà, illisible sur mobile.
6. **Linked views > embeds** : toujours préférer les linked views quand on référence une BDD existante.
