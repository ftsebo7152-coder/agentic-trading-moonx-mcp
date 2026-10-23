# PAPER isolé

`PaperBroker` ne connaît aucun client MCP/REST. Ses écritures vont uniquement à la base locale. Les modes BACKTEST et REPLAY utilisent également des comptes de simulation séparés. LIVE_READ_ONLY ne passe pas dans l'orchestrateur de simulation et LIVE_EXECUTION est refusé à la configuration.

Démo complète : `python -m agentic_trading.cli --database state/demo.sqlite demo --output state/demo-result.json`. Les prix sont synthétiques, aucune clé requise. Une ouverture et trois TP produisent quatre e-mails en attente. Réexécuter la commande sur la même base ne crée pas de doublon du signal déjà traité.

Le simulateur applique spread, slippage adverse, arrondi au tick, frais à l'entrée et sortie, financement proportionnel paramétrable et contraintes de marge/quantité. En cas de gap au stop, le prix d'ouverture défavorable sert de référence. Quand stop et TP sont dans la même bougie, le stop passe en premier, par prudence. Cette règle ne reconstitue pas l'ordre réel des ticks. L'impact et les exécutions partielles sur carnet ne sont pas encore modélisés.

Le scan normal exige des preuves quantitatives et des données fraîches. La commande demo ne contourne ces preuves que pour le scénario explicitement synthétique, dans un compte PAPER. Ce mécanisme n'autorise jamais un appel distant.
