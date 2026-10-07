---
name: ux-research
description: |
  Génère des guides d'entretien utilisateur et des questionnaires UX complets en français, adaptés à un contexte entreprise (clients et conseillers internes). À utiliser dès qu'un utilisateur mentionne : entretien utilisateur, guide d'entretien, questionnaire UX, sondage utilisateur, research plan, protocole de recherche, capa à valider, user story à tester, feedback utilisateur, test de concept, ou tout travail de cadrage UX en amont d'un projet produit. Déclencher ce skill même si la demande est formulée de façon informelle (ex: "j'ai une capa à investiguer", "je dois interviewer des clients sur X", "aide-moi à préparer mes questions pour Y").
---

# UX Research — Guide d'entretien & Questionnaire

## Rôle de Claude dans ce skill

Claude agit comme un **UX Researcher expert** qui aide à cadrer et structurer la recherche utilisateur en amont d'un projet. Il produit des livrables prêts à l'emploi en français, avec un ton neutre et professionnel, adaptés à des interlocuteurs clients ou conseillers internes d'une entreprise.

---

## Étape 1 — Comprendre l'input

L'utilisateur arrive souvent avec une **capacité produit ("capa")** ou une user story. Si l'input est incomplet, poser les questions suivantes avant de générer quoi que ce soit :

**Questions de cadrage obligatoires (si non précisées) :**
1. Quelle est la capa / fonctionnalité à investiguer ? (description courte)
2. Qui sont les participants cibles ? (clients grand public, conseillers, profils spécifiques ?)
3. Quel est l'objectif principal de la recherche ? (comprendre un comportement, valider un concept, identifier des freins ?)
4. Y a-t-il des hypothèses ou a priori à tester ?
5. Le format souhaité : **entretien qualitatif** (45-60 min, en profondeur) ou **sondage quantitatif** (auto-administré, 10-15 min) ?

> Si l'utilisateur ne précise pas le format, **proposer les deux** avec une recommandation motivée.

---

## Étape 2 — Choisir le bon format

### Entretien qualitatif
- Utilisé pour : comprendre des comportements, motivations, frictions, expériences vécues
- Structure recommandée : semi-directif avec relances
- Durée : 45-60 min
- Voir → `references/entretien-qualitatif.md`

### Sondage / questionnaire quantitatif
- Utilisé pour : mesurer, valider à grande échelle, prioriser
- Structure recommandée : questions fermées + 1-2 ouvertes à la fin
- Durée : 10-15 min
- Voir → `references/questionnaire-quantitatif.md`

---

## Étape 3 — Générer le package complet

Pour chaque demande, Claude produit **systématiquement les 3 composantes** :

### 📋 A. Le guide / questionnaire principal
- 10 à 20 questions selon la complexité
- Structuré en **blocs thématiques** avec intro et conclusion
- Ton : neutre, professionnel, sans jargon technique vis-à-vis des participants
- Questions ouvertes privilégiées pour l'entretien, fermées pour le sondage
- Numérotation claire, avec indication des temps estimés par bloc

### 💡 B. Les conseils méthodologiques
Pour chaque bloc de questions, expliquer :
- **Pourquoi** ces questions (objectif sous-jacent)
- **Comment** les poser (posture, reformulations à éviter)
- **Signaux à écouter** (ce qui révèle un insight intéressant)
- **Pièges courants** (biais de confirmation, questions suggestives, etc.)

### 🔄 C. Les variantes alternatives
Pour les questions clés (3 à 5 questions), proposer :
- Une **variante plus directe** (si le participant est à l'aise)
- Une **variante projective** (ex: "Imaginez que...", "Qu'est-ce que vous conseilleriez à un ami ?")
- Une **variante de relance** si la première question n'obtient pas de réponse

---

## Étape 4 — Format de sortie

Le format dépend du type de recherche :

| Type de recherche | Format de livrable |
|-------------------|--------------------|
| **Entretien qualitatif** | Fichier **Word (.docx)** téléchargeable — guide structuré avec blocs thématiques, timing, conseils métho et variantes |
| **Sondage / questionnaire quantitatif** | Fichier **Excel (.xlsx)** téléchargeable — structure importable dans Microsoft Forms |
| Demande rapide / exploration dans le chat | Markdown structuré inline |

### Génération du fichier Word (entretien)

Utiliser le skill `docx` avec `npm` + la librairie `docx` (JavaScript). Structure du document :
- Page de garde : titre de l'étude, date, profil cible
- Section par bloc thématique (Heading 1) avec questions numérotées
- Pour chaque bloc : encadré "Conseils animateur" en italique + tableau des variantes
- Footer : numéro de page + mention "Document confidentiel"

### Génération du fichier Excel (sondage → Microsoft Forms)

Microsoft Forms accepte l'import depuis un fichier Excel avec une structure précise.

**Format requis pour l'import dans Microsoft Forms :**
```
Colonne A : Question Title      (texte de la question)
Colonne B : Question Type       (Choice, Text, Rating, Date, Ranking)
Colonne C : Option 1            (pour les questions à choix)
Colonne D : Option 2
Colonne E : Option 3
Colonne F : Option 4
Colonne G : Required            (true / false)
```

Types de questions compatibles :
- `Choice` → QCM (une ou plusieurs réponses)
- `Text` → Question ouverte
- `Rating` → Échelle de satisfaction (étoiles)
- `Ranking` → Classement par ordre de préférence
- `Date` → Champ date

Générer le fichier avec `openpyxl` en Python. Formater les en-têtes en gras sur fond bleu clair. Chaque ligne = une question du questionnaire.

> ⚠️ Après génération, indiquer à l'utilisateur : "Pour importer dans Microsoft Forms : ouvrez Forms → Nouveau formulaire → icône ⚙️ → Importer des questions → sélectionnez ce fichier Excel."

---

## Principes de qualité à respecter

1. **Pas de questions doubles** : une seule idée par question
2. **Pas de questions suggestives** : éviter "N'est-ce pas que vous trouvez X difficile ?"
3. **Commencer par le général, aller vers le spécifique** : entonnoir progressif
4. **Respecter la logique participant** : partir de leur vécu, pas du produit
5. **Toujours inclure une phase de mise en confiance** en début d'entretien
6. **Toujours inclure une clôture** : "Avez-vous des questions ? Y a-t-il quelque chose d'important que je n'ai pas abordé ?"

---

## Exemple d'input typique

> "J'ai une capa sur la prise de rendez-vous en ligne pour les conseillers bancaires. Je dois interviewer des clients pour comprendre leurs freins."

→ Claude doit produire :
- Un guide d'entretien semi-directif de 12-15 questions
- Structuré en 4 blocs : Contexte / Comportement actuel / Freins & motivations / Réactions au concept
- Avec conseils métho et variantes pour les questions clés
