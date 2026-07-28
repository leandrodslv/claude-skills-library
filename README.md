# Bibliothèque de skills

C'est mon espace personnel de skills pour Claude Code — un dépôt unique où je
range tous les skills que j'utilise ou que je construis, pour ne pas les
perdre d'un projet à l'autre et pouvoir les réutiliser n'importe où.

Chaque skill vit dans son propre dossier sous `.claude/skills/`, avec un
`SKILL.md` qui décrit quand et comment Claude Code doit l'utiliser. C'est la
convention standard de Claude Code : n'importe quel projet qui embarque un
dossier `.claude/skills/<nom>/SKILL.md` rend ce skill disponible via
`/<nom>`.

---

## Skills dans la bibliothèque

| Skill | Ce qu'il fait |
|---|---|
| [`test-agent`](.claude/skills/test-agent/SKILL.md) | Banc d'essai pour agent IA. Analyse en profondeur le prompt d'un agent visé, se spécialise pour lui en générant des scénarios de test taillés sur mesure, le lance pour de vrai dans un bac à sable (Claude Code, Gemini CLI, ou toute commande), dialogue avec lui tour par tour, et produit un rapport ✅ / ❌ / recommandations plus un tableau de bord local. Inclut un exemple complet de bout en bout (analyse, profil, 8 scénarios) construit sur l'agent ECHO. |
| [`academic-pptx-skill`](.claude/skills/academic-pptx-skill/SKILL.md) | Structure et contenu de présentations académiques (colloques, soutenances, comités de financement, séminaires) — gouverne le fond et l'organisation, pas la mise en forme technique du `.pptx`. |
| [`speech-script`](.claude/skills/speech-script/SKILL.md) | Transforme des idées ou un plan en script de discours narratif, prêt à être prononcé — pour présentations orales, conférences, discours d'entreprise. |

---

## Utiliser un skill d'ici dans un autre projet

Copie le dossier du skill dans le nouveau projet :

```
MonProjet/
└── .claude/
    └── skills/
        └── <nom-du-skill>/    ← copié depuis ce dépôt
```

Claude Code le découvre automatiquement au lancement suivant — la commande
`/<nom-du-skill>` devient disponible.

Pour le rendre disponible **partout**, sans le copier projet par projet, place-le
plutôt dans le dossier utilisateur global :

```
~/.claude/skills/<nom-du-skill>/
```

## Ajouter un skill à la bibliothèque

1. Crée `.claude/skills/<nom>/SKILL.md` avec un bloc frontmatter `name` +
   `description` en tête de fichier.
2. Ajoute les fichiers annexes dont le skill a besoin (scripts, gabarits,
   références) dans le même dossier.
3. Commit et push.

Le nom du dossier **doit** être exactement celui utilisé dans `name:` — c'est
lui qui détermine la commande slash.
