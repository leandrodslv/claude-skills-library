# Référence — GitHub Actions (CI/CD)

Les workflows vivent dans `.github/workflows/*.yml`. Un fichier = un workflow.
Le scope `workflow` est requis sur le token `gh` pour pousser des modifications
dans ce dossier (`gh auth refresh -s workflow`).

---

## 1. PILOTER DEPUIS LE CLI

```bash
# Workflows
gh workflow list                          # tous les workflows (actifs et désactivés)
gh workflow view ci.yml
gh workflow view ci.yml --yaml            # afficher le YAML tel que GitHub le voit
gh workflow run deploy.yml --ref main     # déclencher un workflow_dispatch
gh workflow run deploy.yml -f environment=production -f dry_run=false
gh workflow enable ci.yml / gh workflow disable ci.yml

# Runs
gh run list --limit 10
gh run list --workflow=ci.yml --branch=main --status=failure
gh run list --json databaseId,displayTitle,conclusion,createdAt,durationMs
gh run view <run-id>                      # résumé : jobs, durées, conclusions
gh run view <run-id> --log-failed         # ⭐ logs des seules étapes en échec
gh run view <run-id> --job=<job-id> --log # logs complets d'un job
gh run watch <run-id>                     # suivi live jusqu'à la fin
gh run rerun <run-id>                     # tout relancer
gh run rerun <run-id> --failed            # relancer seulement les jobs rouges
gh run rerun <run-id> --debug             # relancer avec les logs de debug activés
gh run cancel <run-id>
gh run download <run-id>                  # récupérer les artefacts

# Sur une PR
gh pr checks <n>
gh pr checks <n> --watch                  # attendre le vert avant de merger
```

### Le run le plus récent, sans copier d'ID à la main
```bash
RUN=$(gh run list --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN" --log-failed
```

---

## 2. MÉTHODE DE DEBUG D'UN CI ROUGE

Dans cet ordre. Ne jamais sauter l'étape 2 : diagnostiquer sans lire les logs
fait perdre plus de temps que de les lire.

1. **Localiser** — `gh run list --limit 5` → quel workflow, quel job, quelle branche
2. **Lire l'erreur réelle** — `gh run view <id> --log-failed`
3. **Classer la panne** :
   | Symptôme dans les logs | Cause probable |
   |---|---|
   | `command not found`, version inattendue | setup-* manquant ou mauvaise version |
   | `ENOENT`, chemin introuvable | `working-directory` ou artefact non téléchargé |
   | secret vide, `401`/`403` | secret absent, mal nommé, ou `permissions:` trop restrictives |
   | passe en local, casse en CI | dépendance d'environnement : casse des noms de fichiers (Linux ≠ Windows), fuseau horaire, locale, `.env` non commité |
   | échec intermittent | test flaky, course réseau, cache corrompu |
   | `Process completed with exit code 137` | OOM — le runner a tué le process |
4. **Reproduire en local** la commande exacte de l'étape, pas une approximation
5. **Corriger** → commit `fix(ci): ...` (ou `fix(scope): ...` si le bug est applicatif)
6. **Confirmer** — `gh pr checks --watch`

### Vider un cache suspect
```bash
gh cache list
gh cache delete <cache-id>
gh cache delete --all
```

### Activer les logs verbeux
```bash
gh run rerun <run-id> --debug
# ou en permanence via des secrets repo :
gh secret set ACTIONS_STEP_DEBUG --body true
gh secret set ACTIONS_RUNNER_DEBUG --body true
```

---

## 3. TEMPLATE — CI PARALLÉLISÉ (Node / Vite / React)

Le pattern à privilégier : jobs indépendants qui tournent **en parallèle**, gardés
par un job rapide, avec cache et annulation des runs obsolètes.

