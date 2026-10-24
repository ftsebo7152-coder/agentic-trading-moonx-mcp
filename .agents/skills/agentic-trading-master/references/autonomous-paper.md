# Moteur PAPER multi-actifs et multi-stratégies

Extension du 24 octobre 2026. Les commandes historiques, les modules de recherche et les 29 skills sont conservés. Le nouveau parcours est `python -m agentic_trading.autonomy.cli`. Il accepte uniquement PAPER et n'importe aucun exécuteur LIVE. Un résultat de simulation ne constitue pas une validation financière.

## Capacités effectivement raccordées

| Élément | Comportement |
|---|---|
| Multi-timeframe | Vérification des bougies clôturées, alignement UTC, trous sur marchés continus, profondeur historique et dernière clôture supérieure attendue. La confirmation produit ses dates, EMA20/50, ADX et raisons de refus. |
| Multi-stratégies | Six règles explicites, sélection selon l'ordre administratif, abstention en cas de signaux opposés. Une preuve valide est privilégiée parmi les candidats du même sens. |
| Multi-actifs | Univers CMC et priorités historiques, plus XAUUSD, XAGUSD et NAS100 dans une nouvelle configuration; HOOD conserve son identité d'action NASDAQ. |
| Risque partagé | Même compte PAPER et mêmes plafonds pour toutes les stratégies et tous les actifs. Stop, sizing net des coûts, limites de pertes et d'exposition restent dans le moteur déterministe. |
| Validation | Une attestation indépendante par instrument, stratégie, politique et base de prix. Aucune signature créée par l'agent. |
| Supervision | Bougies à la minute des positions ouvertes, contrôle indépendant de la collecte plus longue, protections avant les entrées. Les stops simulés ne sont pas des stops natifs de plateforme. |
| Reprise | Bail SQLite par compte, heartbeat, contrôle du jeton dans la transaction de risque et cycle enregistré par dernière bougie/politique. Les identifiants de signal empêchent les doubles positions après reprise. |
| Incidents | Un trou d'historique de supervision reste enregistré et bloque les entrées jusqu'à revue explicite. Les autres données protectrices disponibles continuent d'être traitées. |
| Recherche quantitative | Replay chronologique multi-actifs avec compte partagé, entrée à l'ouverture suivante et coûts adverses; sélection walk-forward bornée, entraînement antérieur au test avec embargo. |

## Les six stratégies

1. **range-breakout-v1** : range des 20 bougies antérieures, volume de déclenchement ≥1,2 fois la moyenne, deux clôtures au-delà du range. Stop opposé. Le nouveau parcours exige également la confirmation supérieure.
2. **breakout-retest-v1** : cassure passée avec volume, maintien au-delà du niveau, puis contact et rejet sur une bougie ultérieure. Tolérance de 0,15 ATR; stop au-delà du retest avec marge de 0,1 ATR.
3. **trend-pullback-v1** : EMA20/50 orientées, ADX ≥20, retour puis franchissement/rejet de l'EMA20 et filtre RSI. Stop au-delà du dernier extrême de cinq bougies, avec marge ATR.
4. **bollinger-reversion-v1** : ADX <25, excursion hors des bandes suivie d'une réintégration clôturée et filtre RSI. Confirmation supérieure compatible avec un régime de range.
5. **smc-retest-v1** : structure BOS/CHOCH déjà confirmée, zone FVG ou order block déjà disponible, retest et rejet; une zone invalidée entre-temps est écartée. Définition SMC simplifiée, pas un moteur ICT complet.
6. **opening-range-v1** : fenêtre de session complète, première clôture franchissant le range et confirmation supérieure. La configuration distincte utilise M5/H1 et une fenêtre de 30 minutes à 09:30 New York. Le calendrier des séances et jours fériés reste à fournir/qualifier.

Les règles sont symétriques LONG/SHORT. Les périodes et seuils codés sont des hypothèses de recherche, sans promesse d'optimalité. Les cinq premières stratégies sont activées dans `configs/strategy-policy.json`; l'opening range est dans `configs/opening-range-policy.json`, car son calcul exige une unité de base plus courte que H1.

