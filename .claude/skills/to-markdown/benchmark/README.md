# Banc d'essai de to-markdown

Mesure reproductible de la qualité de conversion, contre d'autres convertisseurs, sur des documents dont **le contenu exact est connu**.

```bash
python3 benchmark/run.py            # génère le corpus, convertit, réécrit RESULTS.md
python3 benchmark/run.py --keep corpus/ --json mesures.json
python3 benchmark/run.py --only mdconv-natif,markitdown --out -
```

Résultats publiés : [`RESULTS.md`](RESULTS.md). La batterie de documents difficiles : [`hard/README.md`](hard/README.md).

## Méthode

1. **Quatre documents décrits une fois** (titres, paragraphes, listes à puces et numérotées, tableau, lien ; deux en français avec accents, deux en anglais) — `corpus.py`.
2. **Écrits par des outils tiers**, jamais par mdconv : `python-docx` (DOCX), `python-pptx` (PPTX), `openpyxl` (XLSX), LibreOffice (DOCX, ODT, RTF, PDF à partir de HTML), un écrivain CSV et HTML. La vérité (mots, titres, cellules, éléments de liste, liens) vient de la description, pas d'un convertisseur.
3. **Chaque convertisseur lit chaque fichier** ; la sortie est notée :
   - **Rappel** — part des mots du contenu retrouvés (multiensemble, sans casse ni ponctuation) ;
   - **Précision** — part de la sortie qui est du vrai contenu (pénalise doublons, bruit, métadonnées ajoutées) ;
   - **Titres / Tableaux / Listes / Liens** — éléments de structure retrouvés *comme structure Markdown* (ligne `#`, ligne de tableau `|`, puce ou numéro, `[texte](url)`).
   - Front matter YAML, adresses et puces/numéros de liste sont neutralisés pour tous de la même façon.
4. **Concurrents mesurés quand ils sont installés** : markitdown, pandoc (`-t gfm`), pymupdf4llm, pdftotext. Un outil absent disparaît du tableau, sans erreur. Les versions sont inscrites dans `RESULTS.md`.

`mdconv-natif` = bibliothèque standard seule (`--no-external`) ; `mdconv-auto` = avec les moteurs externes présents sur la machine du test.

## Ce que ce banc d'essai ne prouve pas

- **Le corpus est propre et simple.** Quatre documents fabriqués, sans mise en page tordue : un score proche de 100 % montre qu'on ne perd rien sur le cas facile, pas qu'on gagne sur le difficile. C'est le rôle de [`hard/`](hard/README.md).
- **Auteur et juge sont la même personne.** Le banc d'essai a été écrit par l'auteur de mdconv. Pour limiter le biais, les producteurs sont tiers et le code est ouvert, mais il faut le relancer sur vos propres fichiers avant de vous fier à un chiffre.
- **Les scores mesurent le texte et la structure, pas la mise en page.** Ni l'ordre de lecture sur plusieurs colonnes, ni les images, ni la fidélité visuelle.
- **Temps** : convertisseur déjà chargé en mémoire (pandoc et pdftotext : un processus par fichier). Ne comparez que les ordres de grandeur.
- **Versions** : les résultats dépendent des versions installées (ex. cette version de markitdown ne lit pas l'ODT ni le RTF proprement).

## Lire un résultat

Un « — » veut dire « sans objet » (pas de liste dans un CSV). Un score bas sur une ligne précise est une piste d'amélioration : ouvrez le fichier correspondant avec `--keep`, convertissez-le et comparez. Les mesures détaillées par fichier sont dans la sortie `--json`.
