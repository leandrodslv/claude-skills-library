---
title: Cantine — réservation des repas
created: 2026-03-20
updated: 2026-03-20
---

# PRD : Cantine — réservation des repas
*Titre de travail — à confirmer.*

## 0. Objet du document
PRD destiné à la directrice, à la mairie et à l'équipe qui réalisera l'application. Il est construit uniquement à partir de trois sources : `notes-reunion-2026-03-12.md`, `cahier-des-charges-cantine.md` et `courriel-mairie.md`. Vocabulaire ancré dans le glossaire ; hypothèses signalées en ligne `[ASSUMPTION: …]` et listées à la fin. Sources : notes-reunion-2026-03-12.md, cahier-des-charges-cantine.md, courriel-mairie.md.

## 1. Vision
Les parents de l'école des Tilleuls réservent et annulent les repas de leurs enfants depuis leur téléphone, en quelques secondes, au lieu d'une feuille papier remplie le lundi matin (source : notes-reunion-2026-03-12.md, § Problème).

Pour l'école et la mairie, la commande du jeudi repose enfin sur des réservations à jour : moins d'oublis, moins de repas gâchés (source : notes-reunion-2026-03-12.md, § Problème).

## 2. Utilisateurs cibles

### 2.1 Besoins (Jobs To Be Done)
- Parent : ne plus oublier de réserver et pouvoir corriger depuis son téléphone (source : notes-reunion-2026-03-12.md, § Problème).
- Agent de cantine : savoir combien de repas préparer et quelles allergies surveiller (source : cahier-des-charges-cantine.md, § 3.3).
- Agent de mairie : recevoir la commande dans un format exploitable (source : courriel-mairie.md).

### 2.2 Non-utilisateurs (v1)
- Les élèves eux-mêmes ne se connectent pas (aucune source ne les mentionne comme utilisateurs) [ASSUMPTION: les enfants n'ont pas de compte].

### 2.3 Parcours clés
- **UJ-1. Nadia réserve la semaine de ses deux enfants le dimanche soir.**
  - **Persona + contexte :** Nadia, parent de deux élèves, peu à l'aise avec le numérique, sur son téléphone (source : cahier-des-charges-cantine.md, § 2 et § 4).
  - **État d'entrée :** reçoit un rappel et ouvre le lien magique reçu par e-mail (source : notes-reunion-2026-03-12.md, § Décisions).
  - **Parcours :** choisit « toute la semaine », coche les jours pour chaque enfant, valide (source : courriel-mairie.md, remarque 2).
  - **Point culminant :** un écran confirme les repas réservés avec leur total.
  - **Résolution :** elle ferme l'application ; un rappel lui sera envoyé avant la fin des réservations.
  - **Cas limite :** si elle réserve moins de 48 h avant un repas, un message prévient qu'il sera facturé s'il n'est pas annulé à temps.

- **UJ-2. Mme Roux prépare la commande du jeudi.**
  - **Persona + contexte :** la directrice supervise la commande hebdomadaire (source : notes-reunion-2026-03-12.md, § Problème).
  - **État d'entrée :** jeudi matin, avant 12 h.
  - **Parcours :** consulte le nombre de repas par jour et la liste des allergies ; le récapitulatif part seul à la mairie à 12 h (source : cahier-des-charges-cantine.md, § 3.3 et § 3.4).
  - **Point culminant :** la mairie reçoit un tableur sans intervention manuelle (source : courriel-mairie.md, remarque 1).
  - **Résolution :** la commande est passée sans ressaisie.

## 3. Glossaire
- **Parent** — Responsable légal d'un ou plusieurs **Élèves** ; seul à pouvoir réserver. Une famille compte au plus 3 enfants [ASSUMPTION: limite de 3 retenue, voir Questions ouvertes n°1].
- **Élève** — Enfant demi-pensionnaire rattaché à un **Parent**.
- **Réservation** — Repas demandé pour un **Élève** un jour donné ; peut être annulée jusqu'à 48 h avant.
- **Récapitulatif de commande** — Liste des **Réservations** de la semaine suivante envoyée à la mairie le jeudi à 12 h.
- **Agent de cantine** — Personne qui consulte les repas et les allergies du jour.

## 4. Fonctionnalités

### 4.1 Réservation des repas
**Description :** Un **Parent** réserve ou annule des **Réservations** pour ses **Élèves**, sur un jour ou sur toute la semaine. Réalise UJ-1.

**Exigences fonctionnelles :**

#### FR-1 : Réserver un repas
Un **Parent** peut réserver un repas pour un jour donné et pour chacun de ses **Élèves**. Réalise UJ-1. (source : cahier-des-charges-cantine.md, § 3.1)

**Conséquences (testables) :**
- Après validation, la **Réservation** apparaît dans la liste du **Parent**.
- Une **Réservation** déjà existante pour le même **Élève** et le même jour n'est pas dupliquée.

#### FR-2 : Réserver plusieurs jours d'un coup
Un **Parent** peut réserver plusieurs jours en une seule action (« toute la semaine »). Réalise UJ-1. (source : courriel-mairie.md, remarque 2)

**Conséquences (testables) :**
- Une seule validation crée une **Réservation** par jour et par **Élève** coché.

#### FR-3 : Annuler une réservation
Un **Parent** peut annuler une **Réservation** jusqu'à 48 h avant le repas ; au-delà, le repas est facturé. Réalise UJ-1. (sources : cahier-des-charges-cantine.md, § 3.2 ; notes-reunion-2026-03-12.md, § Décisions)

**Conséquences (testables) :**
- L'annulation est refusée avec un message explicite à moins de 48 h du repas.
- Une **Réservation** annulée à temps n'apparaît plus dans le **Récapitulatif de commande**.

#### FR-4 : Se connecter par lien magique
Un **Parent** se connecte en recevant un lien par e-mail, sans mot de passe. Réalise UJ-1. (source : notes-reunion-2026-03-12.md, § Décisions)

**Conséquences (testables) :**
- Le lien ne permet qu'un seul accès [ASSUMPTION: usage unique et durée de validité courte, non précisées dans les sources].

**Hors périmètre :**
- Le paiement en ligne (voir §5).

### 4.2 Suivi cantine et commande
**Description :** L'**Agent de cantine** et la directrice consultent les repas à préparer ; la mairie reçoit le **Récapitulatif de commande**. Réalise UJ-2.

**Exigences fonctionnelles :**

#### FR-5 : Voir les repas et les allergies du jour
Un **Agent de cantine** voit, pour chaque jour, le nombre de repas et la liste des allergies signalées. Réalise UJ-2. (source : cahier-des-charges-cantine.md, § 3.3)

**Conséquences (testables) :**
- Le total affiché égale le nombre de **Réservations** non annulées du jour.

#### FR-6 : Envoyer le récapitulatif à la mairie
Le système envoie à la mairie, chaque jeudi à 12 h, le **Récapitulatif de commande** de la semaine suivante, au format tableur CSV. Réalise UJ-2. (sources : cahier-des-charges-cantine.md, § 3.4 ; notes-reunion-2026-03-12.md, § Décisions ; courriel-mairie.md, remarque 1)

**Conséquences (testables) :**
- Le fichier joint est un CSV lisible par un tableur.
- Il ne contient aucune **Réservation** annulée.

### 4.3 Rappels
**Description :** Les **Parents** sont prévenus avant la fin des réservations. Réalise UJ-1.

**Exigences fonctionnelles :**

#### FR-7 : Rappel avant la fin des réservations
Un **Parent** reçoit un rappel la veille de la fin des réservations. Réalise UJ-1. (source : cahier-des-charges-cantine.md, § 3.5)

**Conséquences (testables) :**
- Le rappel n'est pas envoyé à un **Parent** qui a déjà réservé toute la semaine [ASSUMPTION: règle d'évitement des rappels inutiles, non demandée par les sources].

