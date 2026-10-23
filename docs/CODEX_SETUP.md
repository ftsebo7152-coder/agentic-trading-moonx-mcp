# Codex

Installer Python puis le projet selon README.md. Ouvrir ce dépôt comme projet et vérifier la présence du skill `agentic-trading-master` dans le sélecteur. Invocation explicite : `$agentic-trading-master`. Le dossier canonique est `.agents/skills`.

Documentation officielle consultée : [Build skills](https://learn.chatgpt.com/docs/build-skills), [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app). Le chargement réel dépend de la surface, des politiques et de l'environnement de travail. Les 29 fichiers ont été créés et validés; aucune nouvelle session Codex ni tâche distante n'a été utilisée pour certifier leur découverte.

MCP local optionnel : installer `python -m pip install -e ".[mcp]"`, puis enregistrer dans le client une commande stdio `python -m agentic_trading.cli --database CHEMIN_PERSISTANT mcp-server`. Configurer TRADING_CONFIG_PATH et TRADING_BUNDLE_PATH côté service, en lecture seule. Le serveur expose report, halt et scan PAPER, pas de mutation des plafonds ni d'ordre distant.

Connecter MoonX via l'interface des connecteurs ou la configuration MCP autorisée, puis tester une lecture sur la surface cible. Ne pas exporter automatiquement la connexion personnelle vers un cloud. Les templates se trouvent dans templates/codex. Aucun besoin de clé OpenAI API pour le noyau déterministe; le client agent utilise son propre environnement autorisé.
