---
name: git-github
description: >
  Expert Git & GitHub automation pour Léandro. Gère tout le workflow Git : status, staging,
  commits conventionnels validés, push, pull, branches, tags — ET la partie GitHub : issues,
  pull requests de bout en bout (création ET review), GitHub Actions (CI/CD), Dependabot et
  alertes de sécurité, GitHub Projects, et releases automatisées via release-please.
  Déclencher dès que l'utilisateur mentionne : "commit mes changements", "push sur github",
  "crée une branche", "fais un commit", "synchro git", "versionne mon code", "sauvegarde sur
  github", "git status" — côté commits : "conventional commit", "valide mes messages de
  commit", "installe commitlint", "mes commits sont mal formatés" — côté garde-fous locaux :
  "lance les tests avant de push", "installe un hook pre-push", "empêche de pousser du code
  cassé" — côté PR : "crée une PR", "gère ma PR", "merge ma PR", "où en est ma PR", "ma PR a
  des conflits", "protège ma branche main", "ajoute des reviewers obligatoires", "relis cette
  PR", "review la PR de X", "approuve cette PR" — côté issues : "crée une issue", "liste mes
  issues", "code l'issue 3", "ferme cette issue" — côté CI/CD : "mes tests CI plantent",
  "pourquoi le build a échoué", "regarde les actions", "relance le workflow", "crée un
  workflow", "accélère mon CI" — côté sécurité/dépendances : "mets en place dependabot", "il
  y a des vulnérabilités", "faille de sécurité dans une dépendance", "merge les PR
  dependabot" — côté suivi : "mon board github", "mon kanban de projet", "avancement du
  milestone" — côté release : "mets en place release-please", "crée une release", "automatise
  mes versions", "génère mon changelog", "déploie". Fonctionne dans n'importe quel répertoire
  projet et adapte les messages de commit au contenu des changements. Toujours utiliser ce
  skill plutôt qu'une réponse générique dès qu'une action Git ou GitHub est demandée.
---

# Git & GitHub Automation Skill

Ce skill couvre **une seule chaîne**, de bout en bout :

```
issue → branche → commits conventionnels VALIDÉS → PR → CI vert → squash-merge
                                                                        ↓
                          release-please : PR de release → tag → CHANGELOG → deploy
```

Chaque maillon dépend du précédent. Le message de commit n'est pas de la décoration :
c'est l'entrée machine qui produit la version et le CHANGELOG. D'où la règle centrale
de ce skill : **aucun commit n'est créé sans avoir passé la porte de validation (§4).**

---

## 1. DÉCOUVERTE DU CONTEXTE

Avant toute action :

```bash
git -C <path> rev-parse --show-toplevel 2>/dev/null || echo "PAS UN REPO GIT"
git status --porcelain          # état du working tree
git branch --show-current       # branche courante
git remote -v                   # remote(s)
git log --oneline -5            # derniers commits
```

Avant toute action GitHub (issue, PR, Actions, release) :

```bash
gh auth status 2>/dev/null || echo "gh non disponible → gh auth login"
gh repo view --json nameWithOwner,defaultBranchRef -q '.nameWithOwner + " (" + .defaultBranchRef.name + ")"'
```

Si pas de repo git → proposer `git init` + `git remote add origin <url>`.

---

## 2. WORKFLOW STANDARD

```bash
git status && git diff --stat        # 1. voir ce qui a changé
git add .                            # 2. stager
# 3. générer le message ET LE VALIDER (§4)
git commit -m "type(scope): description"
git push origin <branche-courante>   # 4. pusher
```

---

## 3. ACTIONS DISPONIBLES

| Intention | Où |
|---|---|
| "commit mes changements" / "push" | §2 + §4 |
| "valide / force mes conventional commits" | §5 |
| "lance les tests avant de push" / hook pre-push | §6 |
| "crée / liste / ferme une issue" | §7 |
| **"code l'issue N"** | §8 ⭐ |
| "crée / gère / merge ma PR" | §9 |
| "relis / review la PR de X" | §9g |
| "protège ma branche main" / reviewers obligatoires | §9f |
| "le CI plante" / "crée un workflow" / "accélère le build" | §10 |
| "mets en place dependabot" / "des vulnérabilités ?" | §11 |
| "mets en place release-please" | §12 ⭐ |
| "nouvelle branche" | §13 |
| "mon board / kanban github" | §14 |
| "voir l'historique" | `git log --oneline --graph -20` |
| "annuler / revenir" | `references/actions.md` |

