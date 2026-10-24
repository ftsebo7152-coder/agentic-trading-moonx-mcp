---
name: agentic-trading-master
description: "Orchestrer le trading PAPER Top 100 CoinMarketCap sans cle et preparer une execution MoonX futures supervisee avec risque et journal."
---

Lire docs/OPERATIONS.md. Vérifier les données et preuves quantitatives. Un résultat BLOCK ou NO_TRADE interdit l’entrée. Gérer les protections existantes avant les nouvelles entrées.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER par defaut. Voie LIVE supervisee MoonX futures implementee separement, non activee et testee uniquement avec transport simule; lire docs/LIVE_TRADING_SAFETY.md. Les permissions de l'hote restent applicables.

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

Passage futur au reel : utiliser exclusivement live-check, live-prepare, live-submit, live-reconcile et live-close selon docs/LIVE_TRADING_SAFETY.md, dans une base et un compte dedies. Settings accepte LIVE_EXECUTION; scan/worker et le MCP PAPER restent simules. Ne jamais modifier configs/paper.json pour activer implicitement le reel.

Avant tout envoi, faire qualifier le schema MoonX reel, les specifications et les protections. La configuration privee enabled=true et TRADING_LIVE_ENABLED=YES permettent le transport; elles ne remplacent pas l'approbation humaine de l'empreinte du plan precis. Presenter entree/SL/TP/taille/perte estimee. Ne jamais s'auto-signer la preuve quantitative. Un seul TP natif et une position a la fois; CFD, HOOD, multi-TP distant et OKX/Bybit restent hors de cette voie.

RECONCILIATION_REQUIRED => aucune nouvelle entree ni relance d'ordre; inspecter la plateforme et executer uniquement la reconciliation ou une fermeture precise approuvee. Preserver journal SQL et stops natifs. Signaler clairement qu'un test avec transport simule ne certifie pas l'execution sur le compte reel.

Extensions de recherche : lire [references/research-extensions.md](references/research-extensions.md) pour collecter les flux publics, construire les partitions purgees/forward, examiner les couts observes, le carnet, les structures SMC, les desks, les theses et le journal de recherche. Depuis la racine du projet installe : `python -m agentic_trading.enhancements.cli --help`. Le chemin global du skill n'est pas la racine du depot; verifier le dossier de travail avant d'executer ces commandes.

La collecte utilise le Top 100 CMC existant, puis des donnees spot USDT OKX/Bybit et, en option, funding/OI OKX, RSS et veille calendrier. Annoncer la couverture reelle et les echecs. Les identites/contrats MoonX restent a qualifier; un flux spot ne fournit pas des specifications futures verifiees. Un calendrier de couverture inconnue conserve le blackout. Ne pas remplacer silencieusement HOOD action par un token, ni un univers historique manquant par le classement actuel.

Les nouvelles revues sont consultatives : opinions sourcees, contre-arguments, disponibilite temporelle et desks manquants. Elles ne remplacent ni le calcul de risque ni les preuves signees. Les partitions CV/forward, structures SMC, VaR historique, couts et echeanciers TWAP sont des diagnostics; aucun de ces resultats n'autorise seul une entree. Fit uniquement dans le train, labels matures, holdout non reutilise et avertissement explicite si une composition historique manque.

Pour un cycle PAPER enrichi : collecter dans un bundle JSON puis appeler `python -m agentic_trading.enhancements.cli cycle --config configs/paper.json --bundle state/research-bundle.json`. Ce cycle appelle le moteur existant et ses protections avant les revues. La file de recherche n'a aucun handler d'ordre et ne demarre aucun service. Aucun ajout ne donne de permission LIVE ni n'active une tache planifiee. Lire docs/SOURCE_INTEGRATION_AUDIT.md pour distinguer concepts examines, ajouts effectifs et capacites non importees.