`.github/workflows/ci.yml` :

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  # Garde rapide (~30 s) : si ça casse ici, on ne paie pas les jobs lents.
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  typecheck:
    name: Typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run typecheck

  test:
    name: Tests
    runs-on: ubuntu-latest
    needs: [lint]              # ne démarre que si le lint passe
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
          retention-days: 7

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, typecheck]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - name: Cache build intermédiaire
        uses: actions/cache@v4
        with:
          path: node_modules/.vite
          key: vite-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1     # consommé par le job deploy, pas besoin de le garder

  # Point de contrôle unique à mettre en "required status check" côté branch protection
  ci-ok:
    name: CI
    runs-on: ubuntu-latest
    needs: [lint, typecheck, test, build]
    if: always()
    steps:
      - name: Vérifier qu'aucun job n'a échoué
        run: |
          [ "${{ contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled') }}" = "false" ]
```

**Pourquoi `ci-ok`** : un seul check requis dans la protection de branche, stable
même quand on ajoute ou renomme des jobs en amont.

---

## 4. TEMPLATE — DÉPLOIEMENT

### 4a. Déclenché par une release (le pattern release-please)

`.github/workflows/deploy.yml` :

```yaml
name: Deploy

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      environment:
        description: Cible de déploiement
        type: choice
        options: [staging, production]
        default: staging

concurrency:
  group: deploy-${{ github.event.inputs.environment || 'production' }}
  cancel-in-progress: false     # ⚠️ jamais annuler un déploiement en cours

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'production' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run build
        env:
          VITE_API_URL: ${{ vars.VITE_API_URL }}
      - name: Deploy
        run: npx vercel deploy --prod --token=$VERCEL_TOKEN --yes
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
      - name: Résumé
        run: echo "✅ Déployé — ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
```

Utiliser un **environment** GitHub (`Settings → Environments`) pour :
protéger la prod par une approbation manuelle, scoper les secrets, tracer les déploiements.

### 4b. Réutiliser l'artefact du CI au lieu de rebuilder

```yaml
  deploy:
    needs: [build]
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist }
      - run: npx vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }} --yes
```

### 4c. GitHub Pages

```yaml
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci && npm run build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
      - id: deployment
        uses: actions/deploy-pages@v4
```

---

## 5. OPTIMISER UN CI LENT

Un monolithe séquentiel de 12 min qui casse à la dernière étape est le pire des cas :
on paie le temps complet pour apprendre l'échec le plus tard possible.

### Diagnostiquer d'abord

```bash
# Durée des 10 derniers runs
gh run list --workflow=ci.yml --limit 10 \
  --json displayTitle,conclusion,startedAt,updatedAt \
  -q '.[] | "\(.conclusion)\t\(.displayTitle)"'

# Durée par job du dernier run → identifier le chemin critique
gh run view <run-id> --json jobs \
  -q '.jobs[] | "\(.name): \(((.completedAt|fromdate) - (.startedAt|fromdate)))s"'
```

### Leviers, par ordre de rendement

| Levier | Gain typique | Comment |
|---|---|---|
| **Paralléliser les jobs** | 40-60 % | Découper le monolithe en `lint`/`typecheck`/`test`/`build` sans `needs` entre eux. Le temps total = le job le plus long, plus la somme. |
| **Fail fast** | évite le gâchis | `needs: [lint]` sur les jobs lents : un lint raté coûte 30 s, pas 12 min. |
| **Cache des dépendances** | 1-3 min | `cache: 'npm'` sur `setup-node`, `cache: 'pip'`, `Swatinem/rust-cache`. |
| **Cache de build** | 1-4 min | `actions/cache` sur `.next/cache`, `node_modules/.vite`, `target/`. |
| **`concurrency` + cancel** | runners libérés | Annule les runs obsolètes quand on repush sur la même branche. |
| **Filtres `paths`** | 100 % sur les runs inutiles | Ne pas relancer le CI front quand seul le README change. |
| **Artefacts partagés** | durée d'un build | `upload-artifact` / `download-artifact` : `deploy` consomme le build, ne le refait pas. |
| **Sharding des tests** | proportionnel | Matrice `shard: [1,2,3,4]` + `--shard=${{ matrix.shard }}/4`. |
| **`npm ci --prefer-offline`** | 10-30 s | Exploite mieux le cache npm. |
| **Runners plus gros** | ~2× | `runs-on: ubuntu-latest-4-cores` (payant). Dernier recours, après le reste. |

### Filtres de chemins

```yaml
on:
  pull_request:
    paths:
      - 'src/**'
      - 'package.json'
      - 'package-lock.json'
      - '.github/workflows/ci.yml'
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

