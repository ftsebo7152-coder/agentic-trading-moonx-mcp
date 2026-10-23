# Strategies Playbooks

Le skill ne doit pas chercher a tout trader. Il doit attendre les setups de haute qualite.

## Scoring a 12 Criteres

1 point par critere:

1. Biais D1/H4 aligne.
2. Prix dans premium/discount logique.
3. POI fort: OB, FVG, breaker, mitigation.
4. Liquidity sweep, inducement ou prise de liquidite claire.
5. MSS/CHoCH/BOS confirme sur H1/M15.
6. Session valide ou niveau BTC adapte.
7. News compatibles, pas de blackout.
8. DXY/US10Y/SPX ou on-chain en confluence.
9. Volume coherent avec le setup.
10. ATR dans zone tradable.
11. Spread/liquidite acceptables.
12. R:R >= 1:2 avec SL structurel.

Bonus de qualite non numerique:

- Footprint confirme: absorption, exhaustion ou stacked imbalance dans le sens du trade.
- Heatmap confirme: sweep d'un pool de liquidite puis retrait/absorption.
- Volume Profile confirme: reaction sur HVN/LVN/VAH/VAL/POC.
- CVD/delta confirme: divergence utile ou continuation saine.

Ces elements ne remplacent jamais le SL, le contexte HTF ni le score minimal. Ils servent a departager un setup fort d'un setup moyen.

Seuils:

- 7/12: minimum en session premium.
- 8/12: setup fort ou contexte moins favorable.
- 9/12: nuit/weekend BTC, news, second trade correle.

## Strategie 1 - OB + FVG Retest

Rang S. Strategie a maitriser en premier pendant 3 semaines.

Setup long:

1. Biais H4/H1 haussier ou reversal confirme.
2. Prix revient en discount.
3. Bullish OB + FVG dans la meme zone.
4. Retest propre de la zone.
5. Confirmation M15: bullish engulfing, pin bar, MSS haussier.
6. Entree sur retest ou cloture confirmation.
7. SL sous OB/FVG/swing low avec buffer.
8. TP1: dernier swing high ou liquidite proche.
9. TP2: PDH ou POI oppose.
10. TP3: extension si tendance.

Setup short inverse en premium sur bearish OB + FVG.

Validation apprentissage:

- 30 trades minimum.
- Profit Factor > 1.5.
- Respect regles > 85%.
- Sinon ne pas ajouter de nouvelle strategie.

## Strategie 2 - Liquidity Sweep + Reversal

Rang S, plus rentable mais exigeante.

Setup long:

1. Identifier EQL, PDL, asian low, session low ou swing low evident.
2. Prix sweep sous le niveau.
3. Reintegre rapidement.
4. MSS haussier M15/M5.
5. FVG ou OB cree par l'impulsion de retour.
6. Entree sur retest de FVG/OB.
7. SL sous l'extreme du sweep avec buffer.
8. TP vers EQH, PDH, high de session ou POI oppose.

Setup short inverse apres sweep high.

Refuser si:

- Sweep sans reintegration.
- Entree pendant spike de news.
- SL trop large pour 1%.
- Pas de displacement apres sweep.

## Strategie 2B - Liquidity Sweep + Volume Zone

Rang S/A selon qualite des donnees. Strategie ajoutee pour combiner prise de liquidite et zones de volume.

Conditions:

1. Liquidite evidente: PDH/PDL, Asian high/low, EQH/EQL, swing high/low, OPR high/low.
2. Sweep clair puis reintegration.
3. Zone de volume confirmee: POC, HVN/LVN, VAH/VAL, volume spike, footprint absorption, heatmap liquidity pool, order book imbalance ou CVD divergence.
4. MSS M15 ou M5 apres reintegration.
5. FVG/OB cree par displacement.
6. News blackout false.
7. R:R >= 1:2 et risque <= 1%.

Setup long:

1. Sweep sous un low evident.
2. Absorption ou rejet sur zone de volume.
3. Reclaim de la zone.
4. MSS haussier.
5. Entree sur retest FVG/OB ou reclaim.
6. SL sous extreme du sweep.
7. TP vers POC oppose, daily open, PDH, EQH ou high de session.

Setup short inverse apres sweep high.

Refuser si:

