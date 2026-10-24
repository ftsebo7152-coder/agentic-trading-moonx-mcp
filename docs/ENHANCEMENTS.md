# Extensions de recherche du 24 octobre 2026

Cette mise à jour ajoute des modules indépendants dans `agentic_trading.enhancements`. Les fichiers et fonctionnalités du moteur initial sont conservés. Les 29 skills restent disponibles. Les sources, licences examinées et limites de l'intégration figurent dans [SOURCE_INTEGRATION_AUDIT.md](SOURCE_INTEGRATION_AUDIT.md).

Les commandes ci-dessous se lancent depuis la racine du projet installé, avec son Python. Elles produisent du JSON. Les options générales `--database`, `--output` et `--now` se placent **avant** le nom de la sous-commande. `--now` fixe la date d'analyse, jamais la disponibilité réelle d'une donnée. Les fichiers `examples/research/` sont entièrement synthétiques.

## Collecte publique raccordée au moteur

```powershell
python -m agentic_trading.enhancements.cli --output state/research-bundle.json collect --config configs/paper.json --symbols BTC ETH SOL PUMP --derivatives --news --calendar
python -m agentic_trading.enhancements.cli --output state/research-cycle.json cycle --config configs/paper.json --bundle state/research-bundle.json
```

La base par défaut est identique au CLI initial : `TRADING_DATABASE_URL` si configurée, sinon `state/trading.sqlite`. Pour `cycle`, conserver exactement la base et le compte PAPER déjà utilisés : une base neuve ne contient pas vos positions existantes. Les exemples `journal` isolent volontairement les artefacts de recherche dans une autre base.

Le collecteur fournit les mêmes champs `markets`, `instruments`, `macro`, `liquidity`, `validation` et `asset_identities` que le CLI existant. Il ajoute `collection`, `research_evidence`, `derivatives` et, si demandé, `news`. Les observations techniques, de funding et RSS alimentent directement les revues de recherche. Elles restent neutres tant qu'aucune interprétation sourcée n'est fournie. Il n'y a pas d'appel LLM automatique.

- Bougies horaires spot USDT publiques OKX, puis repli Bybit si le premier fournisseur ne donne pas de bougies valides. Les bougies en cours sont exclues; l'horodatage normalisé est celui de leur clôture. Les niveaux de prix proviennent du fournisseur affiché, pas de MoonX.
- Carnet du même fournisseur que les bougies : spread, profondeur notionnelle dans une bande de 100 points de base. Le volume 24 h est un proxy somme(clôture × volume) sur 24 bougies contiguës, explicitement nommé. Il ne remplace pas un ticker 24 h officiel.
- Funding et open interest USD des swaps OKX si disponibles. Les timestamps de collecte sont conservés par champ, y compris en cache. Aucune série historique de liquidations ni donnée on-chain n'est inventée.
- RSS Federal Reserve, CoinDesk et Cointelegraph : titres, liens, publication et première collecte connue dans ce cache, dédoublonnage, fenêtre de 24 h. Un RSS silencieux n'est pas un calendrier économique vide. Des fournisseurs peuvent être inaccessibles.
- Calendrier USD public optionnel FXMacroData : contrôle des drapeaux de qualité et des heures d'annonce, événements utilisables comme veille. `coverage_until=null` et `calendar_coverage_known=false` restent explicites : une liste d'événements, même longue, ne garantit pas un horizon exhaustif. Le blackout du moteur n'est donc pas levé par cet ajout.
- Cache SQL, plafond de requêtes, timeout, taille maximale, origines HTTPS autorisées, redirections refusées, pause de cinq minutes sur HTTP 429. Aucun contournement des restrictions ou repli silencieux sur des valeurs périmées.

Pour demander la composition actuelle entière :

```powershell
python -m agentic_trading.enhancements.cli --output state/top100-bundle.json collect --config configs/paper.json --top100 --derivatives --news --budget 600
```

`--top100` exige un snapshot CMC actuel valide. Il conserve les priorités de la configuration en plus des actifs admissibles du Top 100. Les stablecoins et identités ambiguës restent exclus; un actif non coté chez les deux fournisseurs apparaît dans les échecs. HOOD reste l'action NASDAQ et n'est jamais remplacée par un token homonyme. HOOD, l'or, l'argent et NAS100 ne sont pas fournis par ce collecteur crypto. Un budget épuisé donne une couverture partielle annoncée, pas un succès complet.

**Les spécifications des instruments collectés restent non qualifiées** (`specs_verified=false`). L'identité CMC exprime l'actif recherché; le rapprochement effectif entre ticker du fournisseur, CMC et contrat MoonX reste à qualifier. USDT/USD n'est pas une parité garantie. Le collecteur ne crée aucune attestation quantitative. Ces données seules ne suffisent donc pas à ouvrir une position.

