# Agentic Trading MoonX MCP

Version **0.1.0**, développement prioritairement en français. Infrastructure installable de recherche et de **PAPER local**, avec moteur de risque déterministe, stockage persistant, sorties partielles et file d'e-mails. Aucune transaction réelle n'est autorisée par ce runtime.

Ce dépôt traduit le cahier des charges PDF de 55 pages en un premier logiciel vérifiable. Il ne constitue pas encore la totalité de l'infrastructure de production demandée. Le statut de chaque exigence et les blocages sont dans [REQUIREMENTS.md](docs/REQUIREMENTS.md) et [ROADMAP.md](docs/ROADMAP.md).

## Démarrage

Python 3.11 ou plus récent. Depuis la racine du dépôt, sous Windows :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m agentic_trading.cli --database state/demo.sqlite demo --output state/demo-result.json
```

Linux :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m agentic_trading.cli --database state/demo.sqlite demo --output state/demo-result.json
```

La commande `demo` utilise des **prix synthétiques explicitement identifiés**. Elle ouvre une position fictive avec stop, déclenche trois sorties partielles, clôture la position et écrit quatre notifications dans une file persistante. Le scénario se répète sans créer de doublon si la même base et le même compte sont réutilisés. Les résultats ne mesurent aucune rentabilité de marché.

Le résultat réellement produit pendant la livraison est dans [paper-demo-result.json](examples/paper-demo-result.json). Les 100 bougies BTC reçues du MCP MoonX sont conservées séparément dans [moonx-btc-1h-observed.json](examples/moonx-btc-1h-observed.json).

## Fonctionnalités opérationnelles

- Modèles typés et calculs financiers en `Decimal` : quantité, marge, notionnel, risque net, sortie pondérée et liquidation approximative.
- RSI, MACD, EMA 20/50/100/200, SMA, ATR, ADX, Bollinger, VWAP UTC, volume relatif, momentum et niveaux précédents.
- Cassure de range sur clôture suivie d'une confirmation. Classification de régime et score explicable, seuil 67/100.
- Risk engine indépendant : stop obligatoire, fraîcheur, précision, coûts, marge, levier, exposition, corrélation, pertes et plafond de dix entrées par jour.
- Simulateur LONG/SHORT, spreads, frais, slippage, financement paramétrable, stops sur gap, trois TP partiels et reprise de l'état.
- SQLite transactionnel, idempotence par compte/signal, sérialisation des entrées et outbox d'e-mails atomique avec les opérations.
- Backtest chronologique, walk-forward générique, bootstrap, Monte Carlo reproductible, stress de coûts, métriques et tests de calibration.
- Calendrier macro avec blackout fermé en cas de couverture inconnue; données disponibles à la date de décision uniquement.
- 29 skills Codex dans `.agents/skills` et 29 copies Claude générées dans `.claude/skills`.
- Worker configurable, serveur MCP local PAPER optionnel et templates de tâches.

## État réel des connecteurs

| Connecteur | Livré et vérifié | Reste à qualifier |
|---|---|---|
| MoonX | 35 déclarations MCP inventoriées; prix BTC et 100 bougies reçus via le MCP connecté; client de lecture et préparation d'intentions testés avec mocks | Client autonome du dépôt non authentifié dans le cloud; spécifications des contrats; exécution et réconciliation distantes; trois TP natifs non démontrés |
| OKX | Documentation MCP officielle examinée; constructeur de requête démo avec `x-simulated-trading: 1`, stop et TP; tests de contrat locaux | Clés démo, connexion authentifiée, transport d'ordres, réconciliation, validation des contrats et du compte |
| Bybit | Serveur MCP officiel identifié; domaine démo officiel et constructeur de requête avec stop/TP; tests locaux | Clés démo; support du domaine démo dans la version MCP choisie; transport d'ordres, compte et réconciliation |

Les adaptateurs refusent la soumission distante dans cette version. Le moteur PAPER n'a aucune référence à un transport réseau de courtage. Aucune bascule automatique vers un autre exchange n'existe. Voir [BROKER_COMPATIBILITY.md](docs/BROKER_COMPATIBILITY.md).

## Données, validation et notifications

La configuration normale est [configs/paper.json](configs/paper.json). Elle conserve 15 actifs prioritaires et ajoute le Top 100 CMC lorsque la source est disponible. Les contrats fournis comme profils sont **non vérifiés**, à l'exception des contrats fictifs de l'exemple. Le système s'abstient lorsqu'un contrat, la liquidité, le calendrier ou la validation quantitative manque.

```sh
python -m agentic_trading.cli scan --config configs/paper.json --bundle examples/synthetic-market.json
python -m agentic_trading.cli backtest --bundle examples/synthetic-market.json --symbol BTC --output state/backtest.json
python -m agentic_trading.cli report --account local-paper
```

Le premier scan normal s'abstient : les données sont historiques et aucune stratégie n'est qualifiée. Le backtest synthétique teste le logiciel; il n'est pas une qualification financière. Une attestation quantitative signée et limitée dans le temps est nécessaire au flux normal; un booléen dans un prompt ne la remplace pas.

Les événements OPEN/EXIT alimentent automatiquement l'outbox. Configurer `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `TRADING_EMAIL_TO` dans `.env` privé ou le gestionnaire de secrets; puis exécuter :

```sh
python -m agentic_trading.cli notify
```

Sans SMTP, les messages restent `PENDING`. `SMTP_ACCEPTED` signifie prise en charge par le serveur, pas livraison dans la boîte. Aucune adresse réelle ni secret n'est commité. Voir [NOTIFICATIONS.md](docs/NOTIFICATIONS.md).

## Skills et déploiement

Codex : ouvrir le dépôt et invoquer `$agentic-trading-master`. Claude Code : `/agentic-trading-master`. La génération et la synchronisation se font avec `python scripts/sync_skills.py`. Leur présence et leur validité sont testées; leur chargement dans chaque service distant doit être vérifié sur place.

Les exemples de tâches sont dans `templates/`. Le service doit disposer d'un disque persistant ou de PostgreSQL, d'un collecteur de données fraîches et d'un moniteur distinct du scan horaire. Le code PostgreSQL est fourni, mais n'a pas été testé contre un serveur pendant cette livraison. Aucun service cloud ni tâche récurrente n'a été activé automatiquement.

## Origine et limites

Les deux sources sont conservées, licences et attributions incluses, dans `vendor/`. Le nouveau noyau est écrit séparément. Les modules actions américaines, SEC et Congrès restent accessibles comme outils de recherche hérités; ils ne deviennent pas des signaux crypto. Le pont TradingView/CDP est optionnel et n'est pas démarré par le runtime.

Lire [SOURCE_AUDIT.md](docs/SOURCE_AUDIT.md), [TEST_RESULTS.md](docs/TEST_RESULTS.md), [LIVE_TRADING_SAFETY.md](docs/LIVE_TRADING_SAFETY.md) et [DELIVERY.md](docs/DELIVERY.md). Aucune performance attendue ou garantie de gain n'est annoncée.

## Mise a jour de l'univers surveille

La configuration PAPER raccorde automatiquement le Top 100 CoinMarketCap a chaque scan et conserve les 15 actifs prioritaires, dont PUMP et HOOD (action NASDAQ). L'API publique officielle est utilisee sans cle. En cas d'indisponibilite ou de limitation, repli explicite sur les priorites. La couverture des prix et fondamentaux depend du collecteur de bundles; aucun flux supplementaire ni ordre reel n'est active. Voir [Top 100 et identites](docs/TOP100_CRYPTO.md).
