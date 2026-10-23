# Audit des sources - 23 octobre 2026

Les deux dépôts ont été clonés en lecture, sans modification de leurs branches distantes. L'inventaire statique couvre **121 fichiers / 13 170 lignes Python** dans Day Trader FR et **160 fichiers / 13 588 lignes JS/Python** dans le dépôt TradingView, tests inclus. `source-inventory.json` contient les chemins, tailles, SHA-256 et fonctions Python. La revue ciblée a porté sur les moteurs de risque, validation de ticket, exécution, sessions, blackout, scoring et fournisseurs. Cet inventaire et ces tests ne constituent pas une certification formelle exhaustive de chaque ligne.

| Composant | Day Trader FR constaté | Dépôt personnel constaté | Décision |
|---|---|---|---|
| Technique | `scan.py` : univers Nasdaq, RSI, cassures et ORB en bougies clôturées | OHLCV, indicateurs et lecture du graphique/CDP | Nouveau moteur multiactifs autonome; outils sources conservés |
| Fondamentale | RSS, SEC, résultats et déclarations Congrès | FRED, Finnhub, CryptoPanic, RSS, contextes BTC | Conserver les lecteurs; ajouter contrat point-in-time et couverture inconnue bloquante |
| Macro | Calendrier NYSE 2026/2027 et news | `blackout.js`, `scoring.js`, fournisseurs | Réécriture du gate; pas de confiance artificiellement augmentée quand les données manquent |
| Risque | `check.py` valide le ticket exact; cash, stop, concentration, daily loss | `session.js` sizing/validation/guard | Risk engine unique en Decimal, coûts et contrats; pas d'import des valeurs par défaut historiques |
| Simulation | `timemachine.py` bootstrap 10 000 trajectoires et replay historique | Replay TradingView interactif | Conserver originaux; ajouter backtest indépendant, MC de résultats et walk-forward |
| MCP/exécution | `ticket.py` prépare mais ne contacte pas le courtier | CDP via sélecteurs du DOM, détection paper/live | Archiver et rendre optionnel; adaptateur MoonX lecture et préparation séparés |
| Journal | Plusieurs fichiers JSON locaux par skill | JSON/JSONL de session et journal | Transactions SQL et outbox centrale |

## Les onze modules conservés

| Module | Implémentation réelle et limites | Nouveau point d'entrée |
|---|---|---|
| trader-scanner | 1 083 lignes; Yahoo gratuit non officiel, marché US, ORB 5 minutes et grille horaire | `trading-market-scanner`; archive disponible |
| trader-news | 546 lignes; RSS, SEC, mouvements, déduplication; User-Agent SEC requis | `trading-fundamental-analysis` |
| trader-entry | 960 lignes; confirmation de clôture, watchlist, horloge simulée | `RangeBreakout` causal; surveillances sources conservées |
| trader-exit | 735 lignes; plan long, ATR/range, sortie temporelle | Simulateur LONG/SHORT et TP multiples |
| trader-timemachine | 956 lignes; bootstrap/replay et seed, pas tous les futurs possibles | MC/validation nouveaux + original |
| trader-budget | 881 lignes; taille actions, cash, brackets | `size_position` multiactifs avec contrat |
| trader-risk | 819 lignes; format, fraîcheur, limites, stop, empreinte ticket | `IndependentRiskEngine` |
| trader-broker | 725 lignes; oui explicite par ticket; aucune connexion dans le script | Préparation distante seulement; aucun autre courtier intégré au nouveau runtime |
| trader-alerts | 787 lignes; prix et alertes locales, pas une protection au courtier | Moniteur PAPER + outbox |
| trader-analyst | 548 lignes; faits SEC, séries, variation et fraîcheur | Recherche actions optionnelle |
| trader-pelosi | 566 lignes; index et déclarations publiques, PDF via pdftotext | Recherche optionnelle, exclue du signal crypto |

## Faiblesses observables et réponses

- Le code de session TradingView écrit un état JSON local; il n'offre pas de coordination SQL entre workers cloud. Le nouveau moteur ne réutilise pas ce stockage.
- Le validateur de plan de `session.js` utilise des distances absolues; une direction doit aussi être contrôlée. Les nouveaux modèles rejettent un stop ou TP du mauvais côté.
- Le sizing TradingView utilise `Number` et le normaliseur de quantité BTC arrondit au pas le plus proche (`0.000781` devient `0.0008` dans son test). Le nouveau sizing arrondit vers le bas et réserve les coûts.
- Le scoring fondamental historique utilise des heuristiques de mots-clés et une confiance initiale même sans données. Le nouveau contexte expose les données manquantes et ne produit pas de probabilité.
- Les calendriers absents ou non couverts ne doivent pas être assimilés à l'absence de news. Le nouveau gate bloque les nouvelles entrées en ce cas.
- Les sélecteurs CDP sont dépendants de l'interface et un clic n'est pas une preuve de fill. Le connecteur Desktop reste optionnel et n'est pas utilisé pour le cloud.
- Day Trader FR est orienté actions US longues : ses paramètres de quantité, calendriers et frais ne sont pas transposés artificiellement aux CFD/perpétuels.

## Tests réellement exécutés

Day Trader FR : **318/318**, après redirection des temporaires Windows dans le workspace. TradingView : **51/51 tests unitaires**, après `npm ci --ignore-scripts` depuis le lockfile. Aucun test remote, CDP e2e ou ordre de courtage n'a été lancé. Les résultats sont dans `TEST_RESULTS.md` et les journaux de livraison.
