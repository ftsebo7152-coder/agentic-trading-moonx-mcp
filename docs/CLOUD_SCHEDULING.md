# Planification et persistance

Le scanner se déclenche toutes les 60 minutes par défaut. Le moniteur est un composant distinct; son worker traite les données disponibles toutes les 15 secondes. Avec des bougies H1, cela reste une supervision en bougies H1, pas une protection en temps réel. Les marchés non crypto exigent leurs calendriers réels; les profils non vérifiés ne doivent pas recevoir d'entrées.

Entrée testable : `python -m agentic_trading.cli worker --config configs/paper.json --bundle examples/synthetic-market.json --once`. Sans --once, le worker tourne jusqu'au signal d'arrêt. Le bundle doit être alimenté atomiquement par un collecteur indépendant avec données, contrat, liquidité et calendrier frais. Le worker livré ne transforme pas les exemples statiques en flux live.

Le Dockerfile et deploy/agentic-trading.service sont des configurations de déploiement proposées, non exécutées dans cette livraison. Aucun compte cloud ni ordonnanceur n'a été activé. En service : monter configuration/attestations en lecture seule; laisser écriture uniquement sur état persistant; fournir les secrets hors dépôt; ajouter des sondes et alertes d'incident; sauvegarder la base.

SQLite est vérifié localement; utiliser un disque persistant avec un seul hôte. Pour plusieurs hôtes, installer `python -m pip install -e ".[cloud]"` et TRADING_DATABASE_URL=postgresql://... via secret. Le backend PostgreSQL utilise des transactions et verrous de compte, mais il n'a pas été testé contre un serveur. Cette validation est un préalable cloud, ainsi que les tests de panne et restauration.

Les templates Codex/Claude sont fournis comme artefacts. Ils n'installent ni skills ni connexions par magie. La disponibilité des outils, secrets, notifications, système de fichiers et processus persistants doit être contrôlée séparément dans chaque environnement. Le README distingue les tests locaux des capacités seulement documentées.

Si l'hôte ne peut pas superviser une position continuellement, utiliser un worker externe permanent; les protections réelles devraient être hébergées au courtier lorsqu'elles sont effectivement supportées. Une tâche horaire ne fournit jamais cette garantie.
