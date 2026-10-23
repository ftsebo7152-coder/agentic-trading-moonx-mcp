---
name: trader-xau-btc
description: "Skill de trading intraday semi-automatise dedie uniquement a XAU/USD et BTC/USD. Utiliser pour analyser XAU/USD, BTC/USD, l'or, le bitcoin, TradingView, Paper Trading, Daily Sweep, OPR, OB + FVG, Liquidity Sweep, Liquidity Sweep + Volume Zone, Fibonacci 61.8 + OB, London Breakout, structure de marche, stop-loss, sizing, levier, news macro, API news/fundamentals, DXY, US10Y, BTC funding/open interest, sessions Londres/New York, journal de trading, backtest, forward test, rentabilite demo, gestion du risque et validation d'un setup long ou short."
---

# Trader XAU/BTC

Skill intraday semi-automatise pour XAU/USD et BTC/USD uniquement.

Objectif: assister la decision de trading, filtrer les mauvais setups, calculer le risque, produire un plan executable en demo, puis en reel seulement apres validation humaine explicite.

Ne jamais promettre la rentabilite. Le skill cherche un processus robuste, mesurable et ameliorable.

## Config Centrale

Ces valeurs sont la source de verite du skill. Les references peuvent donner des exemples, mais elles doivent rester coherentes avec cette config.

```yaml
asset_scope:
  primary: [XAUUSD, BTCUSD]
style: day_trading_intraday
entry_timeframes: [M15]
confirmation_timeframes: [M5, M15]
bias_timeframes: [H1, H4, D1]
current_phase: calibration
capital_reference_usd: 200
risk_per_trade_pct: 1
max_daily_loss_pct: 3
max_weekly_loss_pct_learning: 6
max_weekly_loss_pct_mature: 10
max_trades_per_day: 4
optimal_trades_per_day: 2-3
max_simultaneous_risk_pct: 2
account_leverage_available: "100:1 paper simulation"
timezone: Europe/Paris
sessions:
  london: "08:00-10:30"
  new_york: "14:30-16:30"
```

Si le capital evolue, modifier d'abord `capital_reference_usd` ici, puis recalculer les exemples de sizing dans `references/03-risk-capital-levier.md`.

## Verrouillage de Phase

Le skill doit respecter la phase courante. Si l'utilisateur ne precise rien, utiliser `current_phase: calibration`.

| Phase | Strategies autorisees | Conditions pour passer a la phase suivante |
|---|---|---|
| calibration | OB + FVG Retest uniquement | 30 trades journalises, respect regles > 85%, revue sans violation critique |
| validation | OB + FVG Retest, Liquidity Sweep + Reversal | Profit Factor > 1.3, drawdown maitrise, au moins 50 trades propres |
| maturite | Toutes les strategies validees du skill | Profit Factor > 1.5, 80-100 trades, plusieurs mois demo disciplinés |

Regle stricte:

- Si `current_phase != maturite`, refuser Daily Sweep, OPR, London Breakout avance, Fibonacci 61.8 + OB, Liquidity Sweep + Volume Zone et toute strategie non encore debloquee.
- Si `current_phase == calibration`, ne proposer aucun trade hors OB + FVG Retest, meme si le setup semble attractif.
- Si l'utilisateur demande une strategie verrouillee, expliquer que le setup peut etre observe et journalise, mais pas execute.

## Regles Absolues

1. Refuser tout trade sans stop-loss defini avant l'entree.
2. Risque initial par trade: `risk_per_trade_pct` de la Config Centrale, sauf plan de progression valide par journal.
3. Capital de reference initial: `capital_reference_usd` de la Config Centrale, configure comme le futur reel.
4. Levier compte possible: 100:1 en Paper Trading, mais le levier effectif est controle par la taille de position, la distance du SL et la marge.
5. Mode reel: aucune execution sans confirmation humaine explicite.
6. Actifs autorises: XAU/USD et BTC/USD seulement.
7. Style: day trading intraday, pas scalping. Entrees M15, confirmation possible M5, biais H1/H4/D1.
8. Maximum 4 trades par jour, optimal 2 a 3 trades. Si deux pertes consecutives, un seul trade supplementaire autorise.
9. Stop quotidien: -3% du capital. Stop hebdomadaire: -6% en phase apprentissage ou -10% maximum en regime mature.
10. Aucun trade si une news haute importance rend le risque non maitrisable.
11. Avant tout briefing pre-session XAU/USD ou BTC/USD, appeler `codex_pre_session_json` si le MCP news/fundamentals est disponible.
12. Si `blackout.tradeAllowed` est false, refuser toute nouvelle entree.
13. Si une position approche TP1 sans l'atteindre puis montre une invalidation objective M5/M15, Codex doit proposer une gestion defensive avant TP1: alerte, fermeture partielle, fermeture totale, reduction du risque ou maintien si la structure reste valide. En mode reel, validation humaine explicite obligatoire.