---

## 4. PORTE DE VALIDATION DES COMMITS 🚦

**Obligatoire avant chaque `git commit`.** Ne jamais committer un message qui n'a pas
passé ces cinq contrôles.

```
<type>[(<scope>)][!]: <description>
```

| # | Contrôle | Règle |
|---|---|---|
| 1 | **Type** | Dans : `feat` `fix` `perf` `revert` `docs` `style` `refactor` `test` `build` `ci` `chore` |
| 2 | **Syntaxe** | Deux-points **suivis d'une espace**. Scope entre parenthèses, minuscules. |
| 3 | **Description** | Impératif présent, minuscule initiale, **pas de point final** |
| 4 | **Longueur** | En-tête ≤ 72 caractères |
| 5 | **Atomicité** | Un seul changement logique. Trois choses dans le diff → trois commits. |

Vérification mécanique — la lancer sur le message généré :

```bash
MSG="feat(auth): add magic link login"
echo "$MSG" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\([a-z0-9._/-]+\))?!?: [^ ].{0,64}$' \
  && [ ${#MSG} -le 72 ] && echo "✅ valide" || echo "❌ invalide"
```

### Choisir le type — arbre court

```
Le comportement observable change-t-il ?
├── NON → tests seuls: test · doc: docs · formatage: style
│         .github/: ci · bundler/deps de build: build
│         réorg iso-comportement: refactor · reste: chore
└── OUI → répare du cassé: fix · plus rapide: perf · annule: revert
          nouveau: feat  (+ `!` et footer BREAKING CHANGE si ça casse l'existant)
```

Pièges : un `refactor` qui corrige un bug au passage est un **`fix`** (le type suit
l'effet, pas l'intention). Si tu hésites entre `chore` et autre chose, ce n'est pas `chore`.

### Impact sur la version

| Commits | Bump release-please |
|---|---|
| `fix` / `perf` / `revert` | **patch** — 0.1.0 → 0.1.1 |
| au moins un `feat` | **minor** — 0.1.0 → 0.2.0 |
| au moins un `!` ou `BREAKING CHANGE:` | **major** — 1.3.0 → 2.0.0 (⚠️ en 0.x → minor) |
| uniquement `docs`/`chore`/`style`/`test`/`refactor`/`ci`/`build` | aucune release |

### Scope

