# Matrice de compatibilité et preuve

Sources primaires : [MoonX MCP](https://moon-x.io/ai-agent/), [OKX Agent Trade Kit](https://www.okx.com/docs-v5/agent_en/), [OKX source](https://github.com/okx/agent-trade-kit), [Bybit MCP officiel](https://github.com/bybit-exchange/trading-mcp), [Bybit démo](https://bybit-exchange.github.io/docs/v5/demo), [Bybit ordre](https://bybit-exchange.github.io/docs/v5/order/create-order). Vérification le 23 octobre 2026.

| Capacité | MoonX connecté dans cette session | OKX | Bybit |
|---|---|---|---|
| Prix / OHLCV | Prix BTC et 100 bougies H1 reçus; 1–500 selon signature | Décrit dans MCP officiel; compte non connecté | Décrit dans MCP officiel; compte non connecté |
| Soldes / positions / ordres / historique | Outils déclarés, lectures privées non nécessaires à cette mission | Décrit par le fournisseur | Décrit par le fournisseur |
| LONG / SHORT | `open_futures_position`, `open_forex_position` déclarés, non appelés | Décrit, non essayé | Décrit, non essayé |
| Stop à l'ouverture | Paramètre en futures réguliers et Forex | Requête `attachAlgoOrds` préparée, non soumise | `stopLoss` dans requête préparée, non soumise |
| TP à l'ouverture | Un prix TP dans chaque signature | Un TP dans le constructeur livré | Un TP dans le constructeur livré |
| Trois TP natifs simultanés | **Non démontré**; ne pas remplacer trois niveaux par trois appels qui pourraient s'écraser | Non qualifié dans ce dépôt | Non qualifié dans ce dépôt |
| Fermeture partielle | Futures : `percentage` 1–100; Forex : signature de fermeture totale seulement | Décrit dans API; non essayé | Décrit dans API; non essayé |
| TP/SL partiels | `set_futures_tp_sl` expose fractions; coexistence de plusieurs niveaux non démontrée | À qualifier | À qualifier |
| Limites | Outils d'entrée limite déclarés; futures sans stop à l'entrée dans la signature | Documenté, non essayé | Documenté, non essayé |
| Démo | Ni recherchée comme plateforme de démo ni utilisée, selon complément PDF | Profil demo et en-tête officiel | Compte demo et `api-demo.bybit.com`; distinct du testnet |
| Levier | Futures paramétrable; Forex sans argument levier; valeurs exactes par contrat inconnues | Contrat/compte à vérifier | Contrat/compte à vérifier |
| Idempotence native | Aucun identifiant client dans signature d'ouverture MoonX observée | `clOrdId` dans préparation | `orderLinkId` dans préparation |
| Nuage | Auth/session du MCP connecté localement non transférée automatiquement | Processus MCP et secrets à déployer | Processus MCP et domaine/clef démo à vérifier |

35 déclarations sont conservées dans `moonx-tool-declarations.json`. Elles constituent une preuve des signatures exposées, pas des tests de transactions. Les fonctions de copie, dépôts et clear SL ne sont pas exposées par le nouveau runtime.

**Degen** est exclu : les signatures MoonX indiquent que SL/TP sont ignorés ou non supportés dans ce mode. Les futures limite sans protection atomique sont exclus des intentions exécutables.

La liquidation fournie par le moteur est une approximation isolée. Aucune formule générique ne remplace les règles réelles, le prix de liquidation du fournisseur, la maintenance, les frais et les paliers du contrat.
