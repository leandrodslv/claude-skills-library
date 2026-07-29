# Database Patterns

Schémas de bases de données prêts à l'emploi pour les use-cases Notion les plus courants. Chaque pattern inclut : propriétés, types exacts, vues recommandées, et exemple d'utilisation.

---

## BDD 1 — Tasks

**Use case** : suivi de tâches quotidiennes, GTD-style.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Task | Title | — |
| Status | Status | Not started / In progress / Done / Archived |
| Priority | Select | 🔴 High / 🟡 Medium / 🟢 Low |
| Due | Date | — |
| Project | Relation | → BDD Projects |
| Tags | Multi-select | personal / work / health / learning |
| Effort | Select | S / M / L / XL |
| Created | Created time | — |
| Assignee | Person | (si workspace multi-user) |

### Vues

1. **Today** (table) — Filter: `Due is Today OR Overdue` + `Status ≠ Done` · Sort: Priority desc
2. **This week** (timeline) — Timeline by `Due` · Sort: Priority desc
3. **Board** (board) — Group by `Status` · Hide Archived column
4. **By project** (board) — Group by `Project`
5. **Backlog** (table) — Filter: `Status = Not started` AND `Due is empty`
6. **Done this week** (table) — Filter: `Status = Done` AND `Last edited time is within Past 7 days`

---

## BDD 2 — Projects

**Use case** : projets actifs avec leurs métadonnées.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Project | Title | — |
| Status | Status | Idea / Active / Shipped / Paused / Archived |
| Category | Select | 🎨 Design / 💻 Dev / 💼 Work / 🎓 School / 🏡 Personal |
| Start | Date | — |
| Deadline | Date | — |
| Progress | Formula | `prop("Tasks done") / prop("Tasks total")` |
| Tasks | Relation | → BDD Tasks (rollup count) |
| Link | URL | — |
| Priority | Select | 🔥 Top / 📌 Normal / ❄️ Later |

### Vues

1. **Active projects** (gallery) — Filter: `Status = Active` · Card preview: cover
2. **Timeline** (timeline) — Timeline by Start/Deadline, grouped by Category
3. **By status** (board) — Group by Status
4. **Shipped** (gallery) — Filter: `Status = Shipped` · Sort: Deadline desc (portfolio-style)

---

## BDD 3 — Notes (second brain)

**Use case** : capture d'idées, articles lus, insights.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Note | Title | — |
| Status | Select | 🌱 Seedling / 🌿 Growing / 🌳 Evergreen / 📦 Archived |
| Tags | Multi-select | design / tech / philosophy / career / misc |
| Source | URL | — |
| Author | Text | — |
| Created | Created time | — |
| Linked notes | Relation | → self (notes ↔ notes) |
| Projects | Relation | → BDD Projects |

### Vues

1. **All notes** (table) — Sort: Created desc
2. **Recent captures** (gallery) — Filter: Created is within Past 14 days
3. **Evergreen** (gallery) — Filter: `Status = Evergreen` · Group by Tags
4. **By tag** (board) — Group by Tags

### Convention d'écriture des notes (à mentionner à l'utilisateur)
- Titre = une assertion complète, pas juste un sujet ("Les designs trop denses frustrent l'utilisateur" > "UX Density")
- Chaque note renvoie à ≥1 autre note via la relation `Linked notes`
- Passage Seedling → Evergreen = au moins 3 liens + réécriture dans tes mots

---

## BDD 4 — Habits

**Use case** : tracking quotidien d'habitudes.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Date | Title (format date) | — |
| Day | Formula | `formatDate(prop("Date"), "dddd")` |
| Sport | Checkbox | — |
| Reading | Checkbox | — |
| Meditation | Checkbox | — |
| Water 2L | Checkbox | — |
| Sleep ≥7h | Checkbox | — |
| Mood | Select | ☀️ / ⛅ / 🌧️ / ⚡ |
| Energy | Number (1-5) | — |
| Note | Text | — |
| Score | Formula | compte des checkboxes true / total × 100 |

