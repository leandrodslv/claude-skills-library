# Référence complète des actions Git (commandes avancées)

> Ce fichier couvre **Git en local**. Pour la partie GitHub :
> - Issues → `issues.md`
> - GitHub Actions / CI-CD → `github-actions.md`
> - Releases automatisées → `release-please.md`

## RESET & REVERT

```bash
# Annuler le dernier commit (garde les changements stagés)
git reset --soft HEAD~1

# Annuler le dernier commit (garde les changements non-stagés)
git reset --mixed HEAD~1

# Annuler le dernier commit (DÉTRUIT les changements) ⚠️
git reset --hard HEAD~1

# Créer un commit d'annulation (safe, préserve l'historique)
git revert HEAD

# Revenir à un commit spécifique (identifier via git log)
git reset --hard <commit-hash>

# Force push après reset (⚠️ seulement sur branche perso)
git push origin <branche> --force-with-lease
```

---

## STASH

```bash
# Sauvegarder les changements temporairement
git stash push -m "WIP: description"

# Lister les stashs
git stash list

# Restaurer le dernier stash
git stash pop

# Restaurer un stash spécifique
git stash apply stash@{2}

# Supprimer un stash
git stash drop stash@{0}

# Voir le contenu d'un stash
git stash show -p stash@{0}
```

---

## REBASE

```bash
# Rebase interactif (modifier les N derniers commits)
git rebase -i HEAD~3

# Dans l'éditeur :
# pick   → garder le commit tel quel
# reword → modifier le message
# squash → fusionner avec le commit précédent
# fixup  → fusionner sans garder le message
# drop   → supprimer le commit

# Rebase sur main (synchroniser une feature branch)
git rebase origin/main

# Continuer après conflit résolu
git rebase --continue

# Aborter le rebase
git rebase --abort
```

---

## CHERRY-PICK

```bash
# Appliquer un commit spécifique sur la branche courante
git cherry-pick <commit-hash>

# Appliquer plusieurs commits
git cherry-pick <hash1> <hash2>

# Appliquer une plage de commits
git cherry-pick <hash-start>^..<hash-end>

# Sans committer automatiquement
git cherry-pick --no-commit <hash>
```

---

## TAGS & RELEASES

```bash
# Créer un tag annoté (pour les releases)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Créer un tag léger
git tag v1.0.0-beta

# Lister les tags
git tag -l

# Pousser un tag spécifique
git push origin v1.0.0

# Pousser tous les tags
git push origin --tags

# Supprimer un tag local
git tag -d v1.0.0

# Supprimer un tag remote
git push origin --delete v1.0.0

# Voir les détails d'un tag
git show v1.0.0
```

---

## BRANCHES AVANCÉES

```bash
# Voir toutes les branches (locales + remote)
git branch -a

# Tracer une branche remote
git branch --track feature/remote origin/feature/remote

# Mettre à jour les références remote
git fetch --prune

# Fusionner sans fast-forward (crée un merge commit)
git merge --no-ff feature/ma-branche

# Merger en squash (condense tous les commits en 1)
git merge --squash feature/ma-branche
git commit -m "feat: merge feature X"

# Comparer deux branches
git diff main..feature/ma-branche

# Voir les commits d'une branche pas encore dans main
git log main..feature/ma-branche --oneline
```

---

## REMOTE & SYNCHRONISATION

```bash
# Ajouter un remote
git remote add origin https://github.com/user/repo.git

# Changer l'URL d'un remote
git remote set-url origin https://github.com/user/nouveau-repo.git

# Voir les remotes configurés
git remote -v

# Fetcher sans merger
git fetch origin

# Pull avec rebase (propre, évite les merge commits)
git pull --rebase origin main

# Push sur un remote différent
git push upstream feature/ma-branche

# Forcer le push (après rebase) - utiliser avec précaution
git push --force-with-lease origin feature/ma-branche
```

---

## GITHUB CLI (gh) — bases

