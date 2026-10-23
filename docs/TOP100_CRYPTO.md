# Top 100 dynamique et identite

`configs/paper.json` active `universe: "cmc_top100"`. A chaque scan PAPER, le moteur recupere les 100 premiers actifs de l'API publique officielle CoinMarketCap `/public-api/v3/cryptocurrency/listings/latest`, sans compte ni cle (capitalisation, USD). Il conserve IDs, noms, slugs, rangs, tags, plateformes et quotes dans un snapshot SQL et calcule les entrees/sorties. Les rangs 1 a 100 et les 100 identifiants uniques sont controles.

Le moteur scanne l'union du classement et des actifs prioritaires : BTC, ETH, SOL, INJ, TRX, PUMP, XRP, BNB, HYPE, UNI, AVAX, AAVE, POL, ALGO, HOOD. La liste prioritaire reste suivie meme hors classement. HOOD correspond a l'action Robinhood Markets (NASDAQ), separee des cryptos. XAUUSD/XAGUSD/NAS100 restent des profils disponibles, a ajouter explicitement a la watchlist pour les surveiller.

Les commandes `scan`, `worker` et l'outil MCP `trading_scan` passent tous par ce meme resolveur. `universe` affiche le resultat sans analyser ni ouvrir de position :

```powershell
python -m agentic_trading.cli universe --config configs/paper.json
python -m agentic_trading.cli scan --config configs/paper.json --bundle CHEMIN_BUNDLE.json
```

Aucune CMC_API_KEY n'est necessaire. Le mode public est utilise par defaut par top100, universe, scan, worker et trading_scan MCP, meme si une cle existe dans l'environnement; aucun en-tete de cle n'est envoye. En cas d'erreur reseau, de limitation HTTP 429 ou de classement incomplet, le statut est FALLBACK_PINNED_ONLY : seuls les actifs prioritaires sont analyses. Aucun ancien snapshot ne se fait passer pour un classement actuel. `universe: "static"` conserve une liste fixe sans appel CMC. BACKTEST/REPLAY ne consultent jamais le classement actuel pour simuler une composition historique; HISTORICAL_UNIVERSE_REQUIRED signale cette limite.

## Identites et donnees necessaires

La collecte des bougies, du calendrier, de la liquidite et des preuves quantitatives reste le role du collecteur de bundles. Cette mise a jour ne cree aucun flux de prix pour les 100 actifs ni pour HOOD. Un actif sans bougies cloturees produit NO_TRADE; aucune specification de courtier n'est inventee. La disponibilite MoonX ne se deduit pas du classement.

Ajouter `asset_identities` a la racine du bundle. Pour chaque actif du classement, renseigner le `cmc_id` reel correspondant au snapshot. Pour un actif prioritaire absent du classement, fournir son `cmc_slug` canonique (voir configs/instrument-profiles.json). PUMP designe pump.fun, slug pump-fun. Un symbole duplique ou incompatible avec l'identite prioritaire est bloque. Pour HOOD, fournir exactement :

```json
{"asset_identities": {
  "PUMP": {"cmc_slug": "pump-fun"},
  "HOOD": {"asset_class": "equity", "exchange": "NASDAQ", "symbol": "HOOD"}
}}
```

Cet exemple ne suffit pas pour PUMP s'il appartient au snapshot Top 100 : son cmc_id est alors obligatoire. Les identites proviennent du fournisseur officiel, pas d'une deduction depuis le ticker. Les stablecoins restent dans les 100 lignes du referentiel et sont exclus des nouvelles opportunites. Les positions ouvertes restent supervisees meme apres sortie du classement ou de la watchlist; fournir leurs bougies au collecteur pour permettre leurs sorties protectrices.

Tous les actifs restent soumis aux memes plafonds de risque, stop obligatoire, liquidite, calendrier et attestations quantitatives. PAPER uniquement; aucun ordre distant n'est active. Les tests unitaires utilisent des reponses synthetiques. La recuperation publique sans cle de 100 actifs et le raccordement au scanner ont aussi ete verifies en lecture seule; voir docs/evidence/public-cmc-update.json. Aucune connexion authentifiee n'est requise ou certifiee.

Sources d'identite : https://coinmarketcap.com/currencies/pump-fun/ et https://robinhood.com/us/en/stocks/HOOD/ . API publique : https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api/ .

L'acces public utilise des limites partagees par adresse IP. Il n'y a pas de boucle de relance immediate : en cas d'echec le moteur annonce son repli, et le worker reessaie au prochain scan configure. Le timestamp du fournisseur et le mode public apparaissent dans le rapport. Les codes de succes 0 et "0", ainsi que les cotations USD en liste (v3) ou dictionnaire (v1), sont normalises avant la sauvegarde. Les donnees incompletes, les cotations USD absentes/dupliquees et les classements invalides sont rejetes.

Compatibilite avancee : le client Python accepte explicitement CoinMarketCapUniverse(access="authenticated") pour l'ancien acces v1 avec CMC_API_KEY. Les commandes et la configuration PAPER utilisent toujours le mode public par defaut.
