# Note d'intégration

`caveman-stats` ne calcule rien lui-même : dans le dépôt d'origine, le
skill est un déclencheur (`/caveman-stats`) dont la sortie réelle est
produite par un hook Claude Code (`caveman-mode-tracker.js`, qui lit le
journal de session et appelle `caveman-stats.js` pour formater les chiffres).

Les deux scripts sont vendorisés ici dans `hooks/` pour référence. Pour que
`/caveman-stats` affiche réellement des chiffres, il faut enregistrer
`caveman-mode-tracker.js` comme hook Claude Code (`hooks` dans
`.claude/settings.json` du projet cible) — le déposer seulement dans
`.claude/skills/caveman-stats/` ne suffit pas à l'activer.
