# Order Flow, Footprint, Heatmap et Volume Profile

Ce module est avance. L'utiliser uniquement si les donnees sont disponibles depuis TradingView, un connecteur MCP, une API publique autorisee, un outil externe type Bookmap/Exocharts/TensorCharts, ou une source crypto fiable. Ne jamais inventer le delta, le DOM, les liquidations ou une heatmap.

## Role du Module

L'analyse technique classique montre la structure. L'order flow montre comment le prix interagit avec la liquidite.

Utiliser ce module pour:

- confirmer un sweep;
- detecter absorption ou exhaustion;
- eviter les breakouts faibles;
- lire les zones de liquidation BTC;
- qualifier un retest OB/FVG;
- ameliorer les entrees et les stop-loss;
- eviter les trades contre un mur de liquidite evident.

Ne jamais utiliser l'order flow seul. Il doit confirmer une these deja construite par HTF, POI, session et risk management.

## Donnees et Outils

Donnees utiles:

- Volume Profile: POC, VAH, VAL, HVN, LVN.
- CVD: Cumulative Volume Delta.
- Delta par bougie.
- Footprint bid/ask.
- DOM: depth of market.
- Heatmap de liquidite.
- Liquidation heatmap BTC.
- Open Interest.
- Funding Rate.

Sources possibles:

- TradingView si indicateurs disponibles.
- Bookmap, Exocharts, TensorCharts, ATAS ou equivalents.
- Binance/Bybit public data pour BTC: order book, open interest, funding.
- Heatmap/liquidations via source autorisee.

## Volume Profile

Concepts:

- POC: prix le plus trade de la session ou du range.
- VAH: Value Area High.
- VAL: Value Area Low.
- HVN: High Volume Node, zone d'acceptation.
- LVN: Low Volume Node, zone de rejet ou passage rapide.

Lecture:

- Prix accepte au-dessus du POC: biais intraday plus haussier.
- Prix accepte sous le POC: biais intraday plus baissier.
- Rejet sur VAH en premium: short possible si MSS baissier.
- Rejet sur VAL en discount: long possible si MSS haussier.
- LVN casse avec impulsion: prix peut traverser vite vers le prochain HVN.

Regle:

- Un OB/FVG aligne avec VAL/VAH/POC est plus fort.
- Un TP place juste avant un HVN ou une grosse zone de liquidite est plus realiste.

## CVD et Delta

Delta:

- Delta positif: agressivite acheteuse.
- Delta negatif: agressivite vendeuse.

CVD:

- CVD monte pendant que le prix monte: continuation saine.
- CVD baisse pendant que le prix baisse: continuation saine.
- Prix fait un nouveau low mais CVD ne confirme pas: divergence haussiere potentielle.
- Prix fait un nouveau high mais CVD ne confirme pas: divergence baissiere potentielle.

Signaux utiles:

- Sweep bas + delta tres negatif + prix reintegre: vendeurs pieges, long possible apres MSS.
- Sweep haut + delta tres positif + prix reintegre: acheteurs pieges, short possible apres MSS.
- Breakout prix sans delta/volume: mefiance, risque faux breakout.

Refuser:

- Long si CVD chute fortement sans absorption visible.
- Short si CVD monte fortement sans absorption visible.

## Footprint

Objectif:

- Lire ce qui se passe dans chaque bougie: agressivite, absorption, exhaustion, imbalances.

Concepts:

- Bid x Ask: volumes executes au bid et a l'ask.
- Delta bougie: ask volume - bid volume.
- Imbalance: desequilibre fort entre bid et ask.
- Stacked imbalances: plusieurs niveaux consecutifs en desequilibre.
- Absorption: gros volume agressif absorbe sans continuation.
- Exhaustion: derniere poussee avec volume faible ou incapable de continuer.
- Poor high/poor low: high/low mal termine, souvent revisite.

Lecture long:

1. Prix sweep une liquidite basse.
2. Footprint montre vendeurs agressifs au low.
3. Le prix ne continue pas plus bas.
4. Absorption au bid.
5. Delta negatif extreme puis retournement.
6. MSS haussier.
7. Entree sur retest FVG/OB, SL sous le low absorbe.

Lecture short:

1. Prix sweep un high.
2. Acheteurs agressifs au sommet.
3. Le prix ne continue pas.
4. Absorption a l'ask.
5. Delta positif extreme puis retournement.
6. MSS baissier.
7. Entree sur retest FVG/OB, SL au-dessus du high absorbe.

Regles:

- Absorption + sweep + MSS = signal puissant.
- Stacked imbalances dans le sens du trade renforcent la continuation.
- Stacked imbalances contre le trade pres de l'entree = danger.
- Footprint M5 peut affiner une entree M15, mais ne doit pas transformer le systeme en scalping.

## Heatmap de Liquidite

Objectif:

- Voir ou les ordres limites et pools de liquidite attirent le prix.

Lecture:

