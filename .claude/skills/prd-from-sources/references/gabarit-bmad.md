# Gabarit PRD (format BMAD)

Structure du PRD « classique » de la méthode BMAD, reproduite de mémoire : si votre version de BMAD diffère (les versions récentes ont un déroulé en étapes), adaptez les sections ici — le skill suit ce fichier.

Chaque ligne d'exigence se termine par sa source : `(source : fichier.md, § titre)`.

```markdown
# <Produit> — Product Requirements Document (PRD)

> Sources : liste des fichiers lus (avec ⚠ pour les passages fragiles) · Date · Statut : brouillon

## 1. Objectifs et contexte
### Objectifs
- Résultats attendus, un par ligne (source).
### Contexte
Problème, utilisateurs, situation actuelle — quelques paragraphes sourcés.
### Journal des modifications
| Date | Version | Description | Auteur |

## 2. Exigences
### Fonctionnelles
- **FR1** : Le système doit … (source)
### Non fonctionnelles
- **NFR1** : performance, sécurité, conformité, disponibilité, accessibilité… (source)

## 3. Objectifs de design d'interface (si les sources en parlent)
Vision UX globale · paradigmes d'interaction · écrans principaux · accessibilité · marque · plateformes cibles.

## 4. Hypothèses techniques (si les sources en parlent)
Structure du dépôt · architecture de service · tests requis · autres hypothèses imposées par les sources.

## 5. Liste des epics
- **Epic 1 — <titre>** : objectif en une phrase.

## 6. Détail des epics
### Epic 1 — <titre>
Objectif détaillé.
#### Story 1.1 — <titre>
En tant que <rôle>, je veux <action>, afin de <bénéfice>.
**Critères d'acceptation**
1. …
(Chaque story : réalisable seule, valeur claire, critères testables, tirés des sources ; sinon [À CONFIRMER].)

## 7. Hors périmètre
Ce que les sources excluent explicitement.

## 8. Risques et dépendances
## 9. Questions ouvertes
| # | Question | Pourquoi bloquant | Sources en conflit ou manquantes |

## 10. Traçabilité
| Exigence / story | Source(s) | Fiabilité (sûre / ⚠ fragile / [déduit]) |

## 11. Prochaines étapes
- Revue par les parties prenantes · Prompt pour l'architecte · Prompt pour l'UX (si pertinent)
```

Règles de remplissage : section sans aucune matière dans les sources → `Non couvert par les sources` (ne pas combler) ; numérotation FR/NFR continue ; une story par résultat vérifiable ; pas de priorité (MoSCoW, P0…) sauf si une source la donne.
