# MoonX MCP

L'accès prioritaire passe exclusivement par le serveur MCP officiel : https://api.moon-x.io/mcp . Le connecteur déjà disponible dans Codex a retourné le prix BTC et 100 bougies H1. Le dépôt ne contient pas le jeton de cette connexion.

Installer l'option : `python -m pip install -e ".[mcp]"`. Renseigner MOONX_MCP_URL dans le gestionnaire de secrets ou le .env ignoré, puis `python -m agentic_trading.cli moonx-read --symbol BTC --output state/btc.json`. La commande n'expose que des lectures. Ne pas copier l'URL privée dans un prompt, une sortie terminal, un commit ou une notification.

Le client SDK autonome n'a pas ete authentifie pendant la livraison. La nouvelle voie LiveExecution utilise un transport SDK explicitement autorise a ouvrir/fermer les futures via live-* (voir LIVE_TRADING_SAFETY.md). Les anciens ports generiques prepare/submit restent des interfaces de preparation. Les schemas, contrats et protections doivent etre qualifies sur la plateforme.

La voie reelle supervisee supporte un stop et un seul TP natifs. Les trois sorties partielles distantes ne sont pas implementees; les trois objectifs PAPER ne sont jamais convertis silencieusement. Les CFD necessitent une autre conversion de contrats et ne sont pas admis dans cette voie.

La diligence fournisseur reste incomplète. Les [conditions](https://moon-x.io/terms/) et la [déclaration de risques](https://moon-x.io/risk-disclaimer/) ont été consultées. L'identité légale, l'autorité compétente, la conservation et ségrégation des fonds, les protections et mécanismes de recours n'ont pas fait l'objet d'une vérification indépendante. Les frais et règles de liquidation par instrument restent à confirmer. Les restrictions géographiques doivent être confrontées à la situation effective de l'utilisateur. Aucune qualification de fournisseur réglementé ou prêt pour le réel n'est accordée.
