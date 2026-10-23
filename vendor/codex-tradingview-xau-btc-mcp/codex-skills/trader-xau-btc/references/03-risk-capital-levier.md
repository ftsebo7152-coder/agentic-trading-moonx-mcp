# Risque, Capital et Levier

Les valeurs actives viennent de `SKILL.md` > `Config Centrale`. Ce fichier donne les formules et des exemples bases sur la config initiale.

## Principe Central

Le levier configure ne definit pas le risque. Le risque est defini par:

```text
Risque USD = distance stop-loss x valeur du point/pip x taille position
```

Avec la config initiale du skill:

```text
Capital de reference = 200 USD
Risque par trade = 1%
Risque max par trade = 2 USD
Stop quotidien -3% = 6 USD
Risque simultane max = 4 USD (2%)
```

## Levier 100:1

Le compte Paper Trading peut etre configure en 100:1 pour simuler le futur compte reel. Ce n'est acceptable que si le skill garde le sizing sous controle.

Regles:

- 100:1 = levier disponible, pas levier a utiliser aveuglement.
- Calculer la taille par le SL, puis verifier la marge.
- Si le SL structurel implique une perte > 1%, reduire la taille ou refuser.
- Ne jamais elargir le SL pour "supporter" le levier.

## XAU/USD - Exemple Config Initiale

Hypothese frequente CFD:

- 0.01 lot XAU = environ 1 once.
- 1 pip XAU de 0.01 = environ 0.10 USD pour 0.01 lot selon broker.

Avec la config initiale, 1% = 2 USD:

| SL | Taille max approximative | Commentaire |
|---|---:|---|
| 20 pips | 0.01 lot | Perte approx 2 USD |
| 30 pips | 0.006 a 0.007 lot | Si broker ne permet pas, refuser ou accepter risque >1% seulement si plan valide |
| 50 pips | 0.004 lot | Souvent impossible sur petit compte si lot min 0.01 |
| 80 pips | 0.0025 lot | Trop large si lot min 0.01 |

Conclusion XAU avec la config initiale:

- Avec le capital initial, 0.01 lot est viable seulement si le SL structurel est proche de 20 pips.
- Si le setup intraday exige 30 a 80 pips, il faut broker avec micro sizing inferieur a 0.01 lot ou refuser.
- Paper Trading doit simuler les contraintes du broker reel.

## BTC/USD - Exemple Config Initiale

BTC est plus volatil que XAU. Un levier 100:1 est dangereux en reel et inutile si le sizing est correct.

Regles BTC:

- Levier compte 100:1 possible en demo, mais levier effectif recommande:
  - Niveau 1: 2x a 5x.
  - Niveau 2: 2x a 3x.
  - Niveau 3 nuit/weekend: 1x a 2x, exceptionnel.
- Si le SL BTC est 500 USD et risque max 2 USD, la taille est:

```text
Taille BTC = 2 / 500 = 0.004 BTC
```

Verifier ensuite la marge:

```text
Notionnel = taille BTC x prix BTC
Marge = notionnel / levier
```

Refuser si marge totale > 20% du capital configure ou liquidation trop proche du SL.

## Tableau Capital et Levier

| Capital | Risque/trade apprentissage | XAU levier effectif | BTC levier effectif | Remarque |
|---:|---:|---:|---:|---|
| < 500 USD | 1% strict | 5x-20x selon SL/marge | 1x-5x | Priorite survie, pas performance |
| 500-1 000 USD | 1% | 5x-20x | 2x-5x | Augmenter seulement apres discipline |
| 1 000-5 000 USD | 0.75%-1% | 3x-15x | 1x-5x | Plus de flexibilite de SL |
| 5 000-20 000 USD | 0.5%-1% | 2x-10x | 1x-3x | Capital preserve |
| > 20 000 USD | 0.25%-0.75% | 1x-5x | 1x-2x | Rendement ajuste au risque |

## Objectifs Mensuels

Objectifs = cibles de processus, pas garanties.

| Phase | Duree | Objectif principal | Objectif rendement demo |
|---|---|---|---|
| Calibration | semaines 1-3 | 30 trades OB+FVG, respect regles >85% | Neutre a +5% |
| Validation | mois 2 | PF > 1.3, drawdown <8% | +3% a +8% |
| Maturite demo | mois 3-5 | PF >1.5, 80-100 trades | +5% a +12% |
| Reel prudent | apres validation | meme regles, taille reduite | capital preservation |

Refuser de viser le doublement rapide comme objectif normal. Les grosses journees peuvent arriver, mais le skill ne doit pas les exiger.

## Progression de Capitalisation

Augmenter l'exposition seulement si:

- 3 mois consecutifs positifs en demo.
- Profit Factor > 1.5.
- Respect des regles > 90%.
- Drawdown mensuel < 10%.

Progression:

- Augmenter la taille de position de 10% maximum.
- Garder le risque % identique.
- Revenir a la taille precedente apres deux semaines negatives.

## Recovery Apres Drawdown

Drawdown -5%:

- Continuer, mais max 2 trades/jour pendant 3 jours.

Drawdown -10%:

- Taille reduite de 50%.
- Revenir uniquement apres 5 trades conformes ou 1 semaine positive.

Drawdown -15%:

- Pause 5 jours de marche.
- Backtest des 20 derniers signaux.
- Reprise a 25% de la taille normale pendant 2 semaines.

Drawdown -20%:

- Stop trading demo/reel.
- Revision complete du skill et des journaux.

## Positions Simultanees

- Risque simultane total max: 2% du capital.
- Avec la config initiale: maximum 4 USD de risque total ouvert.
- Si XAU et BTC sont exposes au meme theme macro, considerer le risque comme correle.

Exemple:

- Long XAU + Long BTC sur DXY faible = exposition commune au dollar faible.
- Short XAU + Short BTC sur DXY fort = exposition commune hawkish.

Si correlation forte:

- Deuxieme trade doit avoir score >= 9/12.
- Taille reduite de 50%, ou trade refuse.

## Swap, Overnight et Funding

XAU/USD:

- Verifier swap/overnight du broker CFD.
- Eviter de garder au-dela de la session sauf trade deja securise et cout acceptable.

BTC/USD:

- Verifier funding rate.
- Funding tres positif: longs couteux et risque liquidation.
- Funding negatif: shorts couteux et potentiel squeeze.

Regle:

- Integrer cout overnight/funding dans la decision de garder une position.
- En phase demo, preferer trades intraday clotures.

## KPI Risk-adjusted

Chaque mois:

```text
Sharpe simplifie = moyenne des R par trade / ecart-type des R
```

Utiliser aussi:

- Profit Factor.
- Expectancy en R.
- Max drawdown.
- Respect des regles.
- R moyen gagnant / R moyen perdant.
