# Référence — Issues GitHub

Toutes les commandes supposent `gh auth status` OK et un `cwd` dans le repo.
Ajouter `--repo owner/name` pour agir sur un autre dépôt.

---

## LISTER & RECHERCHER

```bash
gh issue list                                   # ouvertes, 30 par défaut
gh issue list --state all --limit 100
gh issue list --assignee @me
gh issue list --author leandrodslv
gh issue list --label bug --label "priority:high"   # ET logique
gh issue list --milestone "v1.0"
gh issue list --search "magic link in:title"
gh issue list --search "sort:created-asc no:assignee"    # backlog non pris

# Sortie exploitable par script / par l'agent
gh issue list --json number,title,labels,assignees,state
gh issue list --json number,title -q '.[] | "#\(.number) \(.title)"'

# Trier par ancienneté, prendre la prochaine à traiter
gh issue list --state open --search "no:assignee sort:created-asc" --limit 1 \
  --json number,title -q '.[0]'
```

Qualificateurs de recherche utiles : `no:assignee`, `no:label`, `is:open`,
`in:title`, `in:body`, `sort:created-asc|updated-desc|comments-desc`,
`linked:pr` (issues avec une PR liée), `-linked:pr` (sans).

---

## LIRE

```bash
gh issue view 3                     # description
gh issue view 3 --comments          # ⭐ description + toute la discussion
gh issue view 3 --web               # ouvrir dans le navigateur
gh issue view 3 --json title,body,labels,comments
```

**Toujours** `--comments` avant d'implémenter : les précisions et changements de
périmètre vivent presque toujours dans les commentaires, pas dans la description.

---

## CRÉER

```bash
# Interactif
gh issue create

# Complet, non interactif (heredoc pour le markdown multi-ligne)
gh issue create \
  --title "feat: documents compagnons rattachés aux vidéos" \
  --label enhancement --label "area:content" \
  --assignee @me \
  --milestone "v1.2" \
  --body "$(cat <<'EOF'
## Contexte
Chaque vidéo de cours gagnerait à embarquer des ressources téléchargeables
(PDF, snippets, checklists) au lieu de les disperser dans la description.

## Objectif
Permettre d'attacher N documents à une vidéo et de les exposer sous le lecteur.

## Critères d'acceptation
- [ ] Table `companion_documents` (video_id, title, file_url, order)
- [ ] Upload depuis l'admin (PDF, md, zip — 20 Mo max)
- [ ] Liste téléchargeable sous le player, triée par `order`
- [ ] Aucun document visible si la vidéo n'est pas accessible à l'utilisateur

## Hors périmètre
- Versioning des documents
- Prévisualisation inline
EOF
)"

# Depuis un fichier
gh issue create --title "fix: ..." --body-file ./bug-report.md
```

### Anatomie d'une bonne issue (celle que l'agent saura implémenter seul)

1. **Titre conventionnel** — `feat: ...`, `fix: ...` → réutilisable tel quel en titre de PR
2. **Contexte** — le pourquoi, en 2-3 lignes
3. **Objectif** — une phrase
4. **Critères d'acceptation** — cases à cocher, testables, sans ambiguïté
5. **Hors périmètre** — ce qu'il ne faut *pas* faire (évite la dérive de scope)
6. **Pointeurs** — fichiers/modules concernés, maquette, doc externe

---

## MODIFIER & FERMER

```bash
gh issue edit 3 --add-assignee @me
gh issue edit 3 --add-label "in-progress" --remove-label "backlog"
gh issue edit 3 --milestone "v1.2"
gh issue edit 3 --title "feat(auth): connexion par lien magique"
gh issue edit 3 --body-file ./nouvelle-description.md

gh issue comment 3 --body "Implémenté dans #14. Reste à valider l'expiration en preview."
gh issue close 3 --comment "Livré en v1.3.0"
gh issue close 3 --reason "not planned"
gh issue reopen 3

gh issue pin 3 / gh issue unpin 3
gh issue transfer 3 owner/autre-repo
gh issue develop 3 --checkout --name feat/3-magic-link   # crée la branche liée à l'issue
```

