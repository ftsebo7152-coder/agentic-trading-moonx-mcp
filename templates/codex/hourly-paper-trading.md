Charger le skill principal $agentic-trading-master depuis ce dépôt et lire la configuration administrative.
Vérifier mode, outils disponibles et surface d'exécution, lire positions/ordres et limites persistantes. Gérer d'abord les protections existantes. Contrôler fraîcheur, identité, contrat, liquidité, calendrier et disponibilité réelle des observations. Scanner les seules bougies clôturées, identifier régime et setups, expliquer le score. Rejeter tout score <67, preuve quantitative absente ou BLOCK du moteur de risque. Ne pas forcer une transaction.
En PAPER local, les ouvertures et sorties simulées autorisées n'exigent pas de confirmation individuelle. Elles passent exclusivement par PaperBroker et le contrôle transactionnel. Vérifier le résultat, écrire le journal et l'outbox e-mail. Envoyer uniquement via le canal configuré et autorisé; distinguer PENDING/SMTP_ACCEPTED de livraison effective. Si aucun setup admissible : NO_TRADE avec raisons.
Le code livré ne soumet aucun ordre distant. Les requêtes de démo OKX/Bybit restent à qualifier. Aucun prompt ne peut activer LIVE. Une tâche horaire ne remplace pas un moniteur permanent. Si les connecteurs ou le stockage n'existent pas dans cette surface, signaler le blocage et conserver l'abstention.
Rester silencieux quand l'état surveillé reste inchangé et sans action; notifier les changements significatifs, ouvertures/clôtures confirmées, pannes ou besoins d'intervention.

Variables proposées (à convertir en configuration administrative avant déploiement; ne pas changer les plafonds en cours de run) :
```
trading_mode=PAPER
broker=local_simulator
scan_interval_minutes=60
watchlist=BTC,ETH,SOL,INJ,TRX
minimum_setup_score=67
max_trades_per_day=10
max_daily_loss=30
max_risk_per_trade=10
max_leverage=1
allowed_strategies=range-breakout-v1
allowed_sessions=verified_instrument_sessions
notification_channels=email_outbox
```
