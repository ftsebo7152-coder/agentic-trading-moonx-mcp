# Voie reelle supervisee MoonX futures

LIVE_EXECUTION est maintenant un mode de configuration accepte. La soumission, la verification des protections, la reconciliation et la fermeture sont implementees dans src/agentic_trading/live.py, separement du simulateur. Le choix courant configs/paper.json reste PAPER. Aucun appel d'ordre reel, activation, cle ou compte reel n'a ete utilise pendant cette mise a jour. Les tests executent exclusivement un transport simule.

## Perimetre livre

MoonX MCP officiel exclusivement, futures crypto en marge isolee, stop-loss et un TP natifs envoyes avec l'ouverture. Une seule position a la fois, compte dedie sans autre position/ordre futures ou forex. Aucun mode degen. Le plan doit avoir un TP unique; un plan PAPER a trois objectifs n'est jamais transforme silencieusement. Les CFD/or/argent/Nasdaq (conversion en lots), les actions HOOD, OKX/Bybit et les sorties partielles distantes restent hors de cette voie. Aucun worker d'entrees reelles autonomes n'est active.

La configuration n'est plus rejetee au niveau Settings. L'execution exige toutefois enabled=true dans le fichier prive, TRADING_LIVE_ENABLED=YES, un schema qualifie, des specifications de contrat verifiees, un contexte frais, une preuve quantitative signee par l'operateur et l'approbation du plan exact. Un changement du plan ou de la configuration change son empreinte. Un prompt de skill ne vaut pas approbation d'une transaction.

## Configuration future, apres vos essais

1. Installer l'option MCP dans l'environnement du projet : `python -m pip install -e ".[mcp]"`.
2. Copier configs/live-moonx.example.json vers state/live-moonx.json, ignore par Git. Utiliser une base state/live.sqlite et un compte dedie. Renseigner l'identifiant du compte et MOONX_MCP_URL dans le .env prive; ne jamais publier ces valeurs.
3. Qualifier en lecture seule les chemins JSON du bloc schema sur la version effectivement lancee de MoonX. Les champs fournis sont des EXEMPLES de tests, pas une certification du schema MoonX. Il faut verifier compte, solde utilisable, listes de positions/ordres/TP-SL, historique, PnL net de frais, quantite et prix reels. schema_qualified reste false tant que cette verification n'a pas ete faite. Verifier aussi les tailles/paliers et protections du contrat et l'environnement reel/demo exact. Un solde vide ne prouve pas un compte demo.
4. Preparer state/live-packet.json avec plan (TradePlan), instrument (Instrument), context (asof, blackout=false, liquidity_ok=true) et evidence quantitative signee. Le plan contient entree, stop, quantite, levier et un TP de fraction 1; les limites restent dans config.settings.limits. Le contexte doit avoir moins de 60 secondes a l'envoi; les donnees du plan restent soumises au plafond de fraicheur. L'attestation est verifiee via TRADING_VALIDATION_HMAC_KEY; ni le skill ni le LLM ne doivent s'auto-signer une validation.

Commandes depuis la racine du depot (aucune commande d'envoi ci-dessous n'a ete executee pendant le developpement) :

```powershell
python -m agentic_trading.cli --database state/live.sqlite live-check --config state/live-moonx.json
python -m agentic_trading.cli --database state/live.sqlite live-prepare --config state/live-moonx.json --packet state/live-packet.json
```

live-check fait uniquement des lectures, verifie le compte et l'absence d'expositions et indique si le schema est qualifie. live-prepare affiche le plan, son risque estime et l'empreinte a faire approuver. Activer enabled=true et TRADING_LIVE_ENABLED=YES uniquement au moment de votre passage au reel, puis refaire prepare : la configuration fait partie de l'approbation.

```powershell
python -m agentic_trading.cli --database state/live.sqlite live-submit --config state/live-moonx.json --packet state/live-packet.json --approve EMPREINTE_APPROUVEE
python -m agentic_trading.cli --database state/live.sqlite live-reconcile --config state/live-moonx.json --attempt IDENTIFIANT_RETOURNE
```

L'operateur humain approuve l'empreinte apres examen entree/SL/TP/taille/risque. Ne jamais pre-remplir une autorisation depuis le resultat de prepare dans une tache autonome. prepare n'envoie rien. submit relit le compte, les positions/ordres et le prix; le risque est recalcule et un mouvement de prix excessif exige un nouveau plan. L'envoi est reserve en SQL avant l'appel pour serialiser les commandes concurrentes et interdire les doublons.

## Suivi et fermeture

OPEN_PROTECTED signifie qu'une position correspondante, le stop et le TP ont ete relus et que la quantite/risque observes respectent le plan. RECONCILIATION_REQUIRED signifie que l'execution ou les protections sont incertaines; toute nouvelle entree est bloquee. Refaire seulement live-reconcile et inspecter immediatement la plateforme. Ne jamais renvoyer l'ouverture ou effacer sa ligne SQL. Si le stop n'est pas confirme, faire verifier/fermer la position sans attendre; cette version ne pretend pas assurer un service de surveillance 24h/24.

live-reconcile fournit une close_approval pour une fermeture complete precise, que l'operateur doit approuver :

```powershell
python -m agentic_trading.cli --database state/live.sqlite live-close --config state/live-moonx.json --attempt IDENTIFIANT --approve EMPREINTE_FERMETURE_APPROUVEE
```

La fermeture reste permise quand le kill switch des entrees est actif. Elle n'est pas relancee automatiquement apres timeout. Une cloture n'est confirmee que par un historique correspondant a l'identifiant de position et un PnL net; sinon l'intent reste bloque. Une cloture confirmee alimente pertes journalieres/hebdomadaires et serie de pertes. Preserver la base et ses sauvegardes, n'utiliser aucun autre outil pour trader sur ce compte dedie. Les protections natives doivent fonctionner sans le processus local.

## Qualification restante

Les tests prouvent le comportement du code sur fixtures, pas l'execution chez MoonX. L'authentification du client SDK, le schema reel, les fills, frais, liquidation, protections et historique doivent etre qualifies sur l'environnement choisi avant financement/activation. Aucun succes de test ne garantit une performance ou un stop execute au prix exact. Ce travail de qualification sera necessaire au passage au reel; la voie d'envoi n'est plus a programmer pour le perimetre futures supervise decrit ici.
