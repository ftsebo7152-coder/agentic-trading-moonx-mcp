---
name: agentic-trading-master
description: "Orchestrer le trading PAPER avec univers Top 100 CoinMarketCap sans cle et actifs prioritaires, analyse, risque et journal."
---

Lire docs/OPERATIONS.md. Vérifier les données et preuves quantitatives. Un résultat BLOCK ou NO_TRADE interdit l’entrée. Gérer les protections existantes avant les nouvelles entrées.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli scan --config configs/paper.json --bundle examples/synthetic-market.json
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.

Univers : utiliser configs/paper.json avec universe=cmc_top100. Avant un scan, lire docs/TOP100_CRYPTO.md et examiner `python -m agentic_trading.cli universe --config configs/paper.json`. Le moteur raccorde automatiquement cet univers a scan, worker et trading_scan MCP.

Conserver BTC, ETH, SOL, INJ, TRX, PUMP (pump.fun), XRP, BNB, HYPE, UNI, AVAX, AAVE, POL, ALGO et HOOD dans les priorites, meme hors Top 100. HOOD est ici l'action Robinhood Markets, NASDAQ; ne pas substituer un token homonyme. Les autres cryptos viennent exclusivement du snapshot CMC valide, pas d'une liste memorisee ni du classement CoinGecko.

Le classement actuel utilise par defaut l'API publique CoinMarketCap /public-api/v3/cryptocurrency/listings/latest, sans compte ni CMC_API_KEY, meme si une cle existe dans l'environnement. Examiner universe.access=public, le timestamp du fournisseur et les 100 identifiants/rangs valides. Si universe.status=FALLBACK_PINNED_ONLY, annoncer explicitement la couverture reduite. L'acces public reste soumis aux limites par adresse IP; ne pas multiplier les relances en cas de HTTP 429. Un skill ne fournit aucun flux de bougies. Faire fournir par le collecteur asset_identities (cmc_id pour les actifs du snapshot; cmc_slug pour les priorites absentes; asset_class=equity/exchange=NASDAQ/symbol=HOOD pour HOOD), donnees de marche et specifications confirmees. Ne jamais inventer ces valeurs.

Stablecoins et identites ambigues sont exclus des entrees. Conserver les bougies des positions sorties du classement pour leurs protections. Donnees absentes => NO_TRADE; ne pas elargir les plafonds de risque pour couvrir davantage d'actifs. BACKTEST/REPLAY exigent des compositions historiques; aucun classement actuel ne justifie un backtest Top 100.

Executer depuis la racine du depot installe. Invocation : `$agentic-trading-master`. La mise a jour du skill ne demarre ni worker ni tache planifiee.
