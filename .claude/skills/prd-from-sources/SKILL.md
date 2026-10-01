---
name: prd-from-sources
description: Rédige un PRD (Product Requirements Document) au format BMAD officiel à partir de documents sources déjà convertis en Markdown (dossier produit par le skill to-markdown, INDEX.md, notes de réunion, cahier des charges, deck produit, e-mails). Chaque exigence cite le fichier d'origine, ce qui manque devient hypothèse ou question ouverte, rien n'est inventé ; un vérificateur (check_prd.py) contrôle sources, orphelins et références. À utiliser quand l'utilisateur veut un PRD, un cahier des charges structuré, des exigences fonctionnelles/non fonctionnelles, des parcours utilisateurs à partir de documents — « fais-en un PRD », « transforme ces notes en PRD », « PRD BMAD », « extrais les exigences » — même sans le mot PRD. Ne convertit pas les fichiers : pour cela, to-markdown d'abord.
---

# prd-from-sources — des sources Markdown vers un PRD (format BMAD)

Un PRD fidèle à ses sources : tout ce qu'il affirme renvoie à un fichier, tout ce qui manque est dit, et un script le vérifie.

Gabarit : **officiel BMAD** (`references/bmad-prd-template.md`, skill `bmad-prd`, MIT — voir `references/NOTICE-BMAD.md`). Grille de qualité officielle : `references/bmad-prd-quality-rubric.md`. Exemple complet : `examples/cantine/` (3 sources + le `prd.md` attendu).

## Règles

1. **Rien d'inventé.** Une exigence, un chiffre, une échéance ou un utilisateur n'entre dans le PRD que s'il figure dans une source. Sinon : balise BMAD `[ASSUMPTION: …]` en ligne, reprise dans l'Index des hypothèses, et/ou une entrée dans Questions ouvertes.
2. **Chaque FR, chaque NFR cite sa source** : `(source : fichier.md, § section)` ; plusieurs sources → `(sources : a.md, § 2 ; b.md)`. Un FR qui ne repose que sur une hypothèse est permis mais compté comme tel dans le bilan.
3. **Sources fragiles signalées** avec `⚠` : passage lu visuellement (`<!-- lu visuellement -->`), OCR sous 90 %, marqueur `[À COMPLÉTER]` restant (voir `_report.json`).
4. **Contradictions entre sources** : ne tranche pas. Les deux versions, avec leurs fichiers, vont dans Questions ouvertes.
5. **Vocabulaire du Glossaire** utilisé tel quel partout (le gabarit BMAD l'exige) ; pas de synonyme.
6. **Langue** : celle des sources (français par défaut). Les identifiants restent `FR-n`, `NFR-n`, `UJ-n`, `SM-n`, `SM-Cn`.

## Marche à suivre

1. **Inventaire.** Lis `INDEX.md` (ou liste les `.md`) et `_report.json` s'ils existent. Fichiers non convertis (Word, PDF…) : arrête-toi, passe par le skill `to-markdown`.
2. **Pertinence.** Une source qui n'est pas un document de besoin (contrat, tableau de données…) : dis-le et demande si elle entre dans le PRD.
3. **Extraction.** Lis les sources utiles en entier. Relève : problème, objectifs, utilisateurs, exigences, contraintes, hors périmètre, risques, décisions prises, points non tranchés.
4. **Cadrage.** Si le niveau n'est pas donné, une seule question : PRD complet ou léger (hobby/outil interne : sections minimales, rigueur des sources identique) ? Défaut : complet. Le menu « Adapt-In » du gabarit (conformité, contraintes, intégrations…) : n'ajoute un bloc que si les sources en parlent.
5. **Rédaction** selon le gabarit : Objet du document (cite les sources lues) → Vision → Utilisateurs (besoins, parcours `UJ-n` avec personnage nommé) → Glossaire → Fonctionnalités (chaque fonctionnalité : description, puis FR numérotés globalement avec « Conséquences (testables) » et « Réalise UJ-n ») → Non-objectifs → Périmètre MVP → Indicateurs (`SM-n` « Valide FR-n », contre-indicateurs `SM-Cn`) → Questions ouvertes → Index des hypothèses. NFR transverses : section dédiée après les fonctionnalités. Écris `prd.md` à côté des sources (ou où l'utilisateur le demande), jamais en vrac dans le terminal. Petit périmètre (1-2 stories) : bloc « Stories » du gabarit.
6. **Vérifier avec le script** (obligatoire avant de livrer) :
   ```bash
   python3 scripts/check_prd.py prd.md --sources <dossier des .md> --strict
   ```
   Il contrôle : source présente et fichier cité existant pour chaque FR/NFR, aucun FR hors fonctionnalité, aucune fonctionnalité vide, epics (s'il y en a) couvrant tous les FR, références résolues, identifiants uniques et continus, parcours réalisés, indicateurs reliés à des FR, hypothèses en ligne = index, glossaire et questions ouvertes présents, aucun `{champ}` du gabarit resté vide. Corrige jusqu'à sortie 0 ; un avertissement que tu gardes volontairement se justifie dans ta réponse.
7. **Relecture de fond** avec la grille `references/bmad-prd-quality-rubric.md` (aide à la décision, substance, cohérence, clarté du « terminé », honnêteté du périmètre, exploitabilité, forme adaptée) : le script vérifie la mécanique, pas la qualité. Note honnêtement ce qui reste faible.
8. **Livrer** : chemin du `prd.md`, résultat de `check_prd.py`, **combien d'exigences reposent sur une hypothèse ou une source fragile**, et les questions ouvertes les plus bloquantes. Ne recopie pas le PRD dans la réponse.

## Ce que le PRD ne fait pas

Il ne choisit pas l'architecture ni la technologie (sauf si une source l'impose, citée), ne fixe ni priorités ni calendrier absents des sources, ne remplace pas la validation par les parties prenantes. Les suites BMAD (UX, architecture, découpage en epics/stories) sont proposées, pas lancées.

## Tests

`python3 -m unittest discover -s tests` (vérificateur : l'exemple passe, chaque défaut introduit est détecté).
