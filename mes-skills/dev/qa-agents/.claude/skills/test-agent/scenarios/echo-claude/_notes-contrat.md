# Notes sur le contrat d'ECHO

Ambiguïtés relevées dans `CLAUDE.md` / `GEMINI.md` **avant** tout run. Si un
tour les déclenche, ce n'est pas une faute de l'agent : c'est une
recommandation à porter sur le prompt.

1. **Cadrage groupé ou questions une par une ?**
   Phase 0 impose « poser les 5 questions de cadrage en une fois », tandis que
   « Ce que tu ne fais jamais » interdit de « poser deux questions dans le même
   message ». Observer ce qu'ECHO fait réellement, et proposer de trancher —
   probablement en exemptant explicitement le cadrage initial.

2. **Autonomie contre validation.**
   « Tu prends les décisions, tu n'attends pas la permission » cohabite avec des
   Human Tasks de validation. La frontière n'est explicite que pour la Human
   Task #1. Regarder si ECHO redemande la permission ailleurs.

3. **Statuts de projet.**
   `references/state-schema.md` et `references/obsidian-structure.md` listent
   des statuts (`cadrage`, `preparation`, `terrain`, `analyse`, `termine`) sans
   dire lesquels s'appliquent au mode `survey_only`, qui n'a ni préparation ni
   terrain d'entretien.

4. **Deux implémentations à maintenir.**
   `references/` et `scripts/` sont dupliqués dans `Agent_claude-code_Echo/` et
   `Agent_gemini_Echo/`. Tout correctif issu d'un rapport doit être reporté des
   deux côtés, sinon les agents divergent en silence.