⚠️ Si le workflow est un *required check*, `paths` peut bloquer la PR en "en attente"
quand aucun fichier ne matche. Solution : un job `ci-ok` toujours déclenché qui devient
no-op, ou `paths-ignore` plutôt que `paths`.

### Sharding des tests

```yaml
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx vitest run --shard=${{ matrix.shard }}/4
```

**Mesurer avant / après** et le dire explicitement : « 12 min → 8 min 38 ».
Une optimisation non mesurée n'est pas une optimisation.

---

## 6. MATRICES

```yaml
    strategy:
      fail-fast: false            # ne pas tuer les autres combinaisons au 1er échec
      max-parallel: 4
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [18, 20, 22]
        exclude:
          - { os: windows-latest, node: 18 }
        include:
          - { os: ubuntu-latest, node: 22, coverage: true }
    runs-on: ${{ matrix.os }}
```

---

## 7. DÉCLENCHEURS (`on:`)

```yaml
on:
  push:
    branches: [main, 'release/**']
    tags: ['v*']
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  schedule:
    - cron: '0 6 * * 1'          # lundi 6h UTC
  workflow_dispatch:              # bouton manuel + gh workflow run
    inputs:
      dry_run: { type: boolean, default: true }
  release:
    types: [published]
  issues:
    types: [opened, labeled]
  workflow_call:                  # workflow réutilisable, appelé par un autre
```

### Conditions utiles

```yaml
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    if: github.actor != 'dependabot[bot]'
    if: "!contains(github.event.head_commit.message, '[skip ci]')"
    if: github.event.pull_request.draft == false
    if: always()          # même si un job précédent a échoué
    if: failure()         # seulement en cas d'échec (notifications)
```

---

## 8. PERMISSIONS & SECRETS

### Permissions du `GITHUB_TOKEN`

Toujours partir du minimum, puis élargir au besoin :

```yaml
permissions:
  contents: read          # défaut sain
# selon les besoins :
#   contents: write       # créer des tags/releases, pousser des commits
#   pull-requests: write  # créer/commenter des PR
#   issues: write         # créer/commenter des issues
#   packages: write       # publier des packages
#   id-token: write       # OIDC (auth cloud sans secret longue durée)
```

### Secrets et variables

```bash
gh secret list
gh secret set VERCEL_TOKEN                    # saisie interactive (rien dans l'historique shell)
gh secret set API_KEY < token.txt
gh secret set DEPLOY_KEY --env production     # scopé à un environment
gh secret delete OLD_TOKEN

gh variable list                              # non chiffrées, lisibles dans les logs
gh variable set VITE_API_URL --body "https://api.example.com"
```

Dans le YAML : `${{ secrets.NOM }}` (masqué dans les logs) · `${{ vars.NOM }}` (visible).

⚠️ Règles :
- Jamais de secret en dur dans un YAML, même « temporairement ».
- Les secrets ne sont **pas** exposés aux workflows déclenchés par une PR venant d'un fork.
- Un secret affiché dans un log est un secret compromis → rotation immédiate.

---

## 9. WORKFLOWS RÉUTILISABLES & ACTIONS COMPOSITES

### Workflow réutilisable

`.github/workflows/reusable-build.yml` :
```yaml
on:
  workflow_call:
    inputs:
      node-version: { type: string, default: '20' }
    secrets:
      NPM_TOKEN: { required: false }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: ${{ inputs.node-version }}, cache: 'npm' }
      - run: npm ci && npm run build
```

