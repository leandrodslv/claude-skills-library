# Modèle de rapport de banc d'essai

Écrire dans `.claude/banc/rapports/<runId>.md`. Structure imposée ci-dessous.
Le rapport s'adresse à quelqu'un qui va modifier le prompt de l'agent juste
après : chaque défaut doit pointer vers l'endroit à corriger.

---

```markdown
# Banc d'essai — [nom de la cible] — [scénario] — [date]

**Moteur** : [claude-code | gemini | commande] · **Modèle** : [modèle]
**Run** : `[runId]` · **Tours** : [N] · **Coût** : [X] USD · **Durée** : [X] min

## Verdict

> **[TIENT LA ROUTE | TIENT AVEC RÉSERVES | NE TIENT PAS]** — [une phrase, la
> plus importante du rapport : ce que le pilote doit retenir]

## Déroulé

| # | Message envoyé | Ce que l'agent a fait | Vérifs |
|---|---|---|---|
| 1 | [résumé en 6 mots] | [résumé en 10 mots] | 4/4 |
| 2 | … | … | 3/5 ❌ |

## ✅ Ce qui tient

- **[Titre du point fort]** — [ce qui a été observé].
  *Preuve : tour 2, `[chemin du fichier]` ou citation.*

## ❌ Ce qui casse

### [bloquant | majeur | mineur] · [Titre court du défaut]

**Symptôme** — [ce qui s'est passé].
**Preuve** — tour [N] : [citation exacte, ou chemin du fichier].
**Cause probable** — [ce que le contrat dit ou ne dit pas, fichier + section].
**Conséquence** — [ce que l'humain doit rattraper à la main].

## ⚠️ Recommandations

### P1 · [Titre]
- **Où** : `[fichier de contrat]`, section « [section] »
- **Quoi** : [la modification, précise — idéalement la ligne à ajouter]
- **Effet attendu** : [ce que ça corrige, avec le tour concerné]
- **À reporter aussi dans** : [autres copies du contrat, s'il y en a]

### P2 · …
### P3 · …

## Angles morts de ce run

[Les règles du contrat que ce scénario n'a pas éprouvées, et ce qui reste
inconnu. Toujours rempli : un rapport qui ne dit pas ce qu'il n'a pas testé se
fait lire comme un certificat de conformité.]

## Artefacts

- Manifeste : `.claude/banc/runs/[runId]/run.json`
- Réponses : `.claude/banc/runs/[runId]/tours/`
- Fichiers produits : `[chemin du bac à sable]`
- Nettoyage : `banc-agent.ps1 -Nettoyer [runId]`
```

---

## Règles de rédaction

- **Priorités** : P1 = à corriger avant la prochaine utilisation réelle.
  P2 = à la prochaine passe. P3 = confort.
- **Une reco = une modification.** Si elle demande trois phrases de contexte
  avant d'arriver au changement, elle n'est pas mûre.
- **Pas de reco sans défaut observé** dans ce run. Les bonnes idées générales
  sur le prompt vont ailleurs, pas dans un rapport de test.
- **Citer, pas paraphraser.** Une citation entre guillemets vaut dix lignes de
  description.
- **Distinguer la faute de l'agent de la faute du contrat.** Un agent qui suit
  une instruction contradictoire n'a pas échoué : c'est l'instruction qui doit
  changer.
- **Les succès non triviaux se rapportent** : un refus de publier, un refus
  d'inventer, une limite énoncée spontanément. Ce sont eux qui indiquent
  quelles règles tiennent réellement la charge.
