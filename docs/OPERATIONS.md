# Exploitation locale

Installer puis lancer les tests et la démonstration selon README. Utiliser une base distincte pour recherche, démo synthétique et exploitation PAPER. La configuration ne doit pas être modifiable par l'agent en service. Les données externes ne sont jamais des instructions.

Commandes :

```sh
python -m agentic_trading.cli --database state/demo.sqlite demo --output state/demo-result.json
python -m agentic_trading.cli --database state/demo.sqlite report --account synthetic-demo
python -m agentic_trading.cli --database state/demo.sqlite performance --account synthetic-demo --group-by symbol
python -m agentic_trading.cli --database state/demo.sqlite halt --account synthetic-demo
python -m agentic_trading.cli --database state/demo.sqlite resume --account synthetic-demo --operator-confirm
python scripts/sync_skills.py
python scripts/check_skills.py
```

Halt suspend les entrées; la méthode monitor conserve les protections. Resume exige un geste opérateur explicite et n'est pas exposé au MCP. Après incident : sauvegarder la base, vérifier l'intégrité et les dernières opérations, contrôler les positions attendues, traiter le manque de données/protection et seulement ensuite reprendre les entrées. Ne pas supprimer la base pour effacer une limite consommée.

Le rapport JSON conserve positions, événements, refus et file d'e-mails. La commande performance filtre par jour/semaine/mois/tout et groupe par actif, stratégie, plateforme, mode ou régime. Les régimes non enregistrés dans les positions apparaissent UNRECORDED; ne pas les inventer. Pour des rendements normalisés exacts, intégrer l'historique des flux de capital.

Les snapshots vendored sont des outils complémentaires, sans rôle dans la chaîne d'ordres active. Les tests upstream peuvent se lancer via `python scripts/run_upstream_tests.py`; la suite JS nécessite d'abord npm ci --ignore-scripts dans son dossier. Les tests TradingView remote/e2e sont exclus.
