# Claude Code

Les skills de projet se trouvent dans `.claude/skills`. Ils sont générés depuis `.agents/skills`; exécuter `python scripts/sync_skills.py` puis `python scripts/check_skills.py` après modification. Invocation : `/agentic-trading-master` depuis une session démarrée à la racine du dépôt.

Source vérifiée : [documentation Claude Code skills](https://code.claude.com/docs/en/skills). Les sessions locales de projet et les sessions cloud n'ont pas toutes les mêmes règles de chargement. Les tâches cloud ne lisent pas le dossier personnel local; certains fils cloud de projet exigent les skills activés sur le compte. Vérifier le chargement et l'accès aux outils depuis la surface utilisée, pas uniquement depuis le terminal local.

Les copies ont été validées structurellement, pas chargées dans une instance Claude pendant cette livraison. Préparer un premier appel read-only et une démonstration locale avant toute planification. Le serveur MCP PAPER optionnel peut être enregistré comme processus stdio selon les réglages autorisés du client. Ne jamais activer le réel depuis un prompt de tâche.
