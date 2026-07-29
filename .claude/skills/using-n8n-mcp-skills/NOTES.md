# Note d'intégration

Ce pack de 15 skills est conçu pour accompagner le serveur MCP
[n8n-mcp](https://github.com/czlonkowski/n8n-mcp) (même auteur, 21K+ ⭐) :
plusieurs skills référencent directement ses outils (`validate_workflow`,
`get_node`, `n8n_get_workflow`, `n8n_instances`...). Le contenu des
`SKILL.md` (règles, pièges, patterns) reste utile même sans le MCP installé,
mais pour l'usage complet (validation live, recherche de nœuds, gestion
d'instances) il faut configurer le serveur `n8n-mcp` dans le projet cible.

`using-n8n-mcp-skills` est le skill "routeur" du pack — à consulter en
premier sur toute tâche n8n, il oriente vers le skill spécialiste adapté.
