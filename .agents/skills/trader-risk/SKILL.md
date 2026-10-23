---
name: trader-risk
description: "Contrôler stop, pertes, marge, levier, liquidité, coûts et exposition avant une entrée."
---

Utiliser IndependentRiskEngine. Les plafonds sont administratifs et ne doivent pas être changés pour faire passer un plan. Ne jamais élargir le stop.
Fonction d’origine conservée dans vendor/day-trader-fr/trader-risk/. Sa logique actions américaines ne valide pas un contrat crypto/CFD. Le courtage externe historique est exclu du nouveau runtime.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli report --account local-paper
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
