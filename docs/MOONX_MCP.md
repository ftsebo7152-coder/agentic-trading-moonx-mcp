# MoonX MCP

L'accès prioritaire passe exclusivement par le serveur MCP officiel : https://api.moon-x.io/mcp . Le connecteur déjà disponible dans Codex a retourné le prix BTC et 100 bougies H1. Le dépôt ne contient pas le jeton de cette connexion.

Installer l'option : `python -m pip install -e ".[mcp]"`. Renseigner MOONX_MCP_URL dans le gestionnaire de secrets ou le .env ignoré, puis `python -m agentic_trading.cli moonx-read --symbol BTC --output state/btc.json`. La commande n'expose que des lectures. Ne pas copier l'URL privée dans un prompt, une sortie terminal, un commit ou une notification.

Le client SDK autonome n'a pas été authentifié pendant la livraison. Les observations positives portent sur le MCP connecté à cette session, pas sur un déploiement cloud. Les spécifications de contrats, paliers de marge, quantités et liquidations doivent être vérifiés individuellement. `MoonXBrokerAdapter.prepare` produit une intention non envoyée et `submit` refuse toute exécution.

Les trois TP natifs ne sont pas démontrés. Un TP final et un stop dans l'intention ne simulent pas trois ordres hébergés. Le logiciel sait répartir des sorties en PAPER local; la gestion distante reste à développer et qualifier. Fermeture partielle futures déclarée, fermeture partielle Forex non exposée par la signature observée.

La diligence fournisseur reste incomplète. Les [conditions](https://moon-x.io/terms/) et la [déclaration de risques](https://moon-x.io/risk-disclaimer/) ont été consultées. L'identité légale, l'autorité compétente, la conservation et ségrégation des fonds, les protections et mécanismes de recours n'ont pas fait l'objet d'une vérification indépendante. Les frais et règles de liquidation par instrument restent à confirmer. Les restrictions géographiques doivent être confrontées à la situation effective de l'utilisateur. Aucune qualification de fournisseur réglementé ou prêt pour le réel n'est accordée.
