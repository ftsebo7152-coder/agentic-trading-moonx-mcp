---
name: trading-setup-scoring
description: "Décomposer un score de qualité sur 100 et appliquer le seuil de 67."
---

Utiliser SetupScoringEngine. 67/100 est une éligibilité au contrôle du risque, jamais 67 % de réussite. Un score élevé ne contourne aucun blocage.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli scan --config configs/paper.json --bundle examples/synthetic-market.json
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