### Vues

1. **This week** (gallery) — Filter: Date is within Past 7 days · Card: show all checkboxes
2. **Calendar** — Calendar by Date
3. **All time** (table) — Sort: Date desc
4. **Month stats** (table) — Filter: Date is within This month · Show Score with bar visualization

---

## BDD 5 — Reading list

**Use case** : suivi de livres, articles longs, podcasts.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Title | Title | — |
| Type | Select | 📖 Book / 📄 Article / 🎙️ Podcast / 🎬 Video |
| Status | Status | Wishlist / Reading / Done / DNF |
| Author | Text | — |
| Rating | Select | ⭐ / ⭐⭐ / ⭐⭐⭐ / ⭐⭐⭐⭐ / ⭐⭐⭐⭐⭐ |
| Genre | Multi-select | fiction / design / tech / biography / essay / fantasy |
| Started | Date | — |
| Finished | Date | — |
| Notes | Relation | → BDD Notes |
| Cover | Files | — |
| Link | URL | — |

### Vues

1. **Currently reading** (gallery) — Filter: `Status = Reading` · Card: Cover
2. **Wishlist** (gallery) — Filter: `Status = Wishlist` · Card: Cover
3. **Finished 2026** (gallery) — Filter: `Status = Done` AND `Finished is within This year` · Sort: Rating desc
4. **All-time favorites** (gallery) — Filter: `Rating = ⭐⭐⭐⭐⭐`

---

## BDD 6 — CRM léger / Network

**Use case** : contacts pro, réseau alternance, leads.

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Name | Title | — |
| Company | Text | — |
| Role | Text | — |
| Status | Status | Cold / Contacted / In talks / Warm / Closed |
| Type | Select | 🎯 Alternance / 💼 Freelance / 🤝 Partner / 👤 Mentor |
| LinkedIn | URL | — |
| Email | Email | — |
| Last contact | Date | — |
| Next action | Text | — |
| Notes | Text | — |

### Vues

1. **Next actions** (table) — Filter: Status ∈ {Contacted, In talks, Warm} · Sort: Last contact asc
2. **By status** (board) — Group by Status
3. **Alternance pipeline** (board) — Filter: `Type = Alternance` · Group by Status
4. **All contacts** (gallery)

---

## BDD 7 — Content calendar

**Use case** : pour les créateurs de contenu (LinkedIn, blog, portfolio posts).

### Propriétés

| Propriété | Type | Options |
|---|---|---|
| Title | Title | — |
| Platform | Multi-select | LinkedIn / Twitter / Blog / Portfolio / Newsletter |
| Status | Status | Idea / Draft / Ready / Scheduled / Published |
| Publish date | Date | — |
| Topic | Select | Design / Tech / Career / Process |
| Format | Select | Text post / Thread / Long-form / Case study / Carousel |
| Draft | Text | — |
| Final copy | Text | — |
| Link (published) | URL | — |

### Vues

1. **Calendar** — by Publish date
2. **Kanban** — Group by Status
3. **Backlog** — Filter: `Status = Idea`
4. **Published archive** (gallery) — Filter: `Status = Published`

---

## Règles communes aux BDD

1. **Toujours ≥ 2 vues.** Une table par défaut + au moins une vue filtrée/groupée.
2. **Status > Select pour les workflows.** Le type Status (nouveau dans Notion) permet des groupes "Not started / In progress / Completed" natifs.
3. **Relations bilatérales entre BDD sœurs.** Projects ↔ Tasks, Notes ↔ Projects, etc. Ça crée un vrai graphe interconnecté.
4. **Emojis dans les options des Select.** `🔴 High` > `High`. C'est plus lisible en board view.
5. **Rollups et formules pour les métriques.** Count de tasks par projet, % complétion, streaks — valeur énorme pour peu de setup.
6. **Templates de page dans la BDD.** Pour les BDD "répétitives" (Daily notes, Meeting notes, Project), créer un template = gain de temps énorme.