`gh issue develop` est le raccourci natif : il crée une branche **rattachée** à l'issue
côté GitHub (visible dans l'encart "Development"), en plus de la checkout localement.

---

## FERMETURE AUTOMATIQUE VIA COMMIT / PR

Mots-clés reconnus par GitHub dans le corps d'un commit ou d'une PR :

```
close #12   closes #12   closed #12
fix #12     fixes #12    fixed #12
resolve #12 resolves #12 resolved #12
```

- La fermeture n'a lieu **qu'au merge sur la branche par défaut**.
- Plusieurs issues : `Closes #12, closes #13` (répéter le mot-clé, une virgule ne suffit pas).
- Autre repo : `Closes owner/repo#12`.
- ⚠️ Ne pas mettre le mot-clé dans le *titre* de la PR — GitHub ne lit que le corps.

---

## CRÉATION EN BATCH (backlog → issues)

Depuis une liste de tâches, générer les issues d'un coup :

```bash
while IFS='|' read -r title label; do
  gh issue create --title "$title" --label "$label" --body "À détailler."
done <<'EOF'
feat: connexion par lien magique|enhancement
feat: documents compagnons|enhancement
fix: chargement des covers sur iPad|bug
chore: passer le CI en jobs parallèles|chore
EOF
```

Depuis un JSON structuré (plus robuste pour des corps multi-lignes) :

```bash
jq -c '.[]' backlog.json | while read -r row; do
  gh issue create \
    --title "$(jq -r '.title' <<<"$row")" \
    --body  "$(jq -r '.body'  <<<"$row")" \
    --label "$(jq -r '.labels | join(",")' <<<"$row")"
done
```

---

## LABELS

```bash
gh label list
gh label create "area:auth" --color "1D76DB" --description "Authentification"
gh label create "priority:high" --color "D93F0B"
gh label edit bug --color "B60205"
gh label delete wontfix --yes
gh label clone owner/autre-repo          # importer un jeu de labels existant
```

Taxonomie recommandée (préfixée = triable et lisible) :

| Préfixe | Exemples |
|---|---|
| `type:` | `type:feat`, `type:bug`, `type:chore`, `type:docs` |
| `area:` | `area:auth`, `area:ui`, `area:ci`, `area:db` |
| `priority:` | `priority:high`, `priority:medium`, `priority:low` |
| statut | `blocked`, `in-progress`, `needs-design`, `good first issue` |

---

## MILESTONES

Pas de commande `gh milestone` native → passer par l'API :

```bash
gh api repos/{owner}/{repo}/milestones --jq '.[] | "\(.number) \(.title) (\(.open_issues) open)"'

gh api repos/{owner}/{repo}/milestones -f title="v1.2" \
  -f description="Documents compagnons + magic link" -f due_on="2026-09-01T00:00:00Z"

gh issue edit 3 --milestone "v1.2"
```

---

## TEMPLATES D'ISSUE

Fichiers dans `.github/ISSUE_TEMPLATE/`.

`.github/ISSUE_TEMPLATE/feature.yml` :

```yaml
name: Fonctionnalité
description: Proposer une nouvelle fonctionnalité
title: "feat: "
labels: ["type:feat"]
body:
  - type: textarea
    id: contexte
    attributes:
      label: Contexte
      description: Quel problème cela résout-il ?
    validations: { required: true }
  - type: textarea
    id: acceptance
    attributes:
      label: Critères d'acceptation
      value: |
        - [ ] 
        - [ ] 
    validations: { required: true }
  - type: textarea
    id: hors-perimetre
    attributes:
      label: Hors périmètre
  - type: dropdown
    id: priority
    attributes:
      label: Priorité
      options: [low, medium, high]
```

`.github/ISSUE_TEMPLATE/config.yml` :

```yaml
blank_issues_enabled: false
contact_links:
  - name: Question
    url: https://github.com/OWNER/REPO/discussions
    about: Pour les questions, utiliser les Discussions.
```

---

## PROJECTS (v2)

```bash
gh project list --owner leandrodslv
gh project view 1 --owner leandrodslv
gh project item-list 1 --owner leandrodslv
gh project item-add 1 --owner leandrodslv --url https://github.com/OWNER/REPO/issues/3
gh project field-list 1 --owner leandrodslv
```

Nécessite le scope `project` sur le token : `gh auth refresh -s project`

---

## LIER ISSUES ↔ PR

```bash
gh pr view 14 --json closingIssuesReferences -q '.closingIssuesReferences[].number'
gh issue view 3 --json url,title,state
gh issue list --search "-linked:pr is:open"      # issues sans PR en cours
```

---

## RACCOURCIS UTILES POUR L'AGENT

```bash
# Prochaine issue à traiter (la plus ancienne, non assignée, non bloquée)
gh issue list --state open --search "no:assignee -label:blocked sort:created-asc" \
  --limit 1 --json number,title,body

# Toutes les issues d'un milestone, prêtes à être découpées en branches
gh issue list --milestone "v1.2" --state open --json number,title \
  -q '.[] | "feat/\(.number)-\(.title | ascii_downcase | gsub("[^a-z0-9]+"; "-"))"'

# Vérifier avant merge que la PR ferme bien une issue
gh pr view --json closingIssuesReferences -q '.closingIssuesReferences | length'
```