`cycle` réutilise le véritable orchestrateur existant : gestion protectrice, contrôles de risque et décisions d'abord, puis archivage des revues. Les dossiers de recherche n'augmentent pas le score d'entrée et ne peuvent pas transformer `BLOCK` en `PASS`. Le mode réel reste dans les commandes `live-*` séparées; ces extensions ne les appellent pas.

## Validation temporelle et robustesse

```powershell
python -m agentic_trading.enhancements.cli --output state/purged.json validate --input examples/research/samples.json --folds 4 --test-groups 2 --embargo-seconds 3600
python -m agentic_trading.enhancements.cli --output state/forward.json validate --input examples/research/samples.json --method walk-forward --train-sessions 6 --test-sessions 2 --expanding
python -m agentic_trading.enhancements.cli --output state/robustness.json robustness --input examples/research/trades.json
```

Chaque sample contient `id`, `symbol`, `source`, `decision_time`, `information_start`, `information_end`, `feature_available_at`, `label_available_at`. Toutes les dates portent un fuseau. Les caractéristiques doivent être connues à la décision, l'intervalle d'information doit contenir la décision et se terminer avant la disponibilité du label.

- Les actifs ayant la même heure de décision restent dans le même groupe. Un échantillon d'entraînement dont l'intervalle recoupe celui du test est purgé, bornes incluses.
- Embargo après les intervalles test; CPCV par combinaisons de groupes, budget maximal de 1 000 combinaisons. Le résultat marque les folds sans entraînement valide. La CPCV n'est pas une preuve forward et ne construit pas les chemins combinatoires de performance.
- Walk-forward glissant ou expansif, entraînement uniquement dans le passé, labels arrivés à maturité strictement avant la coupure et l'embargo. Les fonctions construisent les partitions; elles ne réentraînent aucun modèle. Normalisation, sélection des variables et hyperparamètres doivent être ajustés exclusivement dans le train de chaque fold.
- Robustesse sur PnL et notionnels alignés : coûts supplémentaires de 5/10/25/50 bps, bruit de coûts adverse reproductible, retrait du meilleur trade, intervalle bootstrap de la moyenne et block bootstrap des trajectoires. Le capital fourni est conservé dans tous les scénarios. Les hypothèses ne couvrent pas les chocs inédits; aucun seuil de rentabilité automatique n'est ajouté.

Pas de certification PBO, DSR ou stratégie gagnante. Les résultats ne constituent pas les preuves signées exigées par le moteur.

Pour consulter une composition historique déjà enregistrée :

```powershell
python -m agentic_trading.enhancements.cli --database state/research.sqlite --now 2026-10-24T12:00:00Z historical-universe
```

La date du snapshot **et** sa date d'enregistrement doivent précéder l'analyse. Le snapshot doit encore respecter l'âge maximal demandé. Sans historique contemporain enregistré : `INSUFFICIENT_DATA`. Cet utilitaire ne transforme pas le classement actuel en historique et ne recâble pas automatiquement un ancien backtest.

## Qualité d'exécution et portefeuille

```powershell
python -m agentic_trading.enhancements.cli costs --input examples/research/costs.json
python -m agentic_trading.enhancements.cli --now 2026-10-24T12:00:00Z book --input examples/research/book.json
python -m agentic_trading.enhancements.cli twap --input examples/research/twap.json
python -m agentic_trading.enhancements.cli --now 2026-10-24T12:00:00Z portfolio --input examples/research/portfolio.json
```

`costs` attend `fills` et `quotes`. Un fill : `symbol,time,side,price,quantity`, et éventuellement `fee_amount,fee_currency`. Une quote : `symbol,time,bid,ask`. Seule la dernière quote antérieure, suffisamment fraîche, est retenue. Le slippage signé au mid inclut déjà le spread; le spread n'est pas additionné deux fois. Les frais non convertibles restent inconnus. Moyenne, p95, couverture quotes et couverture frais sont rapportées; aucune modification automatique des limites de risque. Les frais USDT supposent une parité de devise à contrôler séparément.

`book` attend `book={source,asof,bids,asks}`, `side=buy|sell`, `quantity`. Les niveaux sont consommés du bon côté; VWAP, profondeur, coût adverse et reliquat non servi sont conservés. Carnets croisés, niveaux dupliqués, dates futures et périmées sont refusés. Il s'agit d'une consommation instantanée, sans priorité de file, latence ni liquidité cachée.

`twap` attend `quantity,step,slices,start,interval_seconds`. Les tranches respectent le pas et conservent la quantité totale. Le résultat est seulement un échéancier : aucune soumission ou modification d'ordre n'est faite.

`portfolio` attend des expositions USD signées par symbole et des rendements simples datés avec disponibilité et source. Les dates communes sont utilisées sans remplissage des trous. Il calcule corrélations, VaR et expected shortfall historiques sur **un intervalle des données fournies**, sans annualisation. Expositions fixes, historique limité et coûts exclus : il ne s'agit pas d'un risque futur garanti. `heat` complète le rapport avec le risque résiduel des positions ouvertes par groupe.

