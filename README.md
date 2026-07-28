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

| Skill | Ce qu'il fait | Télécharger |
|---|---|---|
| [`test-agent`](.claude/skills/test-agent/SKILL.md) | Banc d'essai pour agent IA. Analyse en profondeur le prompt d'un agent visé, se spécialise pour lui en générant des scénarios de test taillés sur mesure, le lance pour de vrai dans un bac à sable (Claude Code, Gemini CLI, ou toute commande), dialogue avec lui tour par tour, et produit un rapport ✅ / ❌ / recommandations plus un tableau de bord local. Inclut un exemple complet de bout en bout (analyse, profil, 8 scénarios) construit sur l'agent ECHO. | [.zip](archives/test-agent.zip) |
| [`academic-pptx-skill`](.claude/skills/academic-pptx-skill/SKILL.md) | Structure et contenu de présentations académiques (colloques, soutenances, comités de financement, séminaires) — gouverne le fond et l'organisation, pas la mise en forme technique du `.pptx`. | [.zip](archives/academic-pptx-skill.zip) |
| [`speech-script`](.claude/skills/speech-script/SKILL.md) | Transforme des idées ou un plan en script de discours narratif, prêt à être prononcé — pour présentations orales, conférences, discours d'entreprise. | [.zip](archives/speech-script.zip) |
| [`ui-ux-pro-max`](.claude/skills/ui-ux-pro-max/SKILL.md) | Base de données consultable d'intelligence UI/UX : 84 styles, 192 palettes, 74 associations de polices, 98 règles UX, 104 icônes, presets d'animation GSAP, sur 22 stacks techniques. Génère un design system complet et argumenté à partir d'une description de produit. |  [.zip](archives/ui-ux-pro-max.zip) |
| [`banner-design`](.claude/skills/banner-design/SKILL.md) | Conception de bannières (réseaux sociaux, pubs, hero de site, print) avec plusieurs pistes de direction artistique et visuels générés par IA. | [.zip](archives/banner-design.zip) |
| [`brand`](.claude/skills/brand/SKILL.md) | Voix de marque, identité visuelle, cadres de messages, cohérence de marque sur les contenus et assets marketing. | [.zip](archives/brand.zip) |
| [`design`](.claude/skills/design/SKILL.md) | Skill de design large : identité de marque, tokens, logos, kit d'identité corporate, présentations HTML, bannières, icônes, visuels sociaux. | [.zip](archives/design.zip) |
| [`design-system`](.claude/skills/design-system/SKILL.md) | Architecture de tokens à trois couches (primitif → sémantique → composant), spécifications de composants, génération stratégique de slides. | [.zip](archives/design-system.zip) |
| [`slides`](.claude/skills/slides/SKILL.md) | Présentations HTML stratégiques avec Chart.js, tokens de design, mise en page responsive, formules de copywriting. | [.zip](archives/slides.zip) |
| [`ui-styling`](.claude/skills/ui-styling/SKILL.md) | Interfaces accessibles avec shadcn/ui (Radix + Tailwind), thèmes, dark mode, composants accessibles (dialogs, formulaires, tableaux). | [.zip](archives/ui-styling.zip) |
| [`impeccable`](.claude/skills/impeccable/SKILL.md) | Guidance de design frontend pour agents IA : 23 commandes (`polish`, `audit`, `critique`, `distill`, `animate`, `bolder`, `quieter`…), itération live dans le navigateur, 60 règles de détection déterministes contre les tics visuels génériques des IA (Inter partout, dégradés violet-bleu, cartes imbriquées…). | [.zip](archives/impeccable.zip) |

**`impeccable` vient d'un dépôt tiers** :
[pbakaus/impeccable](https://github.com/pbakaus/impeccable) (licence Apache
2.0, incluse via `LICENSE.txt` ; `NOTICE.md` copié aussi — deux fichiers de
référence de ce skill, `reference/ios.md` et `reference/android.md`, sont
eux-mêmes distillés d'un troisième projet sous licence MIT, crédité dans
`NOTICE.md`). Aucun correctif nécessaire à l'import : les chemins sont déjà
écrits en relatif au projet, sans dépendre d'une variable d'environnement de
plugin. Un script fait référence à `react` comme dépendance externe — sans
incidence hors d'un projet React qui l'a déjà dans son `node_modules`.

**Les 7 skills `ui-ux-pro-max` à `ui-styling` viennent d'un dépôt tiers** :
[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(licence MIT, incluse dans chacun de ces dossiers via `LICENSE.txt`). Un
correctif leur a été apporté à l'import : leur `SKILL.md` appelait son script
via `${CLAUDE_PLUGIN_ROOT}`, une variable que Claude Code ne définit que pour
une installation via `/plugin install` — remplacée par un chemin relatif qui
fonctionne aussi en copie manuelle (le mode d'installation de cette
bibliothèque). Le reste du code (`core.py`) résolvait déjà ses données via son
propre chemin de fichier, sans dépendre de cette variable.

À savoir : `banner-design` mentionne dans sa description des skills
compagnons (`frontend-design`, `ai-artist`, `ai-multimodal`) qui ne font
**pas** partie de ce dépôt tiers et ne sont donc pas dans cette bibliothèque —
il fonctionnera, mais sans ces capacités additionnelles.

---

## Télécharger un seul skill

Chaque skill a sa propre archive dans `archives/` — pas besoin de cloner tout
le dépôt pour en récupérer un seul :

1. Clique sur le lien `.zip` de la table ci-dessus (ou ouvre directement
   `archives/<nom-du-skill>.zip` sur GitHub).
2. Bouton **Download** (ou **⋯ → Download**) sur la page du fichier.
3. Dézippe dans `.claude/skills/<nom-du-skill>/` du projet où tu veux
   l'utiliser — le zip contient directement `SKILL.md` et les fichiers
   annexes à la racine, sans dossier parasite au-dessus.

Ces archives sont régénérées à chaque modification d'un skill : si le
contenu d'un dossier change, retélécharge son `.zip` pour rester à jour.

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
