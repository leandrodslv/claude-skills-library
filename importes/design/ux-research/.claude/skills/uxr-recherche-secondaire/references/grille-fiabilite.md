# Grille de fiabilité des sources

Objectif : noter chaque source de façon reproductible, pour que deux lecteurs
arrivent à la même note. On évalue la source **pour la sous-question posée**, pas
dans l'absolu : une excellente étude hors sujet reste peu pertinente.

## Sommaire
1. Les 5 critères
2. Notes A / B / C / D
3. Signaux d'alerte
4. Fraîcheur selon le domaine
5. Indépendance et triangulation
6. Niveau de confiance d'un insight

---

## 1. Les 5 critères

| Critère | Questions à se poser |
|---|---|
| **Actualité** | Date de publication ? Période réelle de collecte des données (souvent 1-2 ans avant) ? Le domaine a-t-il changé depuis ? |
| **Pertinence** | Même public, pays, secteur, contexte d'usage que notre question ? Répond-elle à une sous-question précise ? |
| **Autorité** | Qui publie (organisme, laboratoire, institut, média) ? Auteur identifiable et compétent ? Relue par des pairs ou soumise à un contrôle ? |
| **Méthode** | Méthode explicite ? Taille et mode de recrutement de l'échantillon ? Questionnaire ou protocole consultable ? Limites reconnues ? |
| **Finalité** | Qui finance ? Un intérêt commercial ou militant à obtenir ce résultat ? Étude publiée pour vendre un produit ou un service ? |

## 2. Notes

| Note | Profil type | Usage |
|---|---|---|
| **A** | Statistique officielle, publication à comité de lecture, étude institutionnelle avec méthode et échantillon publiés | Fonde un insight |
| **B** | Rapport sectoriel ou d'association avec méthode partielle, étude privée sérieuse, revue systématique non relue | Fonde un insight, avec réserve notée |
| **C** | Article d'expert, billet de blog documenté, étude sans méthode détaillée, verbatims publics (avis, forums) | Illustre ou signale une piste ; ne fonde pas seul un insight |
| **D** | Chiffre sans source ni date, contenu marketing, étude de vendeur sans méthode, page non datée, contenu généré sans trace | Écartée (listée avec la raison) |

En cas de doute entre deux notes, retenir la plus basse et écrire pourquoi.

**Notes par type de source atypique :**

| Type | Note habituelle | Remarque |
|---|---|---|
| Normes et textes officiels | A pour ce que le texte exige | N'établit aucun usage réel |
| Données de demande (Trends, suggestions) | B pour une tendance relative, C si la méthode est floue | Mesure un intérêt, pas un besoin |
| Contenus publics des acteurs (FAQ, changelogs, offres d'emploi) | B pour un fait vérifiable (tarif daté, fonctionnalité existante), C pour les pratiques déclarées | Discours de l'acteur |
| Retours d'expérience, talks, podcasts | C | Biais de survivant |
| Littérature grise | B si la méthode est publiée, sinon C | Noter le positionnement de l'auteur |
| Preprints | B si la méthode est claire, sinon C | Noter "non relu" |
| Archives (Wayback Machine) | A ou B pour établir qu'une page existait à une date | Captures parfois incomplètes |
| Wikipédia | Non notée | Porte d'entrée : on note les sources qu'elle cite |

## 3. Signaux d'alerte

- Chiffre "X % des utilisateurs…" sans base (X % de combien de personnes ? lesquelles ?)
- Sondage en ligne auto-sélectionné présenté comme représentatif
- Étude publiée par l'entreprise qui vend la solution recommandée
- Même chiffre repris partout sans lien vers l'origine (circularité)
- Date absente, ou chiffre ancien présenté au présent
- Corrélation présentée comme causalité
- Petit échantillon qualitatif extrapolé en pourcentages
- Résultat d'un pays ou d'un public transposé sans précaution
- Moyenne qui masque des écarts entre segments
- Titre plus affirmatif que le contenu de l'étude
- Corpus social : bots, contenus sponsorisés ou d'influence, fils viraux, brigading,
  fils anciens présentés comme actuels, communauté non représentative du public visé

Chaque signal repéré se note dans la colonne "limites" du registre.

## 4. Fraîcheur selon le domaine

Repères indicatifs, à ajuster : une source plus ancienne n'est pas écartée
d'office, mais sa date doit apparaître.

| Domaine | Au-delà de… | Traitement |
|---|---|---|
| IA, outils numériques, usages mobiles, réseaux sociaux | 2-3 ans | Signaler comme potentiellement périmé |
| Comportements de consommation, e-commerce, médias | 3-4 ans | Idem |
| Santé, éducation, travail, politiques publiques | 5 ans | Vérifier qu'aucune réforme n'a changé la donne |
| Psychologie cognitive, perception, principes d'ergonomie | souvent stable | Une étude fondatrice ancienne reste valable |
| Normes et réglementations | en vigueur ou non | Toujours vérifier la version actuelle |

## 5. Indépendance et triangulation

- Deux articles qui citent la même étude comptent pour **une** source.
- Une confirmation vient d'une autre méthode ou d'un autre organisme, pas d'un
  second écho.
- Triangulation solide : au moins deux types de sources différents (ex. statistique
  officielle + étude académique, ou étude quantitative + verbatims publics).
- Quand deux sources se contredisent, chercher d'abord ce qui les distingue
  (année, population, définition de l'indicateur, méthode) avant de trancher.

## 6. Niveau de confiance d'un insight

| Confiance | Condition |
|---|---|
| **Fort** | ≥ 3 sources indépendantes notées A/B, convergentes, dont ≥ 2 types différents, applicables à notre contexte |
| **Moyen** | 2 sources indépendantes A/B convergentes, ou plusieurs sources dont certaines C ; ou applicabilité à transposer |
| **Faible** | 1 source A/B, ou sources C seulement, ou contradictions non expliquées |

**Corpus social** (Reddit, Instagram, forums, avis) : source C. Seul, il plafonne
à *faible*. Il peut monter à *moyen* si le même thème ressort d'au moins deux
plateformes ou communautés différentes, chacune avec un corpus suffisant
(≥ 30 contenus lus, ≥ 3 requêtes), daté et dénombré. Un corpus mince (10 à 29)
reste illustratif et plafonné à *faible* ; sous 10, il n'est pas exploitable. Il
ne justifie jamais une confiance *forte* sans source A/B.

Un insight à confiance faible reste utile : il devient une hypothèse à tester
en recherche primaire (livrable 7).
