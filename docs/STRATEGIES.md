# Stratégies

range-breakout-v1 : fenêtre par défaut 20 bougies historiques terminées. La bougie précédente clôture au-delà du haut/bas de cette fenêtre avec volume >= 1,2 fois sa moyenne; la dernière bougie clôture du même côté. Stop à l'autre extrême de la fenêtre. Targets à 2R/3R/4R, quantités 25/35/40 % dans le constructeur initial. Le score, la liquidité, le calendrier et les limites restent obligatoires. Cette définition est calculable et causale; elle n'a pas été qualifiée rentable.

Le moteur SMC expérimental calcule FVG trois bougies, BOS au-delà du range antérieur, sweeps avec réintégration, blocs selon bougie opposée avant cassure et premium/discount du range. Il expose execution_enabled=false. Les définitions ne revendiquent pas une interprétation universelle d'ICT.

Non implémentés dans le nouveau moteur : CHOCH, MSS, breaker/mitigation blocks, ORB de session et breakout/retest complet. Les playbooks et le scanner ORB actions existent dans les archives sources, sans intégration active aux contrats crypto/CFD. Multi-timeframe : horizons configurables prévus, mais la confirmation H4/H1/M15/M5 n'est pas fusionnée automatiquement; la composante de score correspondante vaut zéro quand absente.
