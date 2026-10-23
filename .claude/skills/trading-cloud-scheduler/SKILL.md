---
name: trading-cloud-scheduler
description: "Préparer ou exécuter un worker PAPER dans une infrastructure persistante."
---

Lire docs/CLOUD_SCHEDULING.md. Tester les connexions depuis la surface distante avant activation. Ne pas activer une tâche réelle ou un envoi externe simplement en installant ce skill.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli worker --config configs/paper.json --bundle examples/synthetic-market.json --once
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
