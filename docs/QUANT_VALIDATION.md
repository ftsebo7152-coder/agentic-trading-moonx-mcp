# Validation quantitative

Exemple exécuté : `python -m agentic_trading.cli backtest --bundle examples/synthetic-market.json --symbol BTC --output state/backtest.json`. Le replay inspecte les préfixes chronologiques, ouvre à la clôture de confirmation et traite seulement les bougies suivantes. Les positions encore ouvertes sont clôturées en fin d'échantillon et identifiées END_OF_SAMPLE; elles ne disparaissent pas des résultats.

Le module quantitative fournit performance, Wilson, IC bootstrap de moyenne, Monte Carlo par blocs avec seed 19, stress de coûts, Brier score et courbes de fiabilité, puis walk_forward qui sélectionne les paramètres sur l'apprentissage exclusivement. Les ratios Sharpe/Sortino sont au niveau trade et non annualisés; une annualisation exige une série temporelle de rendements de portefeuille.

La progression calculée est RESEARCH, BACKTESTED, FORWARD_TEST ou PAPER_VALIDATED. Elle exige OOS, espérance bootstrap positive, diversité de régimes, largeur d'IC et drawdown autorisés. Les seuils sont configurables; aucun nombre brut de trades ne prouve une rentabilité. LIVE_ELIGIBLE reste faux jusqu'à une qualification opérationnelle et administrative séparée.

Le flux normal vérifie une attestation HMAC opérateur liée à l'actif, à la stratégie, à une empreinte de rapport et à une période. TRADING_VALIDATION_HMAC_KEY appartient au service, pas à l'agent. Aucun signataire n'est exposé par les outils MCP. La gouvernance et la protection OS de cette clé restent des prérequis de déploiement.

Limites : exemple de marché synthétique, court historique MoonX reçu, aucune stratégie financièrement qualifiée; pas de dataset multi-actifs point-in-time ni de carnet historique; filtre macro et SMC non validés statistiquement; MC de PnL ne simule pas tous les prix futurs ni les chocs inconnus. La fonction walk_forward est testée avec un évaluateur déterministe; une étude de marché robuste reste à fournir.
