# Analyse Technique - XAU/USD et BTC/USD

## Timeframes

- D1: biais macro, niveaux journaliers, contexte de tendance.
- H4: structure institutionnelle, POI majeurs, premium/discount.
- H1: plan de session, niveaux d'execution, confirmation intermediaire.
- M15: entree principale intraday.
- M5: affinage uniquement apres setup M15 valide; ne pas basculer en scalping.

## Structure de Marche

Identifier:

- HH/HL: tendance haussiere.
- LH/LL: tendance baissiere.
- BOS: cassure dans le sens de la tendance.
- CHoCH: premier changement de caractere.
- MSS: Market Structure Shift, bascule micro plus precise que le CHoCH, surtout M15/M5.

Regle MSS:

- MSS haussier: sweep ou prise de liquidite basse, retour au-dessus du niveau, cassure du dernier lower high micro.
- MSS baissier: sweep haut, retour sous le niveau, cassure du dernier higher low micro.
- Un MSS seul ne suffit pas: il doit etre dans un POI, une session valide, et avec SL structurel.

## Premium et Discount

Tracer le range significatif H4/H1:

- 0% = low du range, 100% = high du range.
- 50% = equilibrium.
- Premium: au-dessus de 50%, zone favorable aux shorts.
- Discount: sous 50%, zone favorable aux longs.

Filtre:

- Eviter d'acheter en premium sauf continuation tres forte et retest propre.
- Eviter de vendre en discount sauf breakdown confirme.
- Les meilleurs longs naissent en discount + POI bullish.
- Les meilleurs shorts naissent en premium + POI bearish.

## Hierarchie des POI

Priorite:

1. Order Block valide.
2. FVG / imbalance.
3. Breaker Block.
4. Mitigation Block.
5. Niveau OHLC journalier: PDH, PDL, PDC, daily open.
6. Equal highs/lows, liquidity pools.
7. Support/resistance classique.
8. Fibonacci 61.8 / 50 / 78.6.

Plus une zone cumule des POI independants, plus elle est forte. Exemple: discount + bullish OB + FVG + PDL + wick rejection = zone de haute qualite.

## Order Blocks

Bullish OB:

- Derniere bougie baissiere avant impulsion haussiere qui casse une structure.
- Valide si le prix laisse une inefficience ou cree un BOS/MSS.

Bearish OB:

- Derniere bougie haussiere avant impulsion baissiere qui casse une structure.

Entree:

- Preferer le retest du corps de l'OB.
- SL au-dela de l'extreme de l'OB avec buffer.
- Refuser si le prix traverse l'OB sans reaction.

## Fair Value Gap

Bullish FVG:

- Espace entre le high de la bougie 1 et le low de la bougie 3 apres impulsion haussiere.

Bearish FVG:

- Espace entre le low de la bougie 1 et le high de la bougie 3 apres impulsion baissiere.

Utilisation:

- Ne pas entrer parce qu'une FVG existe.
- Attendre retour dans la FVG + confirmation M15/M5 + confluence POI.

## Breaker Blocks

Breaker bullish:

- Ancien bearish OB casse a la hausse, puis reteste comme support.

Breaker bearish:

- Ancien bullish OB casse a la baisse, puis reteste comme resistance.

Usage:

- Tres utile sur XAU/USD lors des retournements apres news ou stop hunt.
- Exiger MSS + retest + rejet clair.

## Mitigation Blocks

Zone non retestee apres impulsion forte.

Usage:

- Anticiper les retracements avant continuation.
- Utile sur BTC/USD quand le prix revient combler une zone institutionnelle avant reprise.
- Ne pas confondre mitigation et retournement: la mitigation prepare souvent la continuation.

## Wick Analysis

Lire les longues meches comme information structurelle:

- Longue meche basse: rejet vendeur, absorption ou sweep de liquidite basse.
- Longue meche haute: rejet acheteur, distribution ou sweep de liquidite haute.
- Meche seule sans reintegration et confirmation = signal faible.

Regle:

- Une meche devient niveau de reference si elle sweep un high/low evident puis reintegre.
- SL d'un trade reversal se place au-dela de l'extreme de la meche avec buffer.

## Inducement

Inducement = faux signal qui attire les traders retail avant le vrai mouvement.

Patterns:

- Breakout trop evident d'un range juste avant une kill zone.
- Retest "parfait" trop propre avant sweep inverse.
- Equal highs/lows visibles qui attirent les stops.
- Petite cassure sans volume puis retour violent.

Regle:

- Si un niveau est trop evident et proche d'une zone de liquidite, attendre le sweep/reintegration avant d'entrer.

## OHLC Journalier

Marquer chaque jour:

- PDH: Previous Day High.
- PDL: Previous Day Low.
- PDC: Previous Day Close.
- Daily Open.
- High/Low du jour en formation.

Utilisation:

- PDH/PDL sont des cibles de liquidite majeures.
- Daily Sweep: sweep PDH/PDL + reintegration + MSS + FVG/OB.
- Daily Open aide a lire le biais intraday: prix au-dessus = pression acheteuse, en-dessous = pression vendeuse, mais jamais seul.

## Gaps de Session

XAU/USD:

- Observer gap lundi ouverture et ecarts apres weekend.
- Lundi 08h00-09h00: taille reduite, attendre stabilisation.

BTC/USD:

- Surveiller CME Bitcoin futures gaps.
- Les gaps CME peuvent devenir des aimants de prix, mais ne justifient pas un trade seuls.

## Wyckoff

Accumulation:

- Range apres baisse, springs sous le range, absorption, breakout.

Distribution:

- Range apres hausse, upthrust au-dessus du range, rejet, breakdown.

Usage:

- Tres utile pour BTC/USD avant grands mouvements.
- Valider avec volume, sweep, MSS et contexte macro.

## DOM et Order Flow

Si donnees disponibles:

- Mur d'achat sous le prix + absorption = support potentiel.
- Mur de vente au-dessus + rejet = resistance potentielle.
- Open interest + funding aident a lire les liquidations BTC.

Sans outil avance:

- Utiliser volume, meches, vitesse du mouvement, reintegration et reaction sur POI.

