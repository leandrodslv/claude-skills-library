# Référence — Pull Requests

Une PR est l'unité de livraison. Avec squash-merge + release-please, **le titre de la PR
devient le message de commit sur `main`, donc la ligne du CHANGELOG**. Un titre bâclé
est une release illisible.

---

## 1. CYCLE DE VIE COMPLET

```
issue → branche → commits → PR (draft) → CI vert → review → merge squash → cleanup
                                ↑                                    ↓
                                └────── corrections ──────────  issue fermée auto
```

### Étape par étape

```bash
# 0. Pré-vol
git status --porcelain                    # working tree propre ?
git fetch origin && git log origin/main..HEAD --oneline   # ce que la PR va contenir
gh pr status                              # une PR existe-t-elle déjà pour cette branche ?

# 1. Pousser la branche
git push -u origin feat/3-magic-link

# 2. Ouvrir la PR
gh pr create --base main --fill           # titre/corps depuis les commits
# ou en explicite (préférable quand il y a plusieurs commits)
gh pr create --base main \
  --title "feat(auth): replace password login with magic link" \
  --body-file .github/pr-body.md \
  --assignee @me --label enhancement

# 3. Attendre le CI
gh pr checks --watch

# 4. Merger
gh pr merge --squash --delete-branch

# 5. Nettoyer en local
git checkout main && git pull --rebase origin main && git fetch --prune
```

---

## 2. CRÉER

```bash
gh pr create --base main --fill                    # depuis les commits
gh pr create --base main --fill-first              # depuis le 1er commit seulement
gh pr create --draft                               # brouillon : pas de review demandée
gh pr create --web                                 # finir dans le navigateur
gh pr create --base main --head feat/x --repo owner/name
gh pr create --title "..." --body "$(cat <<'EOF'
...markdown multi-ligne...
EOF
)"
```

### Le titre : la règle non négociable

Le titre **doit** être un en-tête conventionnel valide (`type(scope): description`),
parce qu'il devient le message du commit squashé. Voir `conventional-commits.md`.

```
✅ feat(auth): replace password login with magic link
✅ fix(reader): correct cover loading on iPad landscape
❌ Magic link
❌ Fixes #3
❌ WIP: auth stuff
```

### Le corps : modèle

```markdown
## Résumé
Une à trois phrases : ce que ça change et pourquoi.

## Changements
- Point saillant 1
- Point saillant 2

## Tests
- [x] Unitaires ajoutés sur X
- [x] Parcours vérifié en local

## Notes de review
Ce qui mérite l'attention du relecteur : décision discutable, dette assumée, zone risquée.

Closes #3
```

⚠️ `Closes #3` doit être dans le **corps**, pas dans le titre — GitHub ne lit que le corps.

### Template versionné

`.github/pull_request_template.md` — préremplit toute nouvelle PR :

```markdown
## Résumé


## Changements
- 

## Tests
- [ ] 

## Checklist
- [ ] Titre au format conventional commit
- [ ] CI vert
- [ ] Pas de secret ni de fichier généré commité

Closes #
```

---

## 3. INSPECTER & SUIVRE

```bash
gh pr list                                  # ouvertes
gh pr list --state all --limit 50
gh pr list --author @me
gh pr list --search "review-requested:@me"  # ce qu'on attend de toi
gh pr list --search "is:open draft:false status:success"   # prêtes à merger
gh pr list --json number,title,statusCheckRollup,reviewDecision

gh pr status                                # vue synthétique : tes PR + celles à relire
gh pr view                                  # la PR de la branche courante
gh pr view 14 --comments                    # ⭐ avec toute la discussion
gh pr view 14 --json reviewDecision,mergeable,mergeStateStatus
gh pr diff 14
gh pr diff 14 --name-only
gh pr checks 14                             # état des checks
gh pr checks 14 --watch --fail-fast         # bloquer jusqu'au vert
```

### Lire l'état réel d'une PR avant de décider

