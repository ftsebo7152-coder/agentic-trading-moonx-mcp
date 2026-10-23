---
name: trader-budget
description: "Dimensionner une quantité arrondie vers le bas selon le risque net et le contrat."
---

Utiliser size_position et economics; distinguer marge, notionnel, risque au stop, gap et liquidation approximative. Refuser les spécifications non vérifiées.
Fonction d’origine conservée dans vendor/day-trader-fr/trader-budget/. Sa logique actions américaines ne valide pas un contrat crypto/CFD. Le courtage externe historique est exclu du nouveau runtime.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli report --account local-paper
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
