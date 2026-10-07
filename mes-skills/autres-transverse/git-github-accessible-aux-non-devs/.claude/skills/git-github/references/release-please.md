# Référence — Releases automatisées avec release-please

## Le principe

`release-please` est un bot qui lit les **commits conventionnels** arrivés sur `main`
et maintient en permanence une **PR de release** ouverte. Cette PR contient le bump
de version, le CHANGELOG généré, et rien d'autre. Merger cette PR crée le tag et la
GitHub Release — ce qui peut à son tour déclencher le déploiement.

```
feat(auth): add magic link      ──┐
fix(ui): correct card spacing   ──┤ merges sur main
feat(docs): companion documents ──┘
                 ↓
   release-please ouvre / met à jour la PR
   « chore(main): release 1.4.0 »
     • package.json  1.3.2 → 1.4.0
     • CHANGELOG.md  Features / Bug Fixes
                 ↓
        merge de la PR de release
                 ↓
   tag v1.4.0 + GitHub Release + CHANGELOG committé
                 ↓
      workflow deploy (on: release published) → prod
```

**Le bénéfice** : on ne décide plus d'un numéro de version ni n'écrit un CHANGELOG
à la main. Le message de commit *est* la source de vérité. En contrepartie, un commit
mal typé produit une version fausse — d'où la validation du titre de PR (§5).

---

## 1. CALCUL DE VERSION

| Commits depuis la dernière release | Bump |
|---|---|
| `fix:`, `perf:`, `revert:` | **patch** — 1.3.2 → 1.3.3 |
| au moins un `feat:` | **minor** — 1.3.2 → 1.4.0 |
| au moins un `!` ou `BREAKING CHANGE:` | **major** — 1.3.2 → 2.0.0 |
| uniquement `docs:`, `chore:`, `style:`, `test:`, `refactor:`, `ci:` | aucune release |

⚠️ **Avant 1.0.0** : par défaut un breaking change bumpe la *minor* (0.3.0 → 0.4.0),
pas la major. Pour passer en 1.0.0, ajouter `"release-as": "1.0.0"` dans la config,
ou mettre `Release-As: 1.0.0` dans le corps d'un commit vide :

```bash
git commit --allow-empty -m "chore: release 1.0.0" -m "Release-As: 1.0.0"
```

---

## 2. WORKFLOW

`.github/workflows/release-please.yml` :

```yaml
name: Release Please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          # config-file / manifest-file par défaut :
          # release-please-config.json et .release-please-manifest.json
```

### Sorties disponibles pour enchaîner

```yaml
      # Ne s'exécute QUE quand la PR de release vient d'être mergée
      - name: Publier sur npm
        if: ${{ steps.release.outputs.release_created }}
        run: npm ci && npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Outputs utiles : `release_created` (bool), `tag_name` (`v1.4.0`), `version` (`1.4.0`),
`major` / `minor` / `patch`, `pr` (JSON de la PR de release), `upload_url`.

### ⚠️ Le piège du `GITHUB_TOKEN`

Les événements produits par le `GITHUB_TOKEN` par défaut **ne déclenchent pas** d'autres
workflows. Donc : si le workflow de déploiement écoute `on: release`, il ne partira pas
si la release a été créée avec le `GITHUB_TOKEN` standard.

Trois solutions, par ordre de préférence :

1. **Tout faire dans le même workflow**, gardé par `if: steps.release.outputs.release_created`
   (le plus simple, recommandé).
2. **Un Personal Access Token** (fine-grained, permissions `contents: write` +
   `pull-requests: write`) stocké en secret et passé à l'action :
   `token: ${{ secrets.RELEASE_PLEASE_TOKEN }}`.
3. **Une GitHub App** avec `actions/create-github-app-token` (le plus propre en équipe).

---

## 3. CONFIGURATION

`release-please-config.json` (à la racine) :

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "node",
  "packages": {
    ".": {
      "changelog-path": "CHANGELOG.md",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": false,
      "draft": false,
      "prerelease": false
    }
  },
  "changelog-sections": [
    { "type": "feat",     "section": "✨ Fonctionnalités" },
    { "type": "fix",      "section": "🐛 Corrections" },
    { "type": "perf",     "section": "⚡ Performance" },
    { "type": "revert",   "section": "⏪ Reverts" },
    { "type": "docs",     "section": "📚 Documentation", "hidden": false },
    { "type": "refactor", "section": "♻️ Refactoring",   "hidden": true },
    { "type": "chore",    "section": "🔧 Maintenance",   "hidden": true },
    { "type": "test",     "section": "✅ Tests",          "hidden": true },
    { "type": "ci",       "section": "🤖 CI",            "hidden": true }
  ]
}
```