- aucune donnees de volume fiable;
- volume invente ou approximatif;
- sweep sans reintegration;
- news rouge en blackout;
- SL trop large;
- spread/ATR non maitrisable.

## Strategie 3 - Fibonacci 61.8 + OB

Rang A. Strategie de precision en tendance claire.

Conditions:

- D1/H4 fortement directionnels.
- Retracement dans la tendance.
- Zone 61.8% alignee avec OB/FVG.
- Premium/discount coherent.

Entree:

- Long en discount sur 61.8 + bullish OB.
- Short en premium sur 61.8 + bearish OB.
- Confirmation M15 obligatoire.

SL:

- Au-dela du swing qui invalide la tendance.
- Si SL trop large pour 1%, refuser.

## Strategie 4 - London Breakout XAU/USD

Rang A, reserve a XAU/USD.

Preparation:

- Marquer range asiatique 00h00-07h00.
- Marquer high, low, midpoint.
- Verifier DXY et news.

Breakout long:

1. Bougie M15 cloture au-dessus asian high.
2. Retest du high casse.
3. Confirmation M15.
4. SL sous retest ou sous midpoint/range selon structure.
5. TP base sur taille du range, PDH, niveau H1.

False breakout:

- Si prix casse high asiatique puis reintegre, chercher short seulement apres MSS baissier.
- SL au-dessus du spike.

## Strategie 5 - OPR

OPR = Opening Price Range.

XAU Londres:

- Construire OPR 08h00-08h15 ou 08h00-08h30.
- Marquer OPR high, low, mid.
- Aucun trade pendant formation.

OPR continuation:

1. Breakout OPR dans le sens H1/H4.
2. Retest OPR high/low.
3. OB/FVG ou wick rejection sur retest.
4. Entree dans le sens breakout.
5. SL de l'autre cote du retest ou sous/au-dessus OPR mid selon structure.

OPR sweep reversal:

1. Prix casse OPR high/low.
2. Reintegre le range.
3. MSS inverse.
4. Entree vers OPR mid puis cote oppose.

NY OPR:

- Si news 14h30, attendre 14h45 avant toute decision.
- Eviter d'anticiper le premier spike.

## Strategie 6 - Daily Sweep

Daily Sweep = sweep d'un niveau journalier majeur puis reversal ou continuation.

Niveaux:

- PDH.
- PDL.
- Daily open.
- PDC.
- High/low du jour.

Setup long:

1. Prix sweep PDL ou daily low.
2. Reintegre au-dessus.
3. Displacement haussier.
4. MSS haussier M15.
5. FVG/OB cree par l'impulsion.
6. Entree sur retest de la FVG/OB.
7. SL sous l'extreme du sweep.
8. TP vers daily open, PDC, PDH, EQH ou high de session.

Setup short:

1. Prix sweep PDH ou daily high.
2. Reintegre dessous.
3. MSS baissier.
4. Entree sur retest FVG/OB bearish.
5. SL au-dessus extreme du sweep.
6. TP vers daily open, PDC, PDL ou low de session.

Regle:

- Ne pas short avant que le prix atteigne une NWOG/FVG/aimant haut proche si structure locale haussiere.
- Ne pas long avant un aimant bas proche si structure locale baissiere.

## Strategie 7 - BTC Breakout avec Volume

Autorisee surtout BTC Niveau 1 ou 2.

Conditions:

- Consolidation H1/M15 lisible.
- Breakout cloture M15.
- Volume >= 150% moyenne 5 bougies.
- Funding pas extreme.
- OI coherent.

Entree preferree: retest du niveau casse.

## Strategie 8 - News Reaction

Pas d'entree avant news rouge.

Post-news:

1. Laisser spike.
2. Attendre M5/M15.
3. Si spike + rejet + reintegration: possible reversal.
4. Si breakout + retest + macro coherente: continuation.
5. Taille reduite si spread/ATR eleves.

## Filtres Specifiques

XAU:

- Ne pas shorter agressivement si banques centrales achetent massivement et structure D1 reste haussiere.
- Spread > 3 pips = no trade.
- Stop hunts frequents avant annonces US: attendre reintegration.

BTC:

- Ne pas shorter si ETF inflows nets positifs 5 jours et structure H4 haussiere, sauf sweep/reversal tres clair.
- Weekend: taille reduite, score 9/12, pas de FOMO.
- Funding tres positif: eviter longs tardifs.
