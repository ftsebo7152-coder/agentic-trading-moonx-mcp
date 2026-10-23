---
name: trading-notifications
description: "Consulter ou traiter la file d’e-mails des événements confirmés."
---

SMTP doit être configuré dans l’environnement sécurisé. SMTP_ACCEPTED signifie prise en charge, pas livraison. Une erreur laisse l’e-mail en attente; ne jamais annoncer un envoi sans acquittement.

Entrées : configuration administrative, watchlist, bougies clôturées, observations disponibles et base persistante, selon le module.
Sorties : JSON avec statut réellement confirmé et raisons des refus. Aucune donnée manquante ne doit être inventée.
Dépendances : Python >= 3.11; projet installé. MCP/SMTP/PostgreSQL sont optionnels et doivent être configurés séparément.
Limites : PAPER local opérationnel; envoi aux exchanges et LIVE désactivés dans cette version. Les permissions de l’hôte restent applicables.

Exemple depuis la racine du dépôt :
```sh
python -m agentic_trading.cli notify --limit 50
```

Vérification : `python -m unittest discover -s tests -v`. Lire les limites et commandes dans `docs/OPERATIONS.md` avant une tâche persistante.