## Structures causales, thèses et recherche par desks

```powershell
python -m agentic_trading.enhancements.cli --now 2026-10-24T12:00:00Z review --input examples/research/evidence.json
python -m agentic_trading.enhancements.cli structure --input examples/research/structure.json
```

`structure` utilise des bougies clôturées, des swings confirmés à droite, FVG à trois bougies, sweeps, BOS/CHOCH et dernier chandelier opposé dans la fenêtre d'order block. Chaque événement porte `available_at`; un pivot ou order block n'est pas connu rétroactivement sur sa bougie d'origine. Ce sont des définitions de recherche explicites, pas de nouvelles stratégies autorisées. Une seule école est appliquée dans ce module.

Pour l'opening range : ajouter `--opening-range --timezone America/New_York --session-open 09:30 --minutes 30 --interval-seconds 60` à `structure`. Toutes les bougies de la fenêtre doivent exister et une bougie postérieure doit être disponible avant d'annoncer un breakout. Le calendrier des jours fériés n'est pas qualifié par ce calcul.

Une preuve de `review` contient `id,symbol,desk,source,source_url,published_at,available_at,fetched_at`, et une opinion optionnelle `stance=bullish|bearish|neutral`. `symbol=ALL` permet un contexte général. Les desks sont macro, fundamental, technical, onchain, funding, liquidation, execution, risk. Les opinions sont fournies, non générées ni assimilées à une probabilité. Les cas haussier/baissier, désaccords, données rejetées et desks sans preuve sont visibles. Un titre de news ne constitue jamais une instruction.

`thesis` ajoute `thesis={hypothesis,invalidation}` au même format symbol/evidence et archive la version. Une hypothèse sans critère d'invalidation est refusée.

## Journal de recherche, holdout, tâches et prédictions

```powershell
python -m agentic_trading.enhancements.cli --database state/research.sqlite journal
python -m agentic_trading.enhancements.cli --database state/research.sqlite journal --action holdout-register --input examples/research/holdout.json
python -m agentic_trading.enhancements.cli --database state/research.sqlite journal --action holdout-consume --input examples/research/holdout.json
```

La base SQLite est persistante. Les artefacts sont chaînés par SHA-256, avec transactions sérialisées et temps monotones. Le contrôle détecte une modification partielle de la chaîne; il ne remplace pas une signature, des sauvegardes externes ou les permissions système. Un administrateur capable de réécrire toute la base pourrait recalculer la chaîne.

Actions `journal` et JSON attendu avec `--input` :

| Action | Champs |
|---|---|
| append | `kind,payload` |
| enqueue | `kind=REVIEW|COLLECT|RECONCILIATION_REMINDER,payload,due` |
| claim | optionnels `lease_seconds,max_attempts` |
| complete | `id,lease_token` retournés par claim |
| holdout-register / holdout-consume | `name,dataset_hash,candidate_hash` |
| predict | `symbol,value,matures_at,source` |
| settle | `identity` de la prédiction, `actual` |

Le holdout est lié à un dataset et un candidat immuables et réservé une seule fois. Une réservation n'exécute pas d'évaluation. Les prédictions ne peuvent être réglées qu'à maturité, une seule fois, y compris en concurrence. Les hashes doivent correspondre à vos fichiers réels; les valeurs d'exemple n'attestent rien.

Les jobs sont dédoublonnés, réclamés sous bail, repris après expiration avec nouveau jeton et plafond de tentatives. Un ancien jeton ne peut pas terminer un nouveau bail. La file n'exécute aucun handler de courtage ni service en arrière-plan : le worker de collecte/revue de l'opérateur doit appeler les commandes autorisées puis `complete`. Les tâches épuisées demandent une inspection opérateur; ne pas recréer des identifiants pour ignorer un incident.

Les nouveaux artefacts/holdouts/baux concurrents sont qualifiés uniquement sur SQLite. Les opérations sensibles correspondantes refusent PostgreSQL dans cette extension jusqu'à validation d'un verrouillage équivalent. Le support PostgreSQL du moteur existant est conservé.

## Skill et vérification

Le skill maître renvoie à une référence autonome et à ces commandes. La copie `.claude` est synchronisée depuis `.agents`. `scripts/update_master_skill.py` met à jour uniquement ce skill installé, conserve une sauvegarde des fichiers remplacés et contrôle les chemins. Il ne lance ni worker ni planification.

```powershell
python scripts/sync_skills.py
python scripts/check_skills.py
python scripts/update_master_skill.py
python -m unittest discover -s tests -v
```

Les contrôles et l'essai public observé sont dans [ENHANCEMENTS_VERIFICATION.md](ENHANCEMENTS_VERIFICATION.md). Aucun test de rentabilité, ordre réel, serveur PostgreSQL, service cloud ni livraison e-mail n'est revendiqué par cette mise à jour.
