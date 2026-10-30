# Référence — Questionnaire / Sondage quantitatif UX

## Structure type d'un questionnaire (10-15 min, 10-20 questions)

### Principe général
Un bon questionnaire UX quantitatif doit être :
- **Court** : 10-15 min max (taux d'abandon augmente fortement au-delà)
- **Progressif** : du général au spécifique
- **Mixte** : majorité de questions fermées + 1-2 ouvertes à la fin
- **Non biaisé** : ordre des options randomisé quand possible

---

## Types de questions à utiliser

### Questions de profil (2-3 max, en début)
Objectif : segmenter les réponses.
- Fréquence d'usage : "À quelle fréquence utilisez-vous [service] ?"
- Profil : ancienneté, type de client, canal préféré

### Questions de comportement (3-5 questions)
Objectif : mesurer des usages réels.
- "Parmi les situations suivantes, lesquelles vous sont déjà arrivées ?" (cases à cocher)
- "Dans quel contexte réalisez-vous habituellement [action] ?" (choix unique)

### Questions de satisfaction / perception (3-5 questions)
Objectif : mesurer l'expérience actuelle.
- Échelle de satisfaction : Likert 1-5 ou 1-7
- NPS ponctuel : "Sur une échelle de 0 à 10, recommanderiez-vous X ?"
- Sémantique différentielle : "Ce service vous semble : Compliqué ←→ Simple"

### Questions sur le concept / capa (3-5 questions)
Objectif : valider la pertinence et la compréhension.
- "Parmi ces fonctionnalités, laquelle vous semblerait la plus utile ?" (max diff ou ranking)
- "Dans quelle mesure seriez-vous susceptible d'utiliser cette fonctionnalité ?" (Likert)
- "Qu'est-ce qui vous freinerait à utiliser cette fonctionnalité ?" (cases à cocher + autre)

### Questions ouvertes (1-2 max, en fin)
Objectif : recueillir du verbatim qualitatif.
- "Y a-t-il quelque chose que vous souhaiteriez ajouter sur ce sujet ?"
- "Qu'est-ce qui rendrait cette fonctionnalité vraiment utile pour vous ?"

---

## Échelles recommandées

| Usage | Échelle recommandée |
|-------|-------------------|
| Satisfaction globale | 1-5 (Très insatisfait → Très satisfait) |
| Fréquence | Jamais / Rarement / Parfois / Souvent / Toujours |
| Accord | Pas du tout d'accord → Tout à fait d'accord (5 niveaux) |
| Probabilité d'usage | Très peu probable → Très probable (5 niveaux) |
| Effort perçu (CES) | 1-7 (Très difficile → Très facile) |

---

## Erreurs fréquentes à éviter

- **Double-barrelled** : "Ce service est-il rapide et facile ?" → séparer en 2 questions
- **Questions négatives** : "N'avez-vous jamais eu de problème ?" → reformuler positivement
- **Échelles asymétriques** : toujours autant de réponses positives que négatives
- **Trop d'ouvertes** : fatigue le répondant et complexifie l'analyse
- **Ordre biaisé** : toujours randomiser l'ordre des options de réponse si possible

---

## Template de structure pour un questionnaire de 15 questions

```
[Introduction] Présentation, durée, confidentialité

[Section 1 - Profil] Q1-Q2 : profil du répondant
[Section 2 - Usage actuel] Q3-Q6 : comportements et satisfaction actuelle  
[Section 3 - Concept] Q7-Q11 : réaction au concept / à la capa
[Section 4 - Priorités] Q12-Q13 : priorisation des fonctionnalités
[Section 5 - Verbatim] Q14-Q15 : questions ouvertes

[Conclusion] Remerciements, suite donnée à l'étude
```
