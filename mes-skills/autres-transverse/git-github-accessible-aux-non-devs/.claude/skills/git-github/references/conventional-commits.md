# Référence — Conventional Commits (spec + application)

Le message de commit n'est pas de la documentation : c'est une **entrée machine**.
`release-please` s'en sert pour calculer la version et écrire le CHANGELOG. Un commit
mal typé produit une version fausse et une release illisible. D'où trois couches
d'application, du plus proche au plus lointain :

```
1. L'agent valide le message avant de committer     (toujours, gratuit)
2. Hook commit-msg local                            (bloque avant le push)
3. Check CI sur le titre de PR                      (bloque avant le merge)  ← le seul incontournable
```

La couche 3 est la seule qui compte vraiment en mode squash-merge : c'est le **titre
de la PR** qui devient le message du commit sur `main`, pas les commits de la branche.

---

## 1. LA SPEC

```
<type>[(<scope>)][!]: <description>

[corps]

[footer(s)]
```

### Règles dures

| Règle | Détail |
|---|---|
| `type` | Obligatoire, minuscules, dans la liste ci-dessous |
| `scope` | Optionnel, entre parenthèses, minuscules, `a-z0-9._/-` |
| `!` | Optionnel, avant le `:` — marque un breaking change |
| `: ` | Deux-points **suivis d'une espace**, obligatoire |
| `description` | Obligatoire, impératif présent, minuscule initiale, **pas de point final** |
| En-tête | ≤ 72 caractères au total |
| Corps | Séparé par une ligne vide, explique le **pourquoi** |
| Footer | Séparé par une ligne vide : `Closes #12`, `BREAKING CHANGE: …`, `Co-Authored-By: …` |

### Regex de validation

```regex
^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\([a-z0-9._/-]+\))?!?: [^ ].{0,64}$
```

Test rapide :
```bash
echo "feat(auth): add magic link login" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\([a-z0-9._/-]+\))?!?: [^ ].{0,64}$' && echo OK || echo KO
```

---

## 2. LES TYPES

| Type | Quand | Version | Section CHANGELOG |
|---|---|---|---|
| `feat` | Nouvelle capacité visible par l'utilisateur | **minor** | ✨ Fonctionnalités |
| `fix` | Correction d'un comportement cassé | **patch** | 🐛 Corrections |
| `perf` | Même comportement, plus rapide / plus léger | **patch** | ⚡ Performance |
| `revert` | Annule un commit précédent | **patch** | ⏪ Reverts |
| `docs` | Documentation seule (README, commentaires, ADR) | — | 📚 Documentation |
| `refactor` | Réécriture sans changement de comportement | — | masqué |
| `style` | Formatage, espaces, points-virgules, ordre des imports | — | masqué |
| `test` | Ajout/modification de tests uniquement | — | masqué |
| `build` | Système de build, bundler, dépendances de build | — | masqué |
| `ci` | Workflows, pipelines, config CI | — | masqué |
| `chore` | Tout le reste : deps, config, ménage | — | masqué |

### Arbre de décision (à dérouler dans cet ordre)

```
Le comportement observable par l'utilisateur change-t-il ?
├── NON
│   ├── Seulement des tests ?              → test
│   ├── Seulement de la doc ?              → docs
│   ├── Seulement du formatage ?           → style
│   ├── .github/workflows/ ?               → ci
│   ├── bundler / build / deps de build ?  → build
│   ├── Code réorganisé, iso-comportement ? → refactor
│   └── Reste (deps, config, ménage)       → chore
└── OUI
    ├── Ça répare quelque chose de cassé ?  → fix
    ├── C'est plus rapide, iso-fonctionnel ? → perf
    ├── Ça annule un commit ?               → revert
    └── C'est nouveau                       → feat
        └── ... et ça casse l'existant ?    → feat! + BREAKING CHANGE:
```

**Pièges classiques** :
- Un `refactor` qui corrige un bug au passage est un `fix`. Le type suit l'effet, pas l'intention.
- Ajouter un test pour un bug qu'on corrige : un seul commit `fix`, pas `fix` + `test`.
- `chore` est le fourre-tout. Si tu hésites entre `chore` et autre chose, ce n'est pas `chore`.
- Mettre à jour une dépendance qui apporte une fonctionnalité aux utilisateurs → `feat`, pas `chore(deps)`.

---

## 3. LE SCOPE

Optionnel mais recommandé : c'est ce qui rend le CHANGELOG lisible.

### Inférence automatique depuis `git diff --name-only`

| Chemin touché | Scope |
|---|---|
| `src/components/**` | `components` |
| `src/pages/**`, `src/views/**` | `pages` |
| `src/lib/**`, `src/utils/**` | `lib` |
| `src/hooks/**` | `hooks` |
| `src/api/**`, `src/services/**` | `api` |
| `supabase/**`, `migrations/**` | `db` |
| `.github/**` | `ci` |
| `package.json`, `*.lock` | `deps` |
| `vite.config.*`, `tsconfig.*`, `.env.example` | `config` |
| `**/*.md`, `docs/**` | `docs` |
| Plusieurs domaines sans dominante | *omis* |

Règle pratique : **si le diff touche plus de 2 domaines, omettre le scope** —
un scope faux est pire qu'un scope absent. Et si le diff touche 5 domaines,
c'est probablement qu'il faut découper en plusieurs commits.