**Exigences non fonctionnelles propres à cette fonctionnalité :**
- **NFR-1** : les rappels sont envoyés le jour prévu même un jeudi de commande. (source : cahier-des-charges-cantine.md, § 4)

## 4bis. Exigences non fonctionnelles transverses
- **NFR-2** : l'application fonctionne le jeudi matin, jour de commande. (source : cahier-des-charges-cantine.md, § 4)
- **NFR-3** : une réservation s'enregistre en moins de 3 secondes. (source : cahier-des-charges-cantine.md, § 4)
- **NFR-4** : conformité RGPD pour les données d'enfants, hébergement en France. (source : cahier-des-charges-cantine.md, § 4)
- **NFR-5** : utilisable par des parents peu à l'aise avec le numérique (RGAA). (source : cahier-des-charges-cantine.md, § 4)

## 5. Non-objectifs
- Pas de paiement en ligne : les familles paient en mairie (source : notes-reunion-2026-03-12.md, § Hors périmètre).
- Pas de menus personnalisés par enfant : seul un champ « allergies » libre existe (source : notes-reunion-2026-03-12.md, § Hors périmètre).

## 6. Périmètre MVP

### 6.1 Dans le périmètre
- Réservation, annulation, connexion par lien magique, suivi cantine, récapitulatif hebdomadaire à la mairie, rappels.

### 6.2 Hors périmètre du MVP
- Paiement en ligne ; menus personnalisés. [NON-GOAL for MVP]

## 7. Indicateurs de succès
Les sources ne donnent aucun objectif chiffré ; les indicateurs ci-dessous sont des propositions à valider.

**Principaux**
- **SM-1** : part des repas commandés réellement consommés [ASSUMPTION: indicateur proposé, aucune cible dans les sources]. Valide FR-1, FR-3, FR-6.

**Secondaires**
- **SM-2** : part des familles ayant réservé au moins une semaine [ASSUMPTION: indicateur proposé]. Valide FR-1, FR-2, FR-7.

**Contre-indicateurs (à ne pas optimiser)**
- **SM-C1** : nombre de rappels envoyés par parent — ne pas l'augmenter pour faire monter SM-2. Contrebalance SM-2.

## 8. Questions ouvertes
1. Combien d'enfants au maximum par famille ? M. Vidal dit 3, Inès dit « jusqu'à 5 » (sources en conflit : notes-reunion-2026-03-12.md, § À trancher).
2. Durée de validité et usage unique du lien magique (non précisés).
3. Cibles chiffrées des indicateurs de succès (aucune dans les sources).
4. Quelles allergies sont à signaler à l'agent de cantine : champ libre seulement, ou liste ? (cahier-des-charges-cantine.md, § 3.3 et notes-reunion-2026-03-12.md divergent en précision).

## 9. Index des hypothèses
- §2.2 — les enfants n'ont pas de compte.
- §3 Glossaire — limite de 3 enfants par famille.
- FR-4 — lien à usage unique, durée courte.
- FR-7 — pas de rappel à un parent ayant déjà tout réservé.
- SM-1 — indicateur « repas consommés ».
- SM-2 — indicateur « familles actives ».
