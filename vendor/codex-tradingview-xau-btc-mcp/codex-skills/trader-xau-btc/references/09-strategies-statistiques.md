# Strategies Intraday Statistiquement Testables

Une strategie n'est pas consideree "validee" parce qu'elle semble logique. Elle devient exploitable seulement apres backtest, forward test demo et journal.

## Conditions D'Admission

- Compatible day trading intraday M15/H1.
- SL structurel avant entree.
- R:R minimum 1:2.
- Conditions objectives, observables et journalisables.
- Au moins 20 exemples backtestes avant demo.
- Au moins 30 trades demo avant augmentation du risque.
- Profit Factor cible > 1.5.
- Respect des regles > 85%.

## Strategies Principales

1. OB + FVG Retest.
2. Liquidity Sweep + Reversal.
3. Liquidity Sweep + Volume Zone.
4. Daily Sweep.
5. OPR.
6. Fibonacci 61.8 + OB.
7. London Breakout XAU/USD.
8. Breakout Retest.
9. News Reaction post-stabilisation.
10. BTC Breakout avec volume.

## Liquidity Sweep + Volume Zone

Objectif: capter un faux mouvement institutionnel qui prend la liquidite puis rejette depuis une zone de volume importante.

Setup long:

1. Identifier une liquidite evidente: PDL, EQL, Asian low, swing low, low de session.
2. Le prix sweep le niveau et reintegre rapidement.
3. La zone du sweep correspond a une zone de volume: HVN/LVN, POC, volume spike, absorption footprint, heatmap liquidity pool ou order book imbalance.
4. MSS haussier M15 ou M5.
5. FVG/OB cree par le displacement de retour.
6. Entree sur retest FVG/OB ou reclaim de la zone de volume.
7. SL sous l'extreme du sweep.
8. TP vers midpoint, VWAP, POC oppose, daily open, PDH ou liquidite opposee.

Setup short inverse apres sweep high.

Refuser si:

- sweep sans reintegration;
- volume non disponible mais pretendu;
- zone de volume faible ou non prouvee;
- news rouge en blackout;
- SL trop large pour 1%;
- R:R < 1:2.

## Verification Statistique

Journaliser par strategie:

- actif;
- session;
- setup;
- score /12;
- R:R prevu;
- resultat en R;
- capture avant/apres;
- erreur d'execution;
- contexte fondamental;
- presence ou non de blackout.

Une strategie perd son statut actif si:

- Profit Factor < 1.2 sur 30 derniers trades;
- drawdown de strategie > 6%;
- violation des regles > 15%;
- performance degradee pendant deux semaines consecutives.