Inférer depuis `git diff --name-only` : `src/components/**` → `components`,
`src/hooks/**` → `hooks`, `supabase/**` → `db`, `.github/**` → `ci`,
`package.json` → `deps`, `**/*.md` → `docs`.
**Plus de 2 domaines touchés → omettre le scope** (un scope faux est pire qu'absent).
Préférer toujours un scope métier (`auth`) à un scope de dossier (`components`).

### Footers

`Closes #12` (ferme l'issue au merge) · `BREAKING CHANGE: …` · `Refs #12` ·
`Release-As: 2.0.0`. Toujours dans le **corps**, jamais dans le titre.

Spec complète, exemples commentés, contre-exemples → `references/conventional-commits.md`

---

## 5. FAIRE RESPECTER LES CONVENTIONAL COMMITS

Trois couches. La 3 est la seule incontournable en squash-merge, parce que c'est
le **titre de la PR** qui devient le commit sur `main`.

| Couche | Quoi | Portée |
|---|---|---|
| 1 | L'agent applique la porte §4 | toujours, gratuit |
| 2 | Hook `commit-msg` local | bloque avant le push, ta machine seulement |
| 3 | **Check CI sur le titre de PR** ⭐ | bloque avant le merge, pour tout le monde |

### Installer la couche 2 — hook natif (zéro dépendance)

```bash
cp ~/.claude/skills/git-github/assets/hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Variante versionnée et partagée (commitlint + husky) → `references/conventional-commits.md` §8

### Installer la couche 3 — check CI ⭐

```bash
mkdir -p .github/workflows
cp ~/.claude/skills/git-github/assets/workflows/pr-title.yml .github/workflows/
git add .github/workflows/pr-title.yml
git commit -m "ci: validate pull request titles as conventional commits"
git push
```
Puis le rendre obligatoire → §8f.

### Corriger un message fautif

```bash
git commit --amend -m "feat(auth): add magic link login"   # dernier commit
git rebase -i HEAD~3                                       # plus ancien → 'reword'
git push --force-with-lease origin <branche>               # branche perso uniquement
```
⚠️ Jamais de réécriture sur `main` ni sur une branche partagée.

---

## 6. GARDE-FOUS AVANT PUSH (lint & tests)

Le hook `commit-msg` (§5) valide la forme du message. Il ne dit rien sur le fond :
rien n'empêche de pousser du code qui casse le lint ou les tests. C'est le rôle du
hook `pre-push`.

```bash
cp ~/.claude/skills/git-github/assets/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Il lance `npm run lint`, `npm run typecheck`, `npm run test` — **uniquement les scripts
qui existent réellement** dans `package.json` (rien à configurer, un projet sans script
`test` ne bloque jamais dessus). Si aucun `package.json` n'est présent, le hook ne fait
rien (no-op, pas d'erreur).

Contourner ponctuellement : `git push --no-verify`.

⚠️ Local seulement — comme tout hook, il ne protège que la machine où il est installé.
Le CI (§10) reste le seul filet garanti pour tout le monde.

---

## 7. ISSUES

```bash
gh issue list --state open --limit 20
gh issue list --assignee @me --label bug
gh issue view 3 --comments            # ⭐ toujours --comments : le périmètre réel est dans la discussion
gh issue create --title "feat: connexion par lien magique" --body-file ./issue.md --label enhancement
gh issue edit 3 --add-assignee @me --add-label in-progress
gh issue comment 3 --body "Implémenté dans #14."
gh issue close 3 --comment "Livré en v1.3.0"
gh issue develop 3 --checkout --name feat/3-magic-link   # branche rattachée à l'issue
```

Titrer l'issue avec le préfixe conventionnel (`feat:`, `fix:`) : il devient le titre
de la PR, donc le commit squashé, donc la ligne du CHANGELOG.

Labels, milestones, templates, création en batch, Projects → `references/issues.md`

---

## 8. WORKFLOW "CODE L'ISSUE N" ⭐

Quand Léandro dit "code l'issue 3", "attaque l'issue 11", dérouler intégralement :

```bash
gh issue view 3 --comments                    # 1. LIRE — c'est la spec, ne jamais deviner
git status --porcelain                        # 2. base propre
git checkout main && git pull --rebase origin main
git checkout -b feat/3-magic-link-login       # 3. brancher
gh issue edit 3 --add-assignee @me            # 4. s'assigner
```

**5. Implémenter** — respecter les conventions du projet, suivre les critères
d'acceptation un par un, ne pas élargir le périmètre.

```bash
# 6. commits atomiques, chacun passé par la porte §4
git commit -m "feat(auth): add magic link token generation"
git commit -m "test(auth): cover magic link expiry and single use"

# 7. PR liée à l'issue
git push -u origin feat/3-magic-link-login
gh pr create --base main \
  --title "feat(auth): replace password login with magic link" \
  --body "$(printf '## Résumé\nRemplace le mot de passe par un lien magique signé.\n\n## Tests\n- [x] Expiration et usage unique\n\nCloses #3\n')"

gh pr checks --watch                          # 8. attendre le vert
```

Naming : `feat/<numéro>-<slug>`, `fix/<numéro>-<slug>`.
Après merge : `git checkout main && git pull --rebase && git branch -d <branche> && git fetch --prune`.
L'issue se ferme seule grâce au `Closes #3`.

**Parallélisation** : une issue = une branche, toujours repartie de `main` à jour,
jamais d'une autre branche feature.

---

## 9. PULL REQUESTS

### 8a. Créer

```bash
gh pr create --base main --fill                    # titre/corps depuis les commits
gh pr create --base main --title "feat(scope): ..." --body-file ./body.md --assignee @me
gh pr create --draft                               # brouillon
```

⚠️ **Le titre doit passer la porte §4** — c'est lui qui devient le commit sur `main`.
`Closes #N` va dans le **corps**, jamais dans le titre.

### 8b. Suivre

```bash
gh pr status                        # tes PR + celles à relire
gh pr view 14 --comments
gh pr checks 14 --watch
gh pr diff 14 --name-only
gh pr view 14 --json mergeable,mergeStateStatus,reviewDecision
```

`mergeStateStatus` : `CLEAN` (mergeable) · `BLOCKED` (review/check manquant) ·
`BEHIND` (en retard sur main → §8d) · `DIRTY` (conflits) · `DRAFT`.

### 8c. Modifier

```bash
gh pr edit 14 --title "..." --add-label enhancement --add-reviewer alice
gh pr ready 14                      # draft → prêt
git commit -m "fix(auth): handle expired token" && git push    # mettre à jour = pousser
```

### 8d. Conflits / retard sur main

```bash
gh pr update-branch 14              # merge de main (côté GitHub)
# ou en local, historique plus propre :
git fetch origin && git rebase origin/main
git diff --name-only --diff-filter=U   # ... résoudre ... git add ... git rebase --continue
git push --force-with-lease
```

### 8e. Merger

```bash
gh pr merge 14 --squash --delete-branch      # ⭐ le défaut
gh pr merge 14 --squash --auto               # merge dès que les checks passent
```

**Checklist avant merge** — les cinq, sans exception :
1. `gh pr checks 14` tout vert
2. Titre conventionnel valide (§4)
3. `Closes #N` présent si la PR répond à une issue
4. Aucun secret ni fichier généré dans `gh pr diff 14 --name-only`
5. Stratégie `--squash`

⚠️ Toujours **demander confirmation** avant un merge — c'est irréversible côté historique
et ça peut déclencher un déploiement.

### 9f. Configurer le dépôt (une fois par projet)

```bash
# Squash exclusif + titre du squash = titre de la PR  ← RÉGLAGE CLÉ pour release-please
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F allow_auto_merge=true -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY

# CODEOWNERS — qui doit relire quoi. Nécessaire pour require_code_owner_reviews ci-dessous.
mkdir -p .github
cp ~/.claude/skills/git-github/assets/CODEOWNERS .github/CODEOWNERS
git add .github/CODEOWNERS && git commit -m "chore: add CODEOWNERS"

# Protection de branche (récupérer d'abord les noms exacts des checks)
gh pr checks <n> --json name -q '.[].name'
gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input - <<'EOF'
{ "required_status_checks": { "strict": true, "contexts": ["CI", "PR Title"] },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "restrictions": null, "required_linear_history": true }
EOF
```

Sans `squash_merge_commit_title=PR_TITLE`, GitHub écrit `Titre (#14)` ou concatène les
messages → CHANGELOG déraillé.

⚠️ **Projet solo** : mettre `"required_pull_request_reviews": null`. GitHub interdit
l'auto-approbation — une review obligatoire bloquerait *tous* tes merges tant que
personne d'autre n'a accès au repo. Activer ce réglage seulement quand un deuxième
contributeur rejoint le projet.

### 9g. Relire (review) la PR d'un autre

```bash
gh pr checkout 14                       # récupérer la branche en local pour tester
gh pr diff 14
gh pr review 14 --approve
gh pr review 14 --request-changes --body "Le token n'est pas invalidé après usage."
gh pr review 14 --comment --body "Question sur le choix du TTL."
```

Traiter les retours reçus sur ses propres PR :
```bash
gh pr view 14 --comments              # tout lire, y compris la discussion inline
git commit -m "fix(auth): invalidate token after first use" && git push
gh pr comment 14 --body "Corrigé en $(git rev-parse --short HEAD)."
```
Répondre à chaque commentaire, même bref — un commentaire sans réponse bloque la review.

Reviews en détail, PR empilées, template de PR, requêtes avancées → `references/pull-requests.md`

---

## 10. GITHUB ACTIONS (CI/CD)

### 9a. Debug d'un CI rouge — dans cet ordre

```bash
gh run list --limit 5                      # 1. localiser
gh run view <id> --log-failed              # 2. ⭐ lire l'erreur RÉELLE, jamais la supposer
# 3. reproduire la commande exacte en local
# 4. corriger → commit fix(ci): … ou fix(scope): …
gh pr checks --watch                       # 5. confirmer
```

Autres commandes : `gh run watch <id>` · `gh run rerun <id> --failed` ·
`gh run rerun <id> --debug` · `gh run cancel <id>` · `gh cache delete --all` ·
`gh workflow run deploy.yml --ref main -f environment=production`

### 9b. Créer un workflow

```bash
mkdir -p .github/workflows
cp ~/.claude/skills/git-github/assets/workflows/ci.yml .github/workflows/
```
CI parallélisé prêt à l'emploi : lint en garde rapide, build caché, job final `ci-ok`
comme unique required check (stable quand on ajoute des jobs).

### 9c. Accélérer un CI lent

Par ordre de rendement : **paralléliser** les jobs (40-60 %) · **fail fast** via `needs:` ·
**cache** des deps et du build · `concurrency` + `cancel-in-progress` · filtres `paths` ·
**artefacts partagés** (le deploy consomme le build, ne le refait pas) · sharding des tests.

Toujours **mesurer avant/après** :
```bash
gh run view <id> --json jobs -q '.jobs[] | "\(.name): \(((.completedAt|fromdate)-(.startedAt|fromdate)))s"'
```

### 9d. Secrets

```bash
gh secret set VERCEL_TOKEN          # saisie interactive, jamais en clair
gh secret list
```
Jamais de secret en dur dans un YAML. Toujours `${{ secrets.NOM }}`.

Templates deploy/Pages, matrices, workflows réutilisables, permissions, `actionlint`
→ `references/github-actions.md`

---

## 11. DEPENDABOT & ALERTES DE SÉCURITÉ

### Installer Dependabot (mises à jour de dépendances)

```bash
mkdir -p .github
cp ~/.claude/skills/git-github/assets/dependabot.yml .github/dependabot.yml
git add .github/dependabot.yml
git commit -m "ci(deps): enable dependabot"
git push
```

Ouvre une PR par mise à jour avec un titre `chore(deps): ...` conventionnel — donc pas
de release pour un simple bump patch/minor. Une mise à jour qui corrige une faille
mérite un titre `fix(deps): ...` pour déclencher une release.

### Traiter une PR Dependabot

```bash
gh pr list --author app/dependabot
gh pr view <n> --comments                       # changelog du package, breaking changes
gh pr checks <n> --watch
gh pr merge <n> --squash --auto --delete-branch  # une fois les checks verts
```

Auto-merger sans relire n'est raisonnable que sur **patch/minor**, CI vert. Un **major**
se relit comme une PR normale — breaking changes possibles.

Automatiser ce tri (`.github/workflows/dependabot-auto-merge.yml`) :
```yaml
name: Dependabot auto-merge
on: pull_request
permissions: { contents: write, pull-requests: write }
jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: dependabot/fetch-metadata@v2
        id: meta
      - if: steps.meta.outputs.update-type != 'version-update:semver-major'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Alertes de sécurité (Dependabot alerts, secret scanning)

```bash
# Vulnérabilités ouvertes, triées par sévérité
gh api repos/{owner}/{repo}/dependabot/alerts -q \
  '.[] | select(.state=="open") | "\(.security_advisory.severity)\t#\(.number)\t\(.security_advisory.summary)"' \
  | sort

# Détail d'une alerte + version corrigée
gh api repos/{owner}/{repo}/dependabot/alerts/<n> \
  -q '.security_vulnerability.first_patched_version.identifier'

# Secrets accidentellement commités (nécessite le secret scanning activé sur le repo)
gh api repos/{owner}/{repo}/secret-scanning/alerts -q '.[] | select(.state=="open")'
```

⚠️ Une alerte `critical`/`high` ouverte sur la branche par défaut passe **avant** toute
autre tâche en cours — corriger ou upgrader immédiatement, ne pas attendre le prochain
cycle Dependabot.

Config avancée (groupes, ignore, monorepo) → `references/github-actions.md` §10

---

## 12. RELEASE-PLEASE ⭐

```
commits conventionnels mergés sur main
   ↓  release-please ouvre/met à jour la PR « chore(main): release 1.4.0 »
   ↓  merge de cette PR → tag v1.4.0 + GitHub Release + CHANGELOG.md
   ↓  job deploy (gardé par release_created) → prod
```

### Installation en une commande

```bash
bash ~/.claude/skills/git-github/assets/setup-release-please.sh --dry-run   # prévisualiser
bash ~/.claude/skills/git-github/assets/setup-release-please.sh             # appliquer
```

Le script est idempotent et pose : `release-please-config.json`,
`.release-please-manifest.json` (initialisé à la version réelle du `package.json`),
les trois workflows, le template de PR, le hook `commit-msg`, les réglages squash-merge
et l'autorisation « Actions peut créer des PR ». Il commite, mais **ne pousse pas**.

### Le piège à connaître

Le `GITHUB_TOKEN` par défaut **ne déclenche pas d'autres workflows**. Un workflow
séparé en `on: release` ne partira donc jamais après release-please. La parade retenue :
le job `deploy` vit dans le **même** workflow, gardé par
`if: needs.release-please.outputs.released == 'true'`.

### Opérations courantes

```bash
gh pr list --search "chore(main): release"          # la PR de release en cours
git log $(git describe --tags --abbrev=0)..HEAD --oneline   # ce que la prochaine contiendra
gh pr merge <n> --squash                            # publier (⚠️ confirmer d'abord)
gh release list && gh release view v1.4.0
git commit --allow-empty -m "chore: release 1.0.0" -m "Release-As: 1.0.0"   # forcer une version
```

Config avancée, monorepo, `extra-files`, dépannage complet → `references/release-please.md`

---

## 13. BRANCHES

```bash
git branch -a
git checkout -b feat/3-magic-link
git branch -d feat/3-magic-link            # -D si squashée (git ne la voit pas mergée)
git push origin --delete feat/3-magic-link
git fetch --prune
```
Nommage : `feat/<issue>-<slug>` · `fix/<issue>-<slug>` · `hotfix/<slug>` ·
`refactor/<slug>` · `docs/<slug>` · `chore/<slug>`

---

## 14. GITHUB PROJECTS (kanban)

```bash
gh project list --owner leandrodslv                     # tous les projects
gh project item-list 1 --owner leandrodslv               # items du board n°1
gh project item-add 1 --owner leandrodslv --url <url-issue-ou-pr>
gh project field-list 1 --owner leandrodslv               # colonnes/champs custom (Status, ...)
```

Nécessite le scope `project` sur le token : `gh auth refresh -s project`.

Utile pour voir l'avancement d'un milestone sans quitter le terminal ; la donnée de
fond reste les issues (§7) — le Project n'est qu'une vue dessus, ne pas dupliquer
l'information (pas de titre/description en double entre l'issue et l'item du board).

Champs custom, automatisations natives, requêtes avancées → `references/issues.md` § Projects (v2)

---

## 15. GITIGNORE & SÉCURITÉ

```bash
git check-ignore -v *          # vérifier ce qui est ignoré
git rm --cached <fichier>      # dé-tracker sans supprimer
```

Toujours ignorer : `node_modules/`, `.env`, `.env*.local`, `dist/`, `build/`,
`.DS_Store`, `*.log`, `__pycache__/`, `.venv/`, `*.pyc`, `.idea/`

⚠️ **Ne JAMAIS** committer clés API, tokens, secrets → `.env` + `.gitignore` + `gh secret set`.
✅ **Toujours** : `git status` avant de stager · commits atomiques · CI vert avant merge ·
`--force-with-lease` jamais `--force`.

---

## 16. FLOW DÉCISIONNEL

```
Léandro veut...
├── "commit/push"                       → §2, en passant par la porte §4
├── "forcer les conventional commits"   → §5
├── "hook avant de push (lint/tests)"   → §6
├── "crée/liste/ferme une issue"        → §7
├── "code l'issue N"                    → §8  ⭐
├── "crée/gère/merge ma PR"             → §9
├── "relis/review la PR de X"           → §9g
├── "protège main / reviewers requis"   → §9f
├── "le CI plante"                      → §10a
├── "crée/accélère un workflow"         → §10b / §10c
├── "dependabot / vulnérabilités"       → §11
├── "release-please / versions auto"    → §12 ⭐
├── "nouvelle branche"                  → §13
├── "mon board/kanban github"           → §14
└── "annuler/revenir"                   → references/actions.md
```

---

## 17. COMPORTEMENT ATTENDU

1. **Détecter le contexte** (répertoire, branche, remote, `gh auth`) avant d'agir
2. **Faire passer la porte §4** à tout message de commit et à tout titre de PR — sans exception
3. **Afficher** les commandes AVANT de les lancer
4. **Demander confirmation** pour l'irréversible ou le sortant : `reset --hard`, force push,
   `pr merge`, `issue close`, suppression de branche distante, modification des réglages du
   dépôt ou de la protection de branche, déclenchement d'un déploiement
5. **Lire l'issue en entier** (`--comments`) avant d'écrire une ligne de code
6. **Lire les vrais logs** (`--log-failed`) avant de diagnostiquer un CI rouge — jamais deviner
7. **Signaler** les fichiers sensibles détectés avant le commit
8. **Résumer** proprement après chaque action

### Format de sortie

```
📁 vibe-hub · branche feat/3-magic-link-login
🎫 Issue #3 — "Remplacer le mot de passe par une connexion par lien magique"
📝 4 fichiers modifiés, 2 ajoutés

Message de commit proposé :
  feat(auth): replace password login with magic link
  ✅ type · ✅ syntaxe · ✅ impératif · ✅ 50/72 car. · ✅ atomique

Commandes :
  git add .
  git commit -m "feat(auth): replace password login with magic link"
  git push -u origin feat/3-magic-link-login
  gh pr create --base main --fill

✅ PR #14 → https://github.com/leandrodslv/vibe-hub/pull/14
🔄 CI en cours (3 jobs) · gh pr checks 14 --watch
📦 Impact release : feat → bump minor (0.1.0 → 0.2.0)
```

---

## Références & assets

| Fichier | Contenu |
|---|---|
| `references/conventional-commits.md` | Spec, arbre de décision, exemples/contre-exemples, installation de la validation |
| `references/pull-requests.md` | Cycle de vie complet, reviews, conflits, stratégies de merge, protection de branche, PR empilées |
| `references/issues.md` | Recherche, batch, labels, milestones, templates, Projects |
| `references/github-actions.md` | Templates CI/deploy, debug, optimisation, matrices, secrets |
| `references/release-please.md` | Config, monorepo, chaîne release→deploy, dépannage |
| `references/actions.md` | Git avancé : rebase, cherry-pick, bisect, stash, submodules, config |
| `assets/setup-release-please.sh` | Installation complète en une commande (idempotent, `--dry-run`) |
| `assets/hooks/commit-msg` | Hook de validation des messages, zéro dépendance |
| `assets/hooks/pre-push` | Hook lint/typecheck/test avant push, zéro dépendance |
| `assets/commitlint.config.js` | Config commitlint (variante versionnée) |
| `assets/workflows/{ci,pr-title,release-please}.yml` | Workflows prêts à déposer |
| `assets/release-please-config.json` | Config release-please avec sections de CHANGELOG en français |
| `assets/pull_request_template.md` | Template de PR |
| `assets/CODEOWNERS` | Template CODEOWNERS pour reviewers obligatoires |
| `assets/dependabot.yml` | Config Dependabot (npm + github-actions, groupée) |