La priorité du fichier ne représente pas un classement de rentabilité. La politique est identifiée par SHA-256 : modifier ses paramètres invalide les anciennes attestations du nouveau parcours.

## Installation et commandes

Utiliser le Python de l'environnement du projet, depuis la racine du dépôt. Le client MoonX Python nécessite l'option MCP déjà déclarée par le projet :

```powershell
python -m pip install -e ".[mcp]"
python -m agentic_trading.autonomy.cli --help
python -m agentic_trading.autonomy.cli strategies
python -m agentic_trading.autonomy.cli --output state/autonomy-demo.json demo
```

`demo` utilise exclusivement une fixture synthétique de replay dans une base temporaire. Elle ne crée aucune qualification et ne démarre aucun worker. Les options générales (`--config`, `--policy`, `--database`, `--output`, `--now`, `--costs`) précèdent la sous-commande.

La configuration par défaut est `configs/multi-asset-paper.json` : priorités crypto existantes, HOOD, XAUUSD, XAGUSD, NAS100, et univers CMC. Les plafonds existants sont conservés. La base par défaut reste `TRADING_DATABASE_URL`, sinon `state/trading.sqlite`. **Conserver la base et le compte déjà utilisés pour retrouver leurs positions.**

## Collecte et raccordement des prix

```powershell
python -m agentic_trading.autonomy.cli --output state/autonomy-bundle.json collect --source hybrid --context state/operator-context.json
python -m agentic_trading.autonomy.cli --output state/autonomy-check.json check --bundle state/autonomy-bundle.json
python -m agentic_trading.autonomy.cli --output state/autonomy-scan.json scan --bundle state/autonomy-bundle.json
```

- `public` : crypto spot OKX puis repli Bybit pour l'unité de base. L'unité supérieure reste chez le même fournisseur. Jusqu'à 300 bougies par requête, bougies en cours exclues, cache et budget de requêtes. Les prix sont en USDT, avec une parité USD qui doit être qualifiée séparément. Le volume notionnel 24 h fourni sur H1 est un proxy calculé sur 24 bougies contiguës.
- `moonx` : uniquement `get_candles` via une session MCP avec écritures désactivées. Les classes métal/index/forex doivent être retournées comme marché forex/CFD; aucune substitution par un token homonyme. Les volumes nuls des CFD sont conservés.
- `hybrid` : crypto publique et actifs traditionnels MoonX. La connexion privée est lue depuis `MOONX_MCP_URL` ou, sur cette installation Codex, depuis l'entrée locale `mcp_servers.moonx.url` du fichier privé de configuration. L'URL n'est ni copiée dans Git ni écrite dans les rapports. Sur un autre hôte, fournir sa propre configuration privée.
- `file` : le contexte doit contenir `external_data`, un bundle de bougies et métadonnées rafraîchi atomiquement par votre fournisseur. Ce parcours permet notamment de raccorder HOOD avec un véritable flux d'action. Une série de prix portant seulement le ticker HOOD ne suffit pas à établir l'identité NASDAQ.

Le bundle comprend `markets` (unité de base), `higher_markets`, `monitor_markets` (M1 pour les positions), `market_metadata`, `instruments`, `asset_identities`, `liquidity`, `macro`, `validation`. Les horodatages de bougies sont des **clôtures UTC**, pas des ouvertures. Le rééchantillonnage fourni conserve uniquement les agrégats complets et signale les fenêtres incomplètes. Des séances à ancrage particulier doivent être normalisées explicitement par le collecteur; aucun remplissage fictif n'est fait.

`check` renvoie par défaut zéro si l'inspection a abouti, même avec des actifs `NOT_READY`. Pour une condition de lancement automatisée, employer `check --bundle ... --require-ready` : le code de sortie est **3** si les entrées demandées ne sont pas qualifiées. Le JSON contient `all_requested_inputs_qualified`. Avec un snapshot CMC, tous ses membres et les priorités sont examinés; sans snapshot actuel, la couverture complète n'est pas revendiquée.