## Ordre de Lecture Obligatoire

Lire les references selon la demande:

- Pour aller vite avant session, lire d'abord `references/00-quick-reference.md`.
- Toujours lire `references/03-risk-capital-levier.md` avant de proposer une entree.
- Pour tout briefing pre-session, lire `references/02-fondamental-macro-news.md` puis `references/04-sessions-timing.md`.
- Pour toute analyse graphique, lire `references/01-technique-structure.md`.
- Pour choisir un setup, lire `references/05-strategies-playbooks.md`.
- Pour revue, optimisation ou suivi demo, lire `references/06-journal-amelioration.md`.
- Pour interaction TradingView/Codex/MCP, lire `references/07-tradingview-mcp-workflow.md`.
- Pour lecture professionnelle du flux d'ordres, lire `references/08-orderflow-footprint-heatmap.md` si des donnees de volume, delta, footprint, heatmap, liquidation map, DOM, CVD ou Volume Profile sont disponibles.
- Pour ajouter ou evaluer une strategie intraday, lire `references/09-strategies-statistiques.md`.
- Pour utiliser les APIs news/macro/BTC, lire `references/10-mcp-news-fundamentals.md`.
- Pour le schema exact du contexte fondamental MCP, lire `tools/codex_pre_session_json.md`.

## Workflow Standard

### 1. Pre-session

1. Appeler `codex_pre_session_json asset=XAUUSD|BTCUSD session=london|new_york timezone=Europe/Paris` si le MCP news/fundamentals est connecte.
2. Si le MCP news n'est pas disponible, verifier manuellement le calendrier economique: Investing.com, ForexFactory, Financial Juice, InvestingLive.
3. Lire le biais hebdomadaire: ING Think, Fed, DXY, US10Y, geopolitiques, COT, ETF BTC.
4. Ne jamais inventer une news, un chiffre macro, un funding, un open interest ou une headline.
5. Si une source API est indisponible, reduire la confiance et ne pas compenser par une supposition.
6. Marquer les niveaux: PDH, PDL, PDC, daily open, asian range, OPR, swing highs/lows, EQH/EQL, OB, FVG, breaker, mitigation, premium/discount.
7. Lire le flux d'ordres si disponible: Volume Profile, delta, CVD, footprint, heatmap, liquidations, DOM.
8. Classer la session: XAU session autorisee ou interdite; BTC niveau 1, 2 ou 3.
9. Definir le biais: long, short ou neutre. Si contradiction forte, rester neutre.

### 2. Detection du Setup

Priorite d'apprentissage:

1. Semaines 1 a 3: OB + FVG Retest uniquement.
2. Ajouter Liquidity Sweep + Reversal seulement apres 30 trades OB + FVG et Profit Factor > 1.5.
3. Ajouter Fibonacci 61.8 + OB ensuite.
4. Ajouter London Breakout uniquement pour XAU/USD.
5. Ajouter OPR et Daily Sweep quand la lecture des niveaux journaliers est stable.
6. Ajouter les filtres order flow/footprint/heatmap seulement si les donnees sont disponibles et comprises; ne jamais inventer ces donnees.
7. Ajouter Liquidity Sweep + Volume Zone seulement quand les donnees de volume, Volume Profile, order book, delta ou CVD sont disponibles.

Avant de proposer une strategie, verifier le `Verrouillage de Phase`. Une strategie verrouillee peut etre analysee pour apprentissage, mais pas recommandee comme entree executable.

Un setup doit obtenir le score minimum adapte a la session:

- XAU/USD: 7/12 minimum en session autorisee, 8/12 pour news ou lundi matin.
- BTC niveau 1: 7/12.
- BTC niveau 2: 8/12.
- BTC niveau 3 nuit/weekend: 9/12 et taille reduite de 50%.

