# Journal et Auto-amelioration

## Journal de Trade

Remplir apres chaque trade:

```text
Date:
Actif: XAU/USD ou BTC/USD
Session:
Strategie:
Direction:
Biais D1/H4/H1:
Contexte macro:
News:
DXY/US10Y/SPX ou BTC funding/OI:
POI:
Premium/discount:
Entree:
SL:
TP1/TP2/TP3:
Gestion active avant TP1:
Progression max vers TP1:
TP1 touche: oui/non
TP1 missed reversal detecte: oui/non
Signaux defensifs detectes:
Action proposee:
Action validee par humain:
Risque USD/%:
Taille:
Levier effectif:
Score /12:
Capture avant:
Capture apres:
Resultat en R:
P&L:
Regles respectees:
Emotion avant/pendant/apres:
Memo audio disponible: oui/non
Erreur principale:
Lecon:
```

## Journal Audio

Pendant ou juste apres le trade, enregistrer une note vocale courte:

1. Ce que je vois.
2. Pourquoi j'entre ou pourquoi je refuse.
3. Ou est l'invalidation.
4. Ce que je ressens.

Le memo audio sert a detecter FOMO, revenge trade, surconfiance.

## Penalites

Violation majeure:

- Trade sans SL.
- SL elargi.
- Risque > limite.
- Trade hors session non autorisee.
- Revenge trade.

Penalite:

- Taille reduite de 50% pendant 5 jours de trading.
- Maximum 2 trades/jour.
- Relecture obligatoire des 5 derniers trades.

Violation critique:

- Suppression du SL.
- Depassement volontaire du stop quotidien.

Penalite:

- Pause 5 jours.
- Backtest de 20 setups avant reprise.

## Biais Cognitifs

| Biais | Danger | Antidote |
|---|---|---|
| Confirmation | Voir seulement ce qui confirme | Chercher le scenario inverse |
| Ancrage | Rester bloque sur un prix | Reevaluer structure actuelle |
| Aversion a la perte | Deplacer SL | SL verrouille avant entree |
| Surconfiance | Augmenter taille apres win | Taille fixe selon regles |
| Recence | Croire que le dernier trade predit le suivant | Score objectif /12 |
| FOMO | Entrer trop tard | Attendre retest ou passer |
| Biais du joueur | "Apres 3 pertes ca doit gagner" | Chaque setup est independant |

## Backtesting

Avant reel:

- Tester chaque strategie sur 3 mois.
- Minimum 20 trades par strategie.
- Validation minimale:
  - Win Rate > 50% ou expectancy positive.
  - Profit Factor > 1.5.
  - Drawdown < 10% en demo.
  - Respect regles > 85%.

Si une strategie echoue:

- La suspendre.
- Identifier le filtre manquant.
- Retester avec correction.

## Score de Confiance par Strategie

Chaque semaine:

```text
Score strategie = 40% Profit Factor + 25% respect regles + 20% drawdown inverse + 15% qualite execution
```

Usage:

- Score fort: strategie prioritaire.
- Score moyen: taille normale mais selectivite accrue.
- Score faible: suspendre ou reduire taille 50%.

## Bibliotheque de Setups

Creer des dossiers:

- XAU_OB_FVG_best.
- XAU_Liquidity_Sweep.
- XAU_OPR.
- XAU_Daily_Sweep.
- BTC_OB_FVG.
- BTC_Breakout.
- BTC_Sweep.
- Erreurs_a_ne_pas_repeter.

Chaque capture doit inclure:

- Avant entree.
- Apres entree.
- Sortie.
- Annotation du POI, SL, TP.

## Rapport Hebdomadaire

Chaque vendredi:

- Nombre de trades.
- Win rate.
- Profit Factor.
- Expectancy en R.
- Max drawdown.
- Respect des regles.
- Meilleure strategie.
- Pire strategie.
- Erreur dominante.
- Plan de la semaine suivante.

## Rapport Mensuel

Inclure:

- Performance %.
- Profit net.
- R moyen.
- Sharpe simplifie.
- Drawdown.
- Strategies par performance.
- Sessions par performance.
- XAU vs BTC.
- Decision: continuer, reduire, suspendre, augmenter seulement si conditions remplies.

## Rapport Trimestriel

Analyser:

- Session la plus rentable.
- Actif le plus rentable.
- Strategie au meilleur Profit Factor.
- Correlations qui marchent ou ne marchent plus.
- Ajustements majeurs du skill.
- Decision de passage reel seulement si demo stable.