`market_metadata[symbol]` contient `source,basis,base_interval,higher_interval,monitor_interval,fetched_at`. Les contrats et identités fournis par la collecte restent non qualifiés, sauf configuration opérateur indépendante. `check` décrit les données et preuves manquantes; il n'ouvre aucune position.

## Contexte opérateur et liquidité

`state/operator-context.json`, conservé hors Git, contient les spécifications réellement vérifiées (`instruments`), le contexte macro point-in-time, les attestations, les identités et les quotes nécessaires. Son absence permet la collecte et l'analyse, avec refus explicite des entrées non qualifiées.

Une quote doit contenir `source,asof,bid,ask,quote_currency`. Le spread observé doit être couvert par le modèle de coûts; il n'est pas artificiellement ramené à une valeur inférieure. En crypto, profondeur et volume notionnel restent exigés. USDT exige `usd_parity_verified=true` par une source qualifiée. Pour les CFD et actions, une quote exécutable vérifiée (`executable_quote=true`) remplace l'hypothèse inappropriée d'un carnet crypto centralisé; aucun volume de marché n'est inventé.

La quote d'entrée ne doit pas dépasser deux minutes d'âge. Une entrée PAPER qualifiée prend son mid observé, arrondi de façon adverse au tick, puis applique les coûts du simulateur. Une référence de bougie sans quote qualifiée sert uniquement au rapport d'un refus, pas à inventer un fill exécutable. Le replay conserve séparément son modèle d'ouverture suivante.

Les coûts peuvent être fournis par `--costs chemin.json` avec les mêmes champs que `Costs` : frais par côté, spread complet, slippage adverse, funding et swap. Ils s'appliquent au worker comme au replay. Ils restent des hypothèses à calibrer sur votre contrat réel.

Une attestation du nouveau parcours se place dans `validation[symbol].strategies[strategy_name]`. Outre les champs déjà exigés par `verify_evidence`, son corps signé lie `policy_hash` et `basis` aux valeurs exactes courantes. La clé HMAC reste privée; l'agent n'émet ni ne signe les preuves. Le replay et le walk-forward produisent des rapports de recherche à examiner, jamais une attestation `PAPER_VALIDATED` automatique.

La couverture inconnue du calendrier conserve le blackout. Les flux macro/RSS précédents restent disponibles; une liste RSS ou un calendrier tronqué ne suffit pas à certifier cette couverture.

## Worker et supervision persistante

Essai d'un seul cycle, puis lancement continu lorsque les entrées ont été qualifiées :

```powershell
python -m agentic_trading.autonomy.cli worker --source hybrid --context state/operator-context.json --once
python -m agentic_trading.autonomy.cli worker --source hybrid --context state/operator-context.json
python -m agentic_trading.autonomy.cli status
```

Le worker renouvelle les données, écrit le bundle atomiquement et décide une seule fois par combinaison de dernières bougies et politique. Un thread distinct rafraîchit les bougies de supervision des positions. Les lectures d'un même compte sont coordonnées par bail; le jeton est contrôlé dans la transaction d'entrée. Les anciennes commandes PAPER refusent également une nouvelle entrée sur un compte détenu par ce runtime. Les sorties protectrices restent autorisées.

Un redémarrage reprend les positions SQL et le journal de cycles. Une interruption au milieu d'un cycle PAPER permet un rejeu avec les mêmes identifiants de signal; cette propriété ne s'étend pas aux ordres distants. Ne pas supprimer la base, les positions, les limites consommées ou le journal pour recommencer.

Une lacune de supervision exige une revue des résultats simulés et éventuellement un replay des données manquantes. Après cette revue opérateur :

```powershell
python -m agentic_trading.autonomy.cli review-paper-gap --symbol BTC --reason "Historique manquant examine et resultats simules rapproches" --operator-confirm
```