```bash
# Auth
gh auth login
gh auth status
gh auth refresh -s workflow,project     # élargir les scopes du token

# Repos
gh repo create mon-projet --public --source=. --push
gh repo clone user/repo
gh repo view --web
gh repo set-default owner/repo          # si plusieurs remotes

# Pull Requests
gh pr create --base main --fill
gh pr list / gh pr view <n> / gh pr checkout <n>
gh pr checks <n> --watch
gh pr merge <n> --squash --delete-branch
```

Le reste — issues, workflows, runs, secrets, releases — est détaillé dans
`issues.md`, `github-actions.md` et `release-please.md`.

---

## DIAGNOSTIC & DEBUGGAGE

```bash
# Historique avec graph
git log --oneline --graph --all --decorate

# Voir qui a modifié quelle ligne
git blame <fichier>

# Trouver le commit qui a introduit un bug
git bisect start
git bisect bad  # commit actuel est mauvais
git bisect good <hash-bon-commit>
# Tester, puis : git bisect good/bad
git bisect reset

# Voir le diff d'un commit précis
git show <commit-hash>

# Voir le diff d'un fichier entre deux commits
git diff <hash1> <hash2> -- <fichier>

# Nettoyer les fichiers non-trackés
git clean -fd  # fichiers + dossiers
git clean -fdn # dry-run (preview)

# Récupérer un fichier supprimé
git checkout <commit-hash> -- <fichier>

# Voir les fichiers modifiés dans un commit
git diff-tree --no-commit-id -r --name-only <hash>
```

---

## CONFIGURATION GIT

```bash
# Config globale
git config --global user.name "Léandro"
git config --global user.email "ton@email.com"
git config --global core.editor "code --wait"

# Alias utiles
git config --global alias.st "status --short"
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.undo "reset --soft HEAD~1"
git config --global alias.pushf "push --force-with-lease"

# Voir toute la config
git config --list

# Activer le rerere (réutiliser les résolutions de conflits)
git config --global rerere.enabled true

# Signer les commits avec GPG
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
```

---

## SUBMODULES

```bash
# Ajouter un submodule
git submodule add https://github.com/user/lib.git libs/lib-name

# Initialiser après clone
git submodule update --init --recursive

# Mettre à jour tous les submodules
git submodule update --remote --merge

# Supprimer un submodule
git submodule deinit libs/lib-name
git rm libs/lib-name
rm -rf .git/modules/libs/lib-name
```

---

## HOOKS GIT

Les hooks sont des scripts dans `.git/hooks/` exécutés automatiquement.

### pre-commit (lint avant commit)
```bash
#!/bin/sh
# .git/hooks/pre-commit
npm run lint || exit 1
```

### commit-msg (valider le format)
```bash
#!/bin/sh
# .git/hooks/commit-msg
if ! grep -qE "^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .{1,72}$" "$1"; then
  echo "❌ Message de commit invalide. Format attendu: type(scope): description"
  exit 1
fi
```

Rendre exécutable : `chmod +x .git/hooks/pre-commit`

---

## PATTERNS DE COMMIT POUR LES PROJETS DE LÉANDRO

### Agents IA (ECHO, LENS, GHOST, PULSE, SCOUT...)
```
feat(echo): add multi-step research pipeline
fix(lens): resolve heuristic scoring for mobile patterns
docs(agents): update CLAUDE.md with new tool references
refactor(ghost): extract persona templates to JSON
```

### Velours Bleu / NPC / projets perso
```
feat(npc): add charles voice differentiation in Paris script
chore(velours-bleu): update Suno prompt templates
docs(npc): add video production pipeline notes
```

### Projets React/Komga/Frontend
```
feat(ui): add dark mode toggle with localStorage persistence
fix(komga): resolve cover art loading on iPad landscape
refactor(reader): extract page navigation to custom hook
chore(deps): upgrade react-query to v5
```

### EDF/UX Research
```
feat(iris): add WCAG 2.2 criteria to accessibility persona
docs(echo): update research protocol for UX interviews
fix(rgaa): correct contrast ratio calculation for AA level
```