### 3. Plan de Trade

Chaque plan doit fournir:

```text
Actif:
Session:
Strategie:
Biais HTF:
Direction:
Zone d'entree:
Stop-loss:
Take-profit 1/2/3:
Distance SL:
Risque en USD et en %:
Taille de position:
Levier effectif:
Marge estimee:
R:R:
Score /12:
Confirmation order flow:
Contexte fondamental/news:
Blackout news:
Trade autorise: oui/non
Condition d'invalidation:
Raison du refus si non:
```

### 4. Gestion

- TP1: fermer 50%, deplacer le SL a break-even si le prix confirme.
- TP2: fermer 30%, verrouiller un gain partiel.
- TP3: laisser courir 20% si le contexte reste valide.
- Ne jamais elargir le SL.
- Sortir avant fin de session si le trade n'est pas resolu et que le contexte se degrade.

#### Gestion Active Avant TP1 - TP1 Missed Reversal

Cette regle est une regle de gestion de position, pas une strategie d'entree. Elle s'applique lorsqu'une position ouverte progresse fortement vers TP1 sans que TP1 soit execute, puis montre des signes objectifs d'invalidation.

Definition de la progression vers TP1:

Pour un long:

```text
progress_to_tp1 = (prix_actuel - prix_entree) / (TP1 - prix_entree)
```

Pour un short:

```text
progress_to_tp1 = (prix_entree - prix_actuel) / (prix_entree - TP1)
```

La regle devient active si:

- `progress_to_tp1 >= 0.80`;
- TP1 n'a pas ete touche ou execute;
- le prix montre ensuite des signaux contraires objectifs.

Signaux defensifs pour une position LONG:

1. Meche haute de rejet proche de TP1.
2. Cloture M5 ou M15 baissiere forte.
3. Perte du dernier higher low M5/M15.
4. MSS ou CHoCH baissier.
5. Retour sous la zone d'entree, sous VWAP, sous OPR mid ou sous un niveau structurel cle.
6. Volume, delta, CVD ou order flow defavorable si disponible.
7. DXY/US10Y repartent fortement contre XAU/USD si disponibles.
8. Funding/OI/market context devient defavorable pour BTC/USD si disponible.

Signaux defensifs pour une position SHORT:

1. Meche basse de rejet proche de TP1.
2. Cloture M5 ou M15 haussiere forte.
3. Perte du dernier lower high M5/M15.
4. MSS ou CHoCH haussier.
5. Retour au-dessus de la zone d'entree, au-dessus VWAP, au-dessus OPR mid ou au-dessus d'un niveau structurel cle.
6. Volume, delta, CVD ou order flow defavorable si disponible.
7. DXY/US10Y repartent contre la these short XAU/USD si disponibles.
8. Funding/OI/market context devient defavorable pour BTC/USD si disponible.

Actions recommandees:

- 0 a 1 signal defensif: conserver la position, aucune sortie anticipee.
- 2 signaux defensifs: alerte de prudence, surveiller activement.
- 3 signaux defensifs: proposer fermeture partielle de 25% a 50%.
- 4 signaux defensifs ou invalidation structurelle claire: proposer fermeture totale.
- Si le prix revient sous/au-dessus de l'entree et invalide totalement la these initiale, proposer fermeture totale ou reduction maximale du risque.
- En mode reel, aucune action ne doit etre executee sans validation humaine explicite.

Regles anti-erreur:

- Ne jamais fermer uniquement parce que le prix respire ou pullback legerement.
- Ne jamais deplacer le SL au hasard.
- Ne jamais elargir le SL.
- Ne jamais transformer cette regle en prise de profit emotionnelle.
- La sortie anticipee doit etre justifiee par des signaux objectifs et journalisee.
- Si les donnees order flow, DXY, US10Y, funding ou OI ne sont pas disponibles, ne pas les inventer; evaluer seulement les signaux visibles.

### 5. Journal et Amelioration

Apres chaque trade:

1. Journaliser la these, l'entree, le SL, les TP, le resultat en R, les emotions et le respect des regles.
2. Ajouter une capture avant/apres si disponible.
3. Mettre a jour les scores par strategie chaque semaine.
4. Ne passer au reel qu'apres plusieurs mois demo avec respect des regles, Profit Factor > 1.5, drawdown maitrise et au moins 80 a 100 trades journalises.
