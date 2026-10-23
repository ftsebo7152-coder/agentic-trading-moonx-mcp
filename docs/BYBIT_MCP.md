# Bybit : démonstration distincte du testnet

Sources : [MCP officiel](https://github.com/bybit-exchange/trading-mcp), [service démo](https://bybit-exchange.github.io/docs/v5/demo), [création d'ordre](https://bybit-exchange.github.io/docs/v5/order/create-order). Le dépôt officiel a été identifié, mais sa compatibilité effective avec le domaine démo doit être vérifiée dans la version choisie. La documentation REST démo est distincte.

Le compte Demo Trading possède son propre identifiant et ses clés. Domaine REST : https://api-demo.bybit.com . Ne pas utiliser une clé testnet comme preuve de compte démo. Les flux privés démo et les flux publics du mainnet ont des rôles distincts; toutes les API ne sont pas proposées en démo.

`BybitBrokerAdapter.prepare_demo` prépare une requête V5 linear, orderLinkId, stopLoss et takeProfit, sans envoi. L'exemple suppose un mode one-way (positionIdx=0); ce mode doit être contrôlé, pas supposé en production. Levier, quantité, pas et état de protection doivent être réconciliés. La réponse d'acceptation d'ordre n'est pas une preuve de fill.

Pas de credentials ni de connexion authentifiée pendant la mission. La soumission et la gestion de multiples TP distants ne sont pas qualifiées. Le simulateur local est immédiatement utilisable sans compte Bybit.
