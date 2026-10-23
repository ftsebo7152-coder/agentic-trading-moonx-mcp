---
name: trading-execution
description: "Préparer les intentions MoonX ou démo OKX/Bybit et vérifier leurs limites effectives."
---

Lire docs/LIVE_TRADING_SAFETY.md et la matrice des connecteurs. Le runtime livré ne soumet aucun ordre distant. Ne pas appeler directement un outil de courtage en contournant ce blocage.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli report --account local-paper
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
