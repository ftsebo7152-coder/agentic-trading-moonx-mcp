---
name: trading-backtest
description: "Rejouer chronologiquement une stratégie avec coûts et sorties simulées."
---

Lire docs/QUANT_VALIDATION.md. Séparer l’échantillon d’apprentissage et celui de test. Identifier les résultats synthétiques; ils ne prouvent aucune rentabilité.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli backtest --bundle examples/synthetic-market.json --symbol BTC
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