Cette commande journalise la revue; elle ne reconstruit pas les fills manquants et ne supprime aucune limite de risque. Une lacune toujours présente déclenche un nouveau blocage. Les arrêts SIGINT/SIGTERM relâchent le bail; une panne brutale laisse le bail expirer. Les incidents sont enregistrés dans le journal et l'outbox existants. L'envoi d'e-mail reste à assurer par le worker de notification existant et un SMTP configuré.

Un incident répété conserve son état de santé sans recréer la même notification à chaque passage; une récupération est journalisée séparément. L'état figure dans `status`. Une erreur du contexte administratif bloque les entrées, tandis que le moniteur peut encore lire les bougies publiques/MCP des positions déjà connues.

La supervision M1 est une simulation OHLC, avec priorité conservative au stop si stop et objectif apparaissent dans la même bougie. Elle n'est pas une exécution en temps réel ni un stop natif. Le poste ou serveur doit rester actif, avec réseau et stockage persistants. Aucun service ou tâche planifiée n'est installé automatiquement par la mise à jour. Le modèle systemd fourni est un point de déploiement à adapter et tester sur l'hôte choisi.

## Replay et sélection walk-forward

```powershell
python -m agentic_trading.autonomy.cli --output state/replay.json replay --bundle state/historical-bundle.json
python -m agentic_trading.autonomy.cli --output state/forward.json walk-forward --bundle state/historical-bundle.json --candidates examples/autonomy-policy-candidates.json --train-sessions 300 --test-sessions 60
```

Les sessions sont les timestamps de clôture distincts, pas nécessairement des jours. Le replay conserve un seul budget partagé, la précision du contrat, les coûts, le financement et la priorité au stop. Le signal n'utilise que les clôtures connues; l'entrée simulée utilise l'ouverture de la bougie suivante. Seule cette ouverture est consultée à cet instant, pas son high/low/close. Les positions restantes sont valorisées et clôturées à la fin de la fenêtre.

Si l'univers est `cmc_top100`, le dataset doit contenir `historical_universe=[{asof,available_at,symbols},...]` avec compositions connues à l'époque. Leur absence bloque les entrées historiques au lieu d'appliquer le Top 100 actuel au passé. Pour étudier une watchlist fixe explicitement choisie, employer une configuration `universe=static` et annoncer ce périmètre.

Le replay de recherche suppose les filtres macro et de liquidité favorables, faute d'historique de ces données. Cette hypothèse apparaît dans le rapport et interdit d'en déduire une qualification d'exécution réelle. Les contrats fournis doivent quand même être vérifiés. Les fichiers de démonstration sont synthétiques et leurs résultats ne sont pas des performances de marché.

Le walk-forward évalue au plus dix politiques et cinquante folds. Les politiques doivent partager les mêmes unités. Il sélectionne uniquement sur la période d'entraînement, avec nombre minimal de trades et résultat net positif, puis évalue sur une période ultérieure séparée par embargo. Sans éléments suffisants, il s'abstient. Chaque fold possède un capital initial indépendant; les résultats ne sont pas annoncés comme une courbe de portefeuille continue. Les outils précédents de purge, CPCV, holdout et bootstrap complètent cette recherche.

## Limites de qualification

Les tests logiciels et la collecte observée sont consignés dans `docs/AUTONOMY_VERIFICATION.md`. Ils ne prouvent pas une rentabilité, un fonctionnement continu en production ou plusieurs mois de forward test. L'activation réelle continue d'exiger les qualifications et approbations du parcours `live-*`; le worker autonome ne l'appelle jamais.

Les spécifications de contrats, quotes exécutables, calendriers complets, historiques point-in-time et preuves financières doivent être fournis et vérifiés sur votre environnement. HOOD exige son flux d'action. La concurrence est qualifiée ici sur SQLite, pas PostgreSQL. Les coupures réseau/serveur et les gaps peuvent rendre des protections simulées incomplètes; les entrées sont alors bloquées et l'incident reste visible.
