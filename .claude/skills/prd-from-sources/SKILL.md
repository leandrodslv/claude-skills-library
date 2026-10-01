---
name: prd-from-sources
description: Rédige un PRD (Product Requirements Document) au format BMAD à partir de documents sources déjà convertis en Markdown (dossier produit par le skill to-markdown, INDEX.md, notes de réunion, cahier des charges, deck produit, e-mails). Chaque exigence cite le fichier d'origine, ce qui manque est listé en « Questions ouvertes », rien n'est inventé. À utiliser quand l'utilisateur veut un PRD, un cahier des charges structuré, des exigences fonctionnelles/non fonctionnelles, des epics et user stories à partir de documents — « fais-en un PRD », « transforme ces notes en PRD », « PRD BMAD », « extrais les exigences » — même sans le mot PRD. Ne convertit pas les fichiers : pour cela, to-markdown d'abord.
---

# prd-from-sources — des sources Markdown vers un PRD (format BMAD)

Un PRD fidèle à ses sources : tout ce qu'il affirme renvoie à un fichier, tout ce qui manque est dit.

## Règles

1. **Rien d'inventé.** Une exigence, un chiffre, une échéance ou un utilisateur cible n'entre dans le PRD que s'il figure dans une source. Sinon : `[À CONFIRMER]` dans le texte et une ligne dans « Questions ouvertes ».
2. **Chaque exigence cite sa source** : `(source : cahier-des-charges.md, § Paiement)`. Plusieurs sources → toutes citées. Une déduction de ta part est étiquetée `[déduit]` avec le raisonnement en une phrase.
3. **Sources fragiles signalées.** Un passage venant d'une lecture visuelle (`<!-- lu visuellement -->`), d'un OCR sous 90 % ou d'un marqueur `[À COMPLÉTER]` restant est cité avec `⚠` ; vérifie `_report.json` (`vision_needed`, avertissements) s'il est présent.
4. **Contradictions entre sources** : ne tranche pas. Liste les deux versions avec leurs fichiers dans « Questions ouvertes ».
5. **Langue** : celle des sources (français par défaut). Garde les termes métier tels qu'écrits.

## Marche à suivre

1. **Inventaire.** Lis `INDEX.md` (ou liste les `.md`) et `_report.json` s'ils existent. Si l'utilisateur donne des fichiers non convertis (Word, PDF…), arrête-toi : passe d'abord par le skill `to-markdown`.
2. **Pertinence.** Si une source n'est pas un document de besoin (contrat, tableau de données, rapport sans lien avec le produit), dis-le et demande si elle doit entrer dans le PRD. N'invente pas un produit à partir de contenu qui n'en parle pas.
3. **Extraction.** Lis les sources utiles en entier. Relève : problème et contexte, objectifs, utilisateurs, exigences, contraintes (techniques, légales, délais, budget), hors périmètre, risques, décisions déjà prises.
4. **Cadrage rapide.** Si l'utilisateur n'a pas dit le niveau voulu, une seule question : PRD complet (avec epics et stories) ou version courte (jusqu'aux exigences) ? Par défaut : complet.
5. **Rédaction** selon `references/gabarit-bmad.md` (sections, numérotation FR/NFR, epics et stories avec critères d'acceptation). Écris dans `prd.md` à côté des sources (ou à l'endroit demandé), pas dans le terminal.
6. **Contrôle** avant de livrer : chaque FR/NFR a une source ou un `[À CONFIRMER]` ; les epics couvrent tous les FR ; aucun chiffre sans source ; « Questions ouvertes » à jour ; la table de traçabilité en fin de document est remplie.
7. **Livrer** : chemin du `prd.md`, nombre d'exigences, **combien reposent sur des sources fragiles ou sur une déduction**, et les 3 questions ouvertes les plus bloquantes. Ne recopie pas le PRD dans la réponse.

## Ce que le PRD ne fait pas

Il ne choisit pas l'architecture ni la technologie (sauf si une source l'impose, citée), ne fixe pas de priorités ou de calendrier absents des sources, ne remplace pas la validation par les parties prenantes. Les suites naturelles BMAD (architecte, UX) sont proposées en « Prochaines étapes », pas lancées.
