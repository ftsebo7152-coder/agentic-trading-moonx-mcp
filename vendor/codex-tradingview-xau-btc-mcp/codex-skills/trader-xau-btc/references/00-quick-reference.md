# Quick Reference Pre-session

Cette page sert de fiche rapide avant Londres ou New York. Elle ne remplace pas les fichiers detailles; elle evite seulement de perdre du temps pendant les 30 minutes de preparation.

## Config Active Par Defaut

| Parametre | Valeur |
|---|---|
| Actifs principaux | XAU/USD, BTC/USD |
| Style | Day trading intraday |
| Entree principale | M15 |
| Confirmation | M5/M15 |
| Biais | H1/H4/D1 |
| Phase par defaut | calibration |
| Capital reference | voir `SKILL.md` > Config Centrale |
| Risque/trade | voir `SKILL.md` > Config Centrale |
| Stop quotidien | voir `SKILL.md` > Config Centrale |
| Max trades/jour | voir `SKILL.md` > Config Centrale |

## Sessions Autorisees

| Session | Fenetre | Usage |
|---|---|---|
| Londres | 08:00-10:30 Europe/Paris | XAU prioritaire, OB/FVG, sweep, OPR apres phase debloquee |
| New York | 14:30-16:30 Europe/Paris | XAU et BTC, attention news US 14:30 |

## Phase Et Strategies

| Phase | Autorise |
|---|---|
| calibration | OB + FVG Retest uniquement |
| validation | OB + FVG Retest, Liquidity Sweep + Reversal |
| maturite | Toutes strategies validees: Daily Sweep, OPR, Fib 61.8 + OB, London Breakout, Liquidity Sweep + Volume Zone |

Si la phase ne permet pas la strategie, refuser l'entree executable et journaliser seulement pour apprentissage.

## Checklist Pre-session

1. Appeler `codex_pre_session_json` si le MCP news/fundamentals est disponible.
2. Verifier `blackout.tradeAllowed`.
3. Si blackout actif, refuser toute nouvelle entree.
4. Marquer PDH, PDL, PDC, daily open, Asian range, OPR, EQH/EQL.
5. Lire DXY, US10Y et contexte Fed pour XAU.
6. Lire funding, open interest, premium et headlines crypto pour BTC.
7. Verifier spread, ATR, session, phase, score.
8. Calculer SL, risque, taille, marge, R:R avant toute validation.

## Seuils De Decision

| Condition | Decision |
|---|---|
| Pas de SL | Refus immediat |
| R:R < 1:2 | Refus |
| Risque > config | Refus ou taille reduite |
| Score XAU < 7/12 | Refus |
| Score BTC niveau 1 < 7/12 | Refus |
| Score BTC niveau 2 < 8/12 | Refus |
| BTC nuit/weekend score < 9/12 | Refus |
| Spread trop eleve | Refus |
| News rouge en blackout | Refus |
| Deux pertes consecutives | Pause ou taille reduite selon plan |

## Blackout News

- News rouge standard: pas de nouvelle entree 30 min avant et 15 min apres.
- FOMC/Powell/NFP/CPI/PCE: prudence renforcée; attendre stabilisation et cloture M15.
- Si les sources API sont indisponibles, reduire la confiance et verifier manuellement Investing.com, ForexFactory, Financial Juice ou InvestingLive.

## Sortie Attendue

Chaque proposition doit finir par:

```text
Trade autorise: oui/non
Raison:
Phase:
Strategie autorisee par phase: oui/non
Blackout news:
Risque USD:
R:R:
Validation humaine requise:
```