`.release-please-manifest.json` — la version courante, tenue à jour par le bot :

```json
{ ".": "0.1.0" }
```

> Les deux fichiers doivent être commités **avant** le premier run, sinon release-please
> part de zéro et propose une 1.0.0 ou 0.1.0 inattendue.

### `release-type` selon le projet

| Valeur | Fichiers de version mis à jour |
|---|---|
| `node` | `package.json`, `package-lock.json` |
| `python` | `pyproject.toml`, `setup.py`, `__init__.py` |
| `rust` | `Cargo.toml`, `Cargo.lock` |
| `go` | tag uniquement |
| `simple` | `version.txt` |
| `terraform-module`, `helm`, `php`, `dart`, `java`… | voir la doc amont |

### Bumper des fichiers supplémentaires

```json
"extra-files": [
  "src/version.ts",
  { "type": "json", "path": "manifest.json", "jsonpath": "$.version" }
]
```

Dans un fichier texte, marquer la ligne à mettre à jour :
```ts
export const VERSION = "0.1.0"; // x-release-please-version
```

### Monorepo

```json
{
  "packages": {
    "packages/web":  { "release-type": "node", "component": "web" },
    "packages/api":  { "release-type": "node", "component": "api" }
  },
  "separate-pull-requests": false,
  "plugins": ["node-workspace"]
}
```

---

## 4. MISE EN PLACE — CHECKLIST

```bash
# 1. Config + manifest (adapter la version courante réelle)
cat > release-please-config.json <<'EOF'
{ "release-type": "node", "packages": { ".": { "changelog-path": "CHANGELOG.md" } } }
EOF
echo '{ ".": "0.1.0" }' > .release-please-manifest.json

# 2. Workflow
mkdir -p .github/workflows
# ... écrire .github/workflows/release-please.yml (§2)

# 3. Autoriser les Actions à créer des PR
#    Settings → Actions → General → Workflow permissions
#    ☑ Read and write permissions
#    ☑ Allow GitHub Actions to create and approve pull requests
gh api -X PUT repos/{owner}/{repo}/actions/permissions/workflow \
  -f default_workflow_permissions=write -F can_approve_pull_request_reviews=true

# 4. Merge strategy : squash uniquement, titre de PR = message de commit
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY

# 5. Commit + push
git add release-please-config.json .release-please-manifest.json .github/workflows/
git commit -m "ci(release): set up release-please automation"
git push origin main

# 6. Vérifier
gh run list --workflow=release-please.yml --limit 3
gh pr list --search "chore(main): release"
```

---

## 5. GARDE-FOUS SUR LES COMMITS

Release-please ne vaut que ce que valent les messages de commit. Deux protections :

### a. Valider le titre des PR (indispensable en mode squash)

`.github/workflows/pr-title.yml` :

```yaml
name: PR Title
on:
  pull_request:
    types: [opened, edited, synchronize]
permissions: { pull-requests: read }
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env: { GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
        with:
          types: |
            feat
            fix
            perf
            docs
            style
            refactor
            test
            chore
            ci
            build
            revert
```

Puis en faire un *required status check* dans la protection de branche.