Appel :
```yaml
jobs:
  build:
    uses: ./.github/workflows/reusable-build.yml
    with: { node-version: '22' }
    secrets: inherit
```

### Action composite (factoriser des steps répétés)

`.github/actions/setup/action.yml` :
```yaml
name: Setup
runs:
  using: composite
  steps:
    - uses: actions/setup-node@v4
      with: { node-version: '20', cache: 'npm' }
    - run: npm ci
      shell: bash
```

Usage : `- uses: ./.github/actions/setup`

---

## 10. AUTOMATISATIONS UTILES

### Étiqueter automatiquement les PR selon les fichiers touchés
```yaml
name: Labeler
on: [pull_request_target]
permissions: { contents: read, pull-requests: write }
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5
```
`.github/labeler.yml` :
```yaml
"area:ui":  { changed-files: [{ any-glob-to-any-file: "src/components/**" }] }
"area:ci":  { changed-files: [{ any-glob-to-any-file: ".github/**" }] }
"area:docs":{ changed-files: [{ any-glob-to-any-file: "**/*.md" }] }
```

### Valider que le titre de PR est conventionnel (indispensable avec squash + release-please)
```yaml
name: PR Title
on:
  pull_request:
    types: [opened, edited, synchronize]
permissions: { pull-requests: read }
jobs:
  lint-title:
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
```

### Dependabot
`.github/dependabot.yml` :
```yaml
version: 2
updates:
  - package-ecosystem: npm
    directory: "/"
    schedule: { interval: weekly }
    commit-message: { prefix: "chore(deps)" }   # reste conventionnel
    open-pull-requests-limit: 5
  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: monthly }
    commit-message: { prefix: "ci(deps)" }
```

---

## 11. TESTER LES WORKFLOWS

- **`act`** (`brew install act` / `winget install nektos.act`) — exécute les workflows
  localement dans Docker : `act pull_request -j lint`. Approximation utile, pas identique.
- **`actionlint`** — linter statique de YAML de workflow, attrape les erreurs de syntaxe
  et d'expressions avant le push : `actionlint .github/workflows/*.yml`
- **Branche jetable** — pour les workflows non déclenchables en local (`release`, secrets) :
  pousser sur `ci/test-workflow`, itérer, supprimer la branche.
- **`workflow_dispatch` avec `dry_run`** — toujours prévoir cet input sur un workflow
  de déploiement, pour pouvoir le tester sans effet de bord.

---

## 12. RÉSUMÉS ET SORTIES

```yaml
      - name: Résumé lisible dans l'UI GitHub
        run: |
          echo "### Résultat du build" >> $GITHUB_STEP_SUMMARY
          echo "- Bundle : $(du -sh dist | cut -f1)" >> $GITHUB_STEP_SUMMARY
          echo "- Commit : \`${{ github.sha }}\`" >> $GITHUB_STEP_SUMMARY

      - id: meta
        run: echo "version=$(node -p "require('./package.json').version")" >> $GITHUB_OUTPUT
      - run: echo "Version ${{ steps.meta.outputs.version }}"
```

Sortie inter-jobs :
```yaml
  build:
    outputs:
      version: ${{ steps.meta.outputs.version }}
  deploy:
    needs: [build]
    steps:
      - run: echo "Déploiement de ${{ needs.build.outputs.version }}"
```

---

## 13. VARIABLES DE CONTEXTE COURANTES

| Expression | Contenu |
|---|---|
| `github.sha` | SHA du commit |
| `github.ref` | `refs/heads/main`, `refs/tags/v1.2.0` |
| `github.ref_name` | `main`, `v1.2.0` |
| `github.event_name` | `push`, `pull_request`, `release`… |
| `github.actor` | qui a déclenché |
| `github.repository` | `owner/name` |
| `github.run_number` | compteur incrémental du workflow |
| `github.event.pull_request.number` | numéro de PR |
| `runner.os` | `Linux`, `Windows`, `macOS` |
