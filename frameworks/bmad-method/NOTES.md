# BMAD-METHOD — fiche de référence

**Dépôt officiel :** https://github.com/bmad-code-org/BMAD-METHOD
**Licence :** MIT (voir `LICENSE.txt`, copie du `README.md` d'origine ci-joint)

## Pourquoi ce n'est pas un skill dans `.claude/skills/`

BMAD ("Breakthrough Method for Agile Ai Driven Development") est un
**framework complet**, pas un skill autonome. Son dépôt contient bien 48
fichiers `SKILL.md` (14 dans `src/core-skills/`, 34 dans `src/bmm-skills/`),
mais chacun dépend d'une infrastructure de projet installée par son propre
CLI :

- `_bmad/config.toml`, `_bmad/config.user.toml`, `_bmad/custom/*.toml`
- un script Python de résolution de config (`_bmad/scripts/resolve_config.py`)
- un catalogue CSV des skills installés (`_bmad/_config/*.csv`)
- des fichiers `customize.toml` fusionnés par skill

Copier ces `SKILL.md` tels quels dans `.claude/skills/<nom>/` — comme pour
les autres skills de cette bibliothèque — produirait des skills cassés :
ils référencent des chemins et scripts qui n'existent que si le framework a
été installé via son propre installeur.

## Ce qu'est BMAD, en résumé

Un framework de développement agile piloté par agents IA, avec :

- 12+ agents experts spécialisés (PM, Architecte, Dev, UX, QA...)
- des workflows structurés couvrant tout le cycle : analyse → planification
  → architecture ("solutioning") → implémentation
- un "Party Mode" pour faire collaborer plusieurs personas d'agents dans une
  même session
- des modules (`core`, `bmm` — BMad Method Module — et d'autres) chacun avec
  leurs propres skills/workflows

## Installation (dans un projet, pas dans cette bibliothèque)

```bash
npx bmad-method@next install
```

Puis ouvrir le projet dans son IDE agentique (Claude Code, Cursor, etc.) —
l'installeur met en place `_bmad/` et enregistre les skills/agents
nécessaires pour ce projet précis.

## À utiliser quand

Pour un projet logiciel entier que tu veux driver avec une méthode agile
structurée bout en bout (du brief produit jusqu'au code), pas pour une
tâche ponctuelle — c'est l'opposé du reste de cette bibliothèque, pensée
pour des skills unitaires et autonomes.
