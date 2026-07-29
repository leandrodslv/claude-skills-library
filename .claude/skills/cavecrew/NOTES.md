# Note d'intégration

`cavecrew` est un guide de décision qui délègue à trois sous-agents
caveman-compressés (`cavecrew-investigator`, `cavecrew-builder`,
`cavecrew-reviewer`). Dans le dépôt d'origine, ce sont des agents Claude Code
enregistrés séparément (`agents/*.md` à la racine du dépôt), pas des scripts
internes au skill.

Les définitions de ces 3 agents sont vendorisées ici dans `agents/` pour
référence. Pour qu'ils soient réellement invocables comme sous-agents, il
faut les copier dans `.claude/agents/` du projet cible (à côté de
`.claude/skills/`) — les déposer seulement dans `.claude/skills/cavecrew/`
ne suffit pas à les enregistrer comme agents.