```bash
gh pr view 14 --json mergeable,mergeStateStatus,reviewDecision,statusCheckRollup \
  -q '{mergeable, state: .mergeStateStatus, review: .reviewDecision,
       checks: [.statusCheckRollup[] | select(.conclusion != "SUCCESS") | .name]}'
```

| `mergeStateStatus` | Signification |
|---|---|
| `CLEAN` | Mergeable, checks OK |
| `BLOCKED` | Review requise ou check obligatoire manquant |
| `BEHIND` | La branche est en retard sur `main` → rebase/update |
| `DIRTY` | Conflits de merge |
| `UNSTABLE` | Mergeable mais un check non bloquant est rouge |
| `DRAFT` | Encore en brouillon |

---

## 4. MODIFIER

```bash
gh pr edit 14 --title "feat(auth): ..."
gh pr edit 14 --body-file ./body.md
gh pr edit 14 --add-label enhancement --remove-label wip
gh pr edit 14 --add-assignee @me
gh pr edit 14 --add-reviewer alice,bob
gh pr edit 14 --milestone "v1.2"
gh pr edit 14 --base develop            # changer la branche cible
gh pr ready 14                          # draft → prêt
gh pr ready 14 --undo                   # repasser en draft
gh pr close 14 --delete-branch
gh pr reopen 14
```

Mettre à jour le contenu d'une PR = pousser sur la branche. Rien d'autre à faire.
```bash
git commit -m "fix(auth): handle expired token edge case"
git push
```

---

## 5. REVIEWS

### Relire la PR d'un autre

```bash
gh pr checkout 14                       # récupérer la branche en local pour tester
gh pr diff 14
gh pr review 14 --approve
gh pr review 14 --request-changes --body "Le token n'est pas invalidé après usage."
gh pr review 14 --comment --body "Question sur le choix du TTL."
```

### Traiter les retours reçus

```bash
gh pr view 14 --comments                                    # tout lire
gh api repos/{owner}/{repo}/pulls/14/comments \
  -q '.[] | "\(.path):\(.line) — \(.user.login): \(.body)"'  # commentaires inline

# corriger, puis
git commit -m "fix(auth): invalidate token after first use"
git push
gh pr comment 14 --body "Corrigé en $(git rev-parse --short HEAD) : le token est marqué consommé à la première validation."
```

Répondre à chaque retour, même bref. Un commentaire sans réponse bloque la review.

---

## 6. MAINTENIR À JOUR / CONFLITS

```bash
# La PR est BEHIND
gh pr update-branch 14                 # merge de main dans la branche (côté GitHub)

# ou en local, historique plus propre (branche perso uniquement)
git checkout feat/3-magic-link
git fetch origin
git rebase origin/main
git push --force-with-lease
```

### Résoudre les conflits

```bash
git fetch origin && git rebase origin/main
git diff --name-only --diff-filter=U    # fichiers en conflit
# ... résoudre ...
git add <fichiers>
git rebase --continue
git push --force-with-lease
# En cas de doute : git rebase --abort
```

⚠️ `--force-with-lease` jamais `--force` : il refuse de pousser si quelqu'un a poussé
entre-temps. Et jamais de force push sur une branche que quelqu'un d'autre a checkoutée.

---

## 7. MERGER

```bash
gh pr merge 14 --squash --delete-branch          # ⭐ le défaut avec release-please
gh pr merge 14 --merge                           # commit de merge (historique préservé)
gh pr merge 14 --rebase                          # rejoue les commits sur main
gh pr merge 14 --squash --auto                   # merge dès que les checks passent
gh pr merge 14 --squash --subject "feat(auth): replace password login with magic link"
gh pr merge 14 --admin                           # ⚠️ outrepasse les protections
```

### Choisir la stratégie

| Stratégie | Quand | Effet sur release-please |
|---|---|---|
| **squash** ⭐ | Défaut. Une PR = un commit sur `main` | Le **titre de la PR** est lu |
| rebase | Chaque commit de la branche a une valeur propre | **Chaque commit** est lu |
| merge | Rarement — branches de release, merges de long cours | Chaque commit est lu, plus un commit de merge parasite |

