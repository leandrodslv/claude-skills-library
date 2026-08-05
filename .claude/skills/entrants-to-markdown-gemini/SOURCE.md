# Origine de ce skill

Skill personnel, variante de `entrants-to-markdown` (également personnel).

**Différence avec `entrants-to-markdown` :** la phase de lecture des fichiers
visuels (SVG, PNG, JPG, GIF, WEBP, BMP, TIFF, schémas, captures d'écran) n'est
plus confiée à l'outil de vision de Claude (`view`), mais automatisée par un
appel direct du script Python à l'**API Gemini** (modèle multimodal). Cela
évite de consommer le contexte de la conversation quand le dossier d'entrants
contient beaucoup de visuels.

Le script dégrade proprement vers le comportement d'origine (fichiers listés
pour traitement manuel par Claude) si aucune clé API Gemini n'est disponible,
si un appel échoue, ou si `--skip-gemini` est passé explicitement.

Nécessite une clé API Gemini gratuite : https://aistudio.google.com/apikey
