# Top 100 dynamique et identite

`configs/paper.json` active `universe: "cmc_top100"`. A chaque scan PAPER, le moteur recupere les 100 premiers actifs de l'API officielle CoinMarketCap `/v1/cryptocurrency/listings/latest` (capitalisation, USD). Il conserve IDs, noms, slugs, rangs, tags, plateformes et quotes dans un snapshot SQL et calcule les entrees/sorties. Les rangs 1 a 100 et les 100 identifiants uniques sont controles.

Le moteur scanne l'union du classement et des actifs prioritaires : BTC, ETH, SOL, INJ, TRX, PUMP, XRP, BNB, HYPE, UNI, AVAX, AAVE, POL, ALGO, HOOD. La liste prioritaire reste suivie meme hors classement. HOOD correspond a l'action Robinhood Markets (NASDAQ), separee des cryptos. XAUUSD/XAGUSD/NAS100 restent des profils disponibles, a ajouter explicitement a la watchlist pour les surveiller.

Les commandes `scan`, `worker` et l'outil MCP `trading_scan` passent tous par ce meme resolveur. `universe` affiche le resultat sans analyser ni ouvrir de position :

```powershell
python -m agentic_trading.cli universe --config configs/paper.json
python -m agentic_trading.cli scan --config configs/paper.json --bundle CHEMIN_BUNDLE.json
```

Charger CMC_API_KEY depuis le .env prive ignore ou le gestionnaire de secrets. Ne pas publier la cle. Sans cle valide, en cas d'erreur reseau ou de classement incomplet, le statut est FALLBACK_PINNED_ONLY : seuls les actifs prioritaires sont analyses. Aucun ancien snapshot ne se fait passer pour un classement actuel. `universe: "static"` conserve une liste fixe sans appel CMC. BACKTEST/REPLAY ne consultent jamais le classement actuel pour simuler une composition historique; HISTORICAL_UNIVERSE_REQUIRED signale cette limite.

## Identites et donnees necessaires

La collecte des bougies, du calendrier, de la liquidite et des preuves quantitatives reste le role du collecteur de bundles. Cette mise a jour ne cree aucun flux de prix pour les 100 actifs ni pour HOOD. Un actif sans bougies cloturees produit NO_TRADE; aucune specification de courtier n'est inventee. La disponibilite MoonX ne se deduit pas du classement.

Ajouter `asset_identities` a la racine du bundle. Pour chaque actif du classement, renseigner le `cmc_id` reel correspondant au snapshot. Pour un actif prioritaire absent du classement, fournir son `cmc_slug` canonique (voir configs/instrument-profiles.json). PUMP designe pump.fun, slug pump-fun. Un symbole duplique ou incompatible avec l'identite prioritaire est bloque. Pour HOOD, fournir exactement :

```json
{"asset_identities": {
  "PUMP": {"cmc_slug": "pump-fun"},
  "HOOD": {"asset_class": "equity", "exchange": "NASDAQ", "symbol": "HOOD"}
}}
```

Cet exemple ne suffit pas pour PUMP s'il appartient au snapshot Top 100 : son cmc_id est alors obligatoire. Les identites proviennent du fournisseur authentifie, pas d'une deduction depuis le ticker. Les stablecoins restent dans les 100 lignes du referentiel et sont exclus des nouvelles opportunites. Les positions ouvertes restent supervisees meme apres sortie du classement ou de la watchlist; fournir leurs bougies au collecteur pour permettre leurs sorties protectrices.

Tous les actifs restent soumis aux memes plafonds de risque, stop obligatoire, liquidite, calendrier et attestations quantitatives. PAPER uniquement; aucun ordre distant n'est active. Le test Top 100 utilise des reponses synthetiques; une recuperation authentifiee de 100 actifs n'a pas ete certifiee sur ce poste.

Sources d'identite : https://coinmarketcap.com/currencies/pump-fun/ et https://robinhood.com/us/en/stocks/HOOD/ . API : https://coinmarketcap.com/api/documentation/ .