Configurer le repo pour ne laisser que le squash, et que le titre du squash soit le titre de la PR :

```bash
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY
```

`squash_merge_commit_title=PR_TITLE` est **le réglage clé** : sans lui, GitHub génère
`Titre de la PR (#14)` ou pire, concatène les messages de commit — et le CHANGELOG déraille.

### Auto-merge

```bash
gh pr merge 14 --squash --auto --delete-branch
```
La PR sera mergée automatiquement dès que tous les checks obligatoires passent.
Nécessite l'auto-merge activé sur le repo :
```bash
gh api -X PATCH repos/{owner}/{repo} -F allow_auto_merge=true
```

### Avant tout merge — checklist

1. `gh pr checks <n>` → tout vert
2. Titre conventionnel valide
3. `Closes #N` présent si la PR répond à une issue
4. Aucun secret ni fichier généré dans `gh pr diff <n> --name-only`
5. La stratégie est bien `--squash`

---

## 8. APRÈS LE MERGE

```bash
git checkout main
git pull --rebase origin main
git branch -d feat/3-magic-link          # -D si la branche a été squashée (git ne la voit pas mergée)
git fetch --prune
```

Ce qui se passe tout seul :
- L'issue `Closes #3` se ferme
- La branche distante est supprimée (`delete_branch_on_merge`)
- release-please ouvre ou met à jour la PR de release (voir `release-please.md`)

---

## 9. PROTECTION DE BRANCHE

Le filet qui rend tout le reste fiable.

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI", "PR Title"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": true
}
EOF

# Vérifier
gh api repos/{owner}/{repo}/branches/main/protection -q '.required_status_checks.contexts'
```

- `required_pull_request_reviews: null` → pas de review obligatoire (projet solo).
  En équipe : `{"required_approving_review_count": 1, "dismiss_stale_reviews": true}`.
- `strict: true` → la branche doit être à jour avec `main` avant merge.
- ⚠️ `contexts` doit contenir les **noms des jobs** exactement tels qu'ils apparaissent
  dans les checks. Les récupérer avec `gh pr checks <n> --json name -q '.[].name'`.
- ⚠️ Un check listé mais jamais déclenché (à cause d'un filtre `paths`) bloque la PR
  indéfiniment. D'où le pattern du job `ci-ok` toujours déclenché (`github-actions.md` §3).

---

## 10. PR EMPILÉES (STACKED)

Quand une feature dépend d'une autre encore en review :

```bash
git checkout -b feat/4-magic-link-ui feat/3-magic-link     # partir de la branche parente
# ... travailler ...
git push -u origin feat/4-magic-link-ui
gh pr create --base feat/3-magic-link --title "feat(ui): magic link form"
```

Après le merge de la PR parente, rebaser l'enfant sur `main` et rebaser la cible :
```bash
git checkout feat/4-magic-link-ui
git fetch origin && git rebase --onto origin/main feat/3-magic-link
git push --force-with-lease
gh pr edit <n> --base main
```

À utiliser avec parcimonie : deux niveaux maximum, sinon le coût de rebase dépasse le bénéfice.

---

## 11. RACCOURCIS POUR L'AGENT

```bash
# PR de la branche courante, ou rien
gh pr view --json number -q .number 2>/dev/null || echo "aucune PR"

# Toutes mes PR prêtes à merger
gh pr list --author @me --json number,title,mergeStateStatus \
  -q '.[] | select(.mergeStateStatus=="CLEAN") | "#\(.number) \(.title)"'

# Les checks rouges de la PR courante
gh pr checks --json name,state -q '.[] | select(.state!="SUCCESS") | .name'

# L'issue fermée par la PR courante
gh pr view --json closingIssuesReferences -q '.closingIssuesReferences[].number'

# Vérifier que le titre est conventionnel avant de merger
gh pr view --json title -q .title | grep -qE '^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\([a-z0-9._/-]+\))?!?: .' \
  && echo "titre OK" || echo "❌ titre non conventionnel"
```