### b. Valider les commits en local (commitlint + husky)

```bash
npm i -D @commitlint/cli @commitlint/config-conventional husky
npx husky init
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
echo "export default { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js
```

Alternative sans dépendance — hook git natif `.git/hooks/commit-msg` :
```sh
#!/bin/sh
grep -qE "^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?!?: .{1,72}" "$1" || {
  echo "❌ Message non conventionnel. Format : type(scope): description"
  exit 1
}
```
(`chmod +x .git/hooks/commit-msg` — attention : non versionné, donc local à ta machine.)

---

## 6. LA CHAÎNE COMPLÈTE : release → deploy

Option recommandée — tout dans `release-please.yml`, pas de problème de token :

```yaml
name: Release & Deploy

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    outputs:
      released: ${{ steps.release.outputs.release_created }}
      tag: ${{ steps.release.outputs.tag_name }}
    steps:
      - uses: googleapis/release-please-action@v4
        id: release

  deploy:
    needs: [release-please]
    if: needs.release-please.outputs.released == 'true'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
        with: { ref: ${{ needs.release-please.outputs.tag }} }
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci && npm run build
      - run: npx vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }} --yes
      - run: echo "🚀 ${{ needs.release-please.outputs.tag }} en production" >> $GITHUB_STEP_SUMMARY
```

---

## 7. OPÉRATIONS COURANTES

```bash
# Où en est la PR de release ?
gh pr list --search "chore(main): release" --json number,title,url

# Merger la release (déclenche tag + release + deploy)
gh pr merge <n> --squash

# Voir ce que la prochaine release contiendra
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Releases existantes
gh release list
gh release view v1.4.0
gh release view v1.4.0 --json body -q .body     # notes générées

# Forcer une version précise (commit vide sur main)
git commit --allow-empty -m "chore: release 2.0.0" -m "Release-As: 2.0.0"

# Empêcher release-please de prendre un commit en compte
git commit -m "fix: correctif interne" -m "Release-As: skip"   # ou typer en chore:
```

---

## 8. DÉPANNAGE

| Symptôme | Cause / correctif |
|---|---|
| Aucune PR de release créée | Aucun commit `feat`/`fix` depuis la dernière release — normal. Vérifier avec `git log <dernier-tag>..HEAD --oneline`. |
| `GitHub Actions is not permitted to create pull requests` | Settings → Actions → General → cocher *Allow GitHub Actions to create and approve pull requests*. |
| Version de départ inattendue | `.release-please-manifest.json` absent ou faux. Le renseigner avec la version réelle et committer. |
| CHANGELOG vide | Les commits ne sont pas conventionnels, ou les types utilisés sont `hidden: true` dans `changelog-sections`. |
| Le deploy ne part pas après la release | Le `GITHUB_TOKEN` ne déclenche pas d'autres workflows → utiliser le job unique (§6) ou un PAT. |
| Le merge a produit `Merge pull request #14 from…` | La stratégie de merge n'est pas *squash*, ou le titre du squash n'est pas `PR_TITLE`. Corriger dans Settings → General → Pull Requests. |
| Un breaking change n'a pas bumpé la major | Projet en 0.x : c'est le comportement par défaut. Utiliser `Release-As: 1.0.0`. |
| PR de release en conflit | Fermer la PR ; release-please la recrée proprement au prochain push sur `main`. |

---

## 9. ALTERNATIVES

| Outil | Quand le préférer |
|---|---|
| **release-please** | Release par PR, revue avant publication, monorepo. Le défaut recommandé. |
| **semantic-release** | Publication immédiate au push sur `main`, sans PR intermédiaire. Plus brutal, plus rapide. |
| **changesets** | Monorepo JS où chaque contributeur déclare l'impact à la main (`.changeset/*.md`). |
| **`gh release create --generate-notes`** | Petit projet, releases occasionnelles, aucune automatisation à maintenir. |