### Scopes fonctionnels

Mieux vaut un scope métier qu'un scope de dossier quand les deux existent :
`feat(auth)` est plus parlant que `feat(components)`.

---

## 4. BREAKING CHANGES

Deux notations, **équivalentes**, cumulables :

```
feat(api)!: remove /v1 endpoints
```
```
feat(api): move to /v2 endpoints

BREAKING CHANGE: /v1 est supprimé. Migrer les clients vers /v2 avant le 1er mars.
```

Le `!` est visible dans `git log --oneline`, le footer explique la migration.
**Utiliser les deux** pour un vrai breaking change.

⚠️ En 0.x, release-please bumpe la **minor** sur breaking change (0.3.0 → 0.4.0),
pas la major. Voir `release-please.md` §1.

---

## 5. FOOTERS

```
Closes #12                          ferme l'issue au merge sur main
Closes #12, closes #13              plusieurs issues (répéter le mot-clé)
Closes owner/repo#12                issue d'un autre repo
Refs #12                            référence sans fermer
BREAKING CHANGE: <description>      breaking change
Co-Authored-By: Nom <email>         co-auteur
Release-As: 2.0.0                   force une version (release-please)
```

Mots-clés de fermeture reconnus : `close/closes/closed`, `fix/fixes/fixed`,
`resolve/resolves/resolved`.

---

## 6. LE CORPS : QUOI Y METTRE

Le corps est optionnel. L'ajouter quand la ligne de titre ne suffit pas à comprendre
la décision dans six mois. Il répond au **pourquoi**, jamais au comment (le diff dit
déjà le comment).

```
fix(auth): expire magic link tokens after 15 minutes

Les tokens sans expiration restaient valides indéfiniment dans les boîtes mail,
ce qui transformait un ancien e-mail archivé en clé d'accès permanente.
15 minutes couvre le délai de livraison réel observé (p99 ≈ 40 s) avec une
marge large.

Closes #3
```

---

## 7. EXEMPLES

### Bons
```
feat(auth): add magic link login
fix(ui): resolve button alignment on mobile viewport
perf(reader): lazy-load page images below the fold
docs(readme): update installation steps for Windows
ci(workflows): split build into parallel lint and test jobs
chore(deps): bump react from 18.2 to 18.3
refactor(api): extract user validation to dedicated service
feat(auth)!: replace password login with magic link
revert: "feat(auth): add magic link login"
```

### Mauvais, et pourquoi
| Message | Problème |
|---|---|
| `Update files` | Pas de type, description vide de sens |
| `feat: Added new feature.` | Passé + majuscule + point final ; et « new feature » ne dit rien |
| `fix: bug` | Quel bug ? Inutilisable dans un CHANGELOG |
| `FEAT(UI): ...` | Type et scope en majuscules |
| `feat:add login` | Espace manquante après les deux-points |
| `feat(auth) add login` | Deux-points manquants |
| `wip` | `wip` n'est pas un type ; utiliser un commit draft ou `chore:` |
| `feat: add login, fix navbar, update deps` | Trois changements en un commit → trois commits |

---

## 8. INSTALLER LA VALIDATION

### Couche 2 — hook local

**Option A : hook natif (zéro dépendance, local à la machine)**

```bash
cp ~/.claude/skills/git-github/assets/hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Le hook est dans `.git/hooks/`, donc **non versionné** : il ne protège que ta machine.
Suffisant pour un projet solo.

**Option B : commitlint + husky (versionné, partagé par l'équipe)**

```bash
npm i -D @commitlint/cli @commitlint/config-conventional husky
npx husky init
cp ~/.claude/skills/git-github/assets/commitlint.config.js .
echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
git add .husky commitlint.config.js package.json package-lock.json
git commit -m "chore: enforce conventional commits with commitlint"
```

Vérifier :
```bash
echo "mauvais message" | npx commitlint     # doit échouer
echo "feat(auth): add login" | npx commitlint  # doit passer
```

### Couche 3 — check CI sur le titre de PR ⭐

C'est **la** protection qui compte avec un merge en squash.

```bash
mkdir -p .github/workflows
cp ~/.claude/skills/git-github/assets/workflows/pr-title.yml .github/workflows/
git add .github/workflows/pr-title.yml
git commit -m "ci: validate pull request titles as conventional commits"
git push
```

Puis le rendre obligatoire (protection de branche) :
```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -F required_status_checks[strict]=true \
  -f 'required_status_checks[contexts][]=PR Title' \
  -F enforce_admins=false \
  -F required_pull_request_reviews=null \
  -F restrictions=null
```

---

## 9. RÉÉCRIRE UN MESSAGE FAUTIF

```bash
# Dernier commit, pas encore poussé
git commit --amend -m "feat(auth): add magic link login"

# Un commit plus ancien (rebase interactif → 'reword')
git rebase -i HEAD~3

# Déjà poussé sur une branche perso
git push --force-with-lease origin <branche>
```

⚠️ Jamais de réécriture sur `main` ni sur une branche partagée. Si un mauvais message
est déjà sur `main` : le laisser, et corriger le CHANGELOG à la main dans la PR de release.

Si un commit non conventionnel est déjà sur `main` et pollue la release, il n'apparaîtra
simplement pas dans le CHANGELOG — release-please ignore ce qu'il ne sait pas parser.
Le risque n'est pas le crash, c'est le silence.