- Mur de liquidite au-dessus: aimant potentiel, puis resistance si absorbe.
- Mur de liquidite en-dessous: aimant potentiel, puis support si absorbe.
- Liquidite qui disparait avant le prix: risque spoofing, ne pas se fier aveuglement.
- Prix tape une zone de liquidite puis rejette: sweep valide si reintegration.
- Prix tape une zone et la traverse avec volume: continuation possible vers la prochaine zone.

BTC:

- Les liquidation heatmaps sont tres utiles.
- Les clusters de liquidations longues sous le prix attirent les chasses baissieres.
- Les clusters de liquidations shorts au-dessus attirent les squeezes haussiers.

Regle BTC:

- Ne pas entrer long juste sous une grosse zone de liquidations longues non balayee.
- Ne pas entrer short juste sous une grosse zone de liquidations shorts non balayee.
- Apres balayage du cluster + reintegration + MSS, chercher reversal.

## DOM

DOM = carnet d'ordres visible.

Lire:

- Gros bid qui tient sous le prix: support potentiel.
- Gros ask qui tient au-dessus: resistance potentielle.
- Gros bid qui disparait: faux support possible.
- Gros ask qui disparait: breakout possible.

Attention:

- Les ordres limites peuvent etre annules.
- Le DOM est plus fiable quand il est confirme par execution reelle, delta et prix.

## Open Interest et Funding BTC

Open Interest:

- Prix monte + OI monte: nouveaux longs, tendance possible mais attention surlevier.
- Prix monte + OI baisse: short squeeze, mouvement peut s'essouffler.
- Prix baisse + OI monte: nouveaux shorts, tendance possible.
- Prix baisse + OI baisse: deleveraging, mouvement peut ralentir.

Funding:

- Tres positif: trop de longs, risque de liquidation long.
- Negatif: trop de shorts, risque de short squeeze.

Regle:

- Long BTC meilleur si funding neutre/legerement negatif et structure haussiere.
- Short BTC meilleur si funding tres positif + sweep high + MSS baissier.

## Integration dans les Strategies

OB + FVG Retest:

- Chercher absorption dans la zone OB/FVG.
- CVD doit cesser de pousser contre l'entree.
- Volume profile doit soutenir la zone.

Liquidity Sweep:

- Footprint/heatmap doivent montrer prise de liquidite.
- Delta extreme puis echec = piege.
- Entree seulement apres reintegration + MSS.

Daily Sweep:

- PDH/PDL sweep + cluster heatmap = fort.
- Si cluster non encore touche juste au-dessus/en-dessous, attendre le nettoyage.

OPR:

- Breakout OPR avec volume/delta dans le sens = continuation.
- Breakout OPR sans delta puis reintegration = faux breakout.

London Breakout XAU:

- Breakout range asiatique doit avoir volume et acceptation.
- Rejet footprint sur high/low asiatique = sweep reversal possible.

BTC Breakout:

- Exiger volume >= 150%, OI coherent, funding non extreme.
- Heatmap doit montrer route plausible vers la prochaine liquidite.

## Grille de Confirmation Avancee

Ajouter cette grille apres le score /12:

```text
Order Flow disponible: oui/non
Volume Profile: favorable / neutre / defavorable
CVD: confirme / diverge / defavorable
Delta bougie: confirme / neutre / defavorable
Footprint absorption: oui/non
Stacked imbalances: pour / contre / absent
Heatmap: liquidite balayee / aimant restant / danger
OI BTC: confirme / neutre / danger
Funding BTC: sain / neutre / dangereux
Conclusion flux: confirme / reduire taille / refuser
```

Decision:

- Si score technique valide et flux confirme: trade autorise selon risque.
- Si score technique valide mais flux neutre: taille normale ou reduite selon contexte.
- Si score technique valide mais flux defavorable: reduire taille de 50% ou refuser.
- Si flux non disponible: ne pas penaliser, mais ne pas pretendre qu'il confirme.

## Ajout Autonome - VWAP et Anchored VWAP

VWAP est un pont entre volume et prix.

Utiliser:

- VWAP session Londres/NY pour XAU.
- Anchored VWAP depuis daily open, news spike, swing high/low ou sweep.
- Prix au-dessus VWAP + retest = pression acheteuse.
- Prix sous VWAP + retest = pression vendeuse.

Confluence forte:

- OB/FVG + AVWAP + discount/premium + MSS.

## Ajout Autonome - Regime de Liquidite

Classer le marche avant de trader:

- Regime normal: spread stable, volume normal, ATR tradable.
- Regime thin: faible volume, spreads larges, meches erratiques; reduire ou no trade.
- Regime news: ATR extreme, delta violent, slippage; attendre stabilisation.
- Regime trend: volume confirme, pullbacks propres; privilegier continuation.
- Regime liquidation: BTC OI/funding extremes; privilegier sweeps et reversals confirmes.

Le regime de liquidite peut invalider une strategie meme si le pattern visuel est beau.
