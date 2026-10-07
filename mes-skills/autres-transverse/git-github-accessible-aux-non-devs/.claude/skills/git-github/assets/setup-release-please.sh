#!/usr/bin/env bash
# Installe la chaîne complète : conventional commits → PR → release automatisée.
#
# Usage (depuis la racine du repo) :
#   bash ~/.claude/skills/git-github/assets/setup-release-please.sh [--dry-run]
#
# Idempotent : ne réécrit pas un fichier existant, ne recommite pas si rien n'a changé.

set -euo pipefail

ASSETS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

run() {
  if $DRY_RUN; then echo "   [dry-run] $*"; else eval "$@"; fi
}

step() { echo ""; echo "── $* ────────────────────────────────"; }

# ── 0. Pré-vol ────────────────────────────────────────────────────────────────
step "Pré-vol"
git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "❌ Pas un repo git."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "❌ gh non authentifié → gh auth login"; exit 1; }

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
BRANCH=$(git branch --show-current)
VERSION=$(node -p "require('./package.json').version" 2>/dev/null || echo "0.1.0")
echo "   Repo    : $REPO"
echo "   Branche : $BRANCH"
echo "   Version : $VERSION"

# Le script ne stage que SES fichiers : on ne contrôle que ces chemins-là.
# Un travail en cours ailleurs dans le repo n'est donc pas bloquant.
OWNED="release-please-config.json .release-please-manifest.json .github"
DIRTY=$(git status --porcelain -- $OWNED)
if [ -n "$DIRTY" ]; then
  echo "⚠️  Changements non commités sur les chemins gérés par ce script :"
  echo "$DIRTY" | sed 's/^/      /'
  echo "   Committer ou stasher ces fichiers avant de continuer."
  $DRY_RUN || exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "   ℹ️  Travail en cours ailleurs dans le repo — non concerné, sera laissé intact."
fi

# ── 1. Config release-please ──────────────────────────────────────────────────
step "Config release-please"
if [ -f release-please-config.json ]; then
  echo "   release-please-config.json existe déjà — conservé."
else
  run "cp '$ASSETS/release-please-config.json' ."
  echo "   ✅ release-please-config.json"
fi

if [ -f .release-please-manifest.json ]; then
  echo "   .release-please-manifest.json existe déjà — conservé."
else
  run "echo '{ \".\": \"$VERSION\" }' > .release-please-manifest.json"
  echo "   ✅ .release-please-manifest.json (départ à $VERSION)"
fi

# ── 2. Workflows ──────────────────────────────────────────────────────────────
step "Workflows"
run "mkdir -p .github/workflows"
for wf in release-please.yml pr-title.yml ci.yml; do
  if [ -f ".github/workflows/$wf" ]; then
    echo "   .github/workflows/$wf existe déjà — conservé."
  else
    run "cp '$ASSETS/workflows/$wf' .github/workflows/"
    echo "   ✅ .github/workflows/$wf"
  fi
done

# ── 3. Template de PR ─────────────────────────────────────────────────────────
step "Template de PR"
if [ -f .github/pull_request_template.md ]; then
  echo "   Template existe déjà — conservé."
else
  run "cp '$ASSETS/pull_request_template.md' .github/"
  echo "   ✅ .github/pull_request_template.md"
fi

# ── 4. Hook local de validation des commits ───────────────────────────────────
step "Hook commit-msg (local, non versionné)"
if [ -f .git/hooks/commit-msg ]; then
  echo "   Hook existe déjà — conservé."
else
  run "cp '$ASSETS/hooks/commit-msg' .git/hooks/commit-msg"
  run "chmod +x .git/hooks/commit-msg"
  echo "   ✅ .git/hooks/commit-msg"
fi

# ── 5. Réglages du dépôt ──────────────────────────────────────────────────────
step "Réglages du dépôt (squash-merge + titre de PR)"
run "gh api -X PATCH 'repos/$REPO' \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_auto_merge=true \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY >/dev/null"
echo "   ✅ squash-merge exclusif, titre du squash = titre de la PR"

step "Autoriser les Actions à créer des PR"
run "gh api -X PUT 'repos/$REPO/actions/permissions/workflow' \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true >/dev/null"
echo "   ✅ Workflow permissions: write + création de PR"

# ── 6. Commit ─────────────────────────────────────────────────────────────────
step "Commit"
run "git add release-please-config.json .release-please-manifest.json .github/"
if $DRY_RUN || [ -n "$(git diff --cached --name-only)" ]; then
  run "git commit -m 'ci(release): set up conventional commits, CI and release-please'"
  echo "   ✅ Commité"
else
  echo "   Rien à committer."
fi

# ── 7. Suite ──────────────────────────────────────────────────────────────────
step "Prochaines étapes"
cat <<'EOF'
   1. git push origin main
   2. gh run list --workflow=release-please.yml --limit 3
   3. Vérifier les noms exacts des checks après le premier run :
        gh pr checks <n> --json name -q '.[].name'
   4. Activer la protection de branche avec ces noms :
        gh api -X PUT repos/OWNER/REPO/branches/main/protection --input - <<'JSON'
        {
          "required_status_checks": { "strict": true, "contexts": ["CI", "PR Title"] },
          "enforce_admins": false,
          "required_pull_request_reviews": null,
          "restrictions": null,
          "required_linear_history": true
        }
JSON
   5. Décommenter le job deploy dans .github/workflows/release-please.yml
      et poser le secret correspondant : gh secret set VERCEL_TOKEN
EOF
echo ""
