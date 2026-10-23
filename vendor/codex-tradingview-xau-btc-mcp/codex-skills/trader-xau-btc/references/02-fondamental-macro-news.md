# Fondamental, Macro et News

## Sources Obligatoires

### MCP News/Fundamentals Prioritaire

Si le serveur MCP `news-fundamentals` ou le module integre du depot `codex-tradingview-xau-btc-mcp` est disponible, l'appeler avant toute analyse pre-session:

```text
codex_pre_session_json asset=XAUUSD session=london timezone=Europe/Paris
codex_pre_session_json asset=XAUUSD session=new_york timezone=Europe/Paris
codex_pre_session_json asset=BTCUSD session=new_york timezone=Europe/Paris includeOrderBook=true
```

Regles:

1. Si `blackout.tradeAllowed` est false, refuser toute nouvelle entree.
2. Si `providerStatus` montre des sources indisponibles, reduire la confiance.
3. `fundamentalScore.bias` sert de contexte, jamais de signal d'entree.
4. Ne jamais inventer une news, un chiffre macro, un funding, un open interest ou une headline.
5. Continuer seulement si TradingView, session, SL, sizing, R:R et risk guard valident aussi.

Pre-session:

- Investing.com: calendrier economique, consensus, precedent, impact.
- ForexFactory: confirmation du calendrier, horaires exacts, impact rouge.
- Financial Juice: flux temps reel macro, Fed speakers, rumeurs, headlines rapides.
- InvestingLive: commentaires de marche, lecture rapide des reactions, contexte FX/DXY.
- ING Think: biais macro hebdomadaire, dollar, taux, banques centrales, geopolitique.

Ne pas inventer une news. Si une source n'est pas accessible, le dire et reduire la confiance.

## Protocole Hebdomadaire ING Think

Dimanche soir ou lundi matin:

1. Lire les analyses ING Think sur USD, Fed, inflation, taux, DXY, EUR/USD, GBP/USD, JPY, or si disponible.
2. Extraire 5 lignes maximum:
   - biais dollar: fort, faible, neutre;
   - biais taux US: hausse, baisse, neutre;
   - risque geopolitique: haut, normal, faible;
   - sentiment de risque: risk-on, risk-off, mixte;
   - events critiques de la semaine.
3. Traduire en biais:
   - XAU/USD: long, short ou neutre;
   - BTC/USD: long, short ou neutre.
4. Ne jamais entrer uniquement sur le biais ING: il sert de contexte, pas de signal.

## Workflow Pre-session

07h30-08h00 pour Londres:

1. Calendrier: Investing.com + ForexFactory.
2. News live: Financial Juice + InvestingLive.
3. DXY H4/H1, US10Y, SPX/NQ futures.
4. XAU: PDH, PDL, daily open, asian range, gaps.
5. BTC: funding, open interest si disponible, ETF/news crypto, CME gap.
6. Biais final: long, short, neutre.

13h30-14h30 pour New York:

1. Refaire calendrier US.
2. Verifier annonces 14h30 et 16h00.
3. Lire headlines Financial Juice.
4. Reevaluer DXY, US10Y, SPX/NQ.
5. Decider: trading normal, blackout, ou attente post-news.

## APIs Et Outils A Privilegier

### XAU/USD

- `news_get_calendar`: calendrier economique.
- `news_get_high_impact_events`: CPI, NFP, PCE, FOMC, Powell, Fed speakers.
- `news_check_blackout`: blocage automatique avant/apres news rouge.
- `macro_get_fred_context`: US10Y, Fed Funds, CPI, PCE, dollar broad proxy.
- `macro_get_us10y_context`: contexte taux US.
- `news_get_headlines`: headlines macro/geopolitique sourcees.

### BTC/USD

- `btc_get_funding`: funding Binance Futures.
- `btc_get_open_interest`: open interest Binance Futures.
- `btc_get_orderbook`: order book leger comme proxy DOM.
- `btc_get_market_context`: funding, OI, premium, ticker, order book optionnel.
- `news_get_headlines`: news crypto/BTC sourcees.
- `codex_pre_session_json includeOrderBook=true`: contexte complet.

### Fallback Manuel

Si les APIs sont indisponibles:

- utiliser `data/manual_calendar.json` si configure;
- utiliser RSS publics si disponibles;
- sinon faire une verification manuelle Investing.com/ForexFactory/Financial Juice/InvestingLive;
- baisser la confiance et ne jamais inventer.

## Matrice News

### XAU/USD

| News | Resultat > prevision | Resultat < prevision | Lecture |
|---|---|---|---|
| NFP | USD fort, XAU souvent short | USD faible, XAU souvent long | Attendre spike + confirmation |
| CPI | Inflation haute: reaction mixte; souvent USD/taux forts puis or peut hedge | Dovish, XAU souvent long | Priorite a reaction DXY/US10Y |
| PCE | Plus important pour Fed; haut = hawkish | bas = dovish | Haute importance |
| FOMC hawkish | XAU short | - | Ne pas entrer pendant decision |
| FOMC dovish | XAU long | - | Attendre conference/retest |
| US10Y hausse | XAU short | - | Inverse taux reels |
| Crise geopolitique | XAU long refuge | - | Peut monter avec USD |

### BTC/USD

| News | Resultat > prevision | Resultat < prevision | Lecture |
|---|---|---|---|
| NFP/CPI/PCE hawkish | BTC souvent short | BTC souvent long | Actif risk-on sensible liquidite |
| FOMC dovish | BTC long | - | Favorable liquidite |
| ETF inflows 5 jours | BTC long | - | Ne pas shorter sans signal fort |
| ETF outflows 5 jours | BTC short/neutre | - | Prudence longs |
| Regulation negative | BTC short | - | Reduire levier |
| Funding tres positif | Risque long squeeze down | - | Eviter longs tardifs |
| Funding negatif | Potentiel short squeeze | - | Chercher reversal long |

## Cycle Fed

Classer la Fed:

- Cycle hausse des taux: XAU sous pression, BTC sous pression.
- Pause restrictive: ranges, reactions fortes aux donnees inflation/emploi.
- Cycle baisse des taux: XAU et BTC favorises, surtout si DXY baisse.

Ne jamais ignorer PCE, speeches Fed, dot plot, conference Powell.

## Banques Centrales Globales

Surveiller:

- BCE: impact EUR/USD puis DXY.
- Bank of England: impact GBP/USD, sentiment Europe.
- Bank of Japan: impact USD/JPY, DXY, risk sentiment.

Si plusieurs banques centrales deviennent hawkish contre USD, DXY peut faiblir, favorable XAU.

## DXY - Protocole Dedie

Lire DXY en H4 puis H1:

1. Structure: HH/HL ou LH/LL.
2. Position vs daily open et PDH/PDL DXY.
3. POI DXY: OB, FVG, support/resistance.
4. Rejet DXY sur resistance = favorable XAU long.
5. Breakout DXY confirme = favorable XAU short et souvent BTC short.

Trade XAU contre DXY seulement si XAU a une structure propre et un setup valide.

## COT Report

Chaque vendredi:

- Lire CFTC Commitment of Traders pour l'or.
- Observer positions commerciales, managed money, changements nets.
- Utiliser comme biais long terme, pas comme signal intraday.

Si commercials tres short et managed money tres long, prudence sur longs tardifs XAU.

## Or Physique

Suivre mensuellement/trimestriellement:

- World Gold Council: achats banques centrales.
- ETF or: GLD, IAU flows.
- Production miniere et demande bijouterie/industrielle.

Ces donnees influencent le biais long terme, pas l'entree M15.

## Geopolitique

Evaluer chaque semaine:

- Russie-Ukraine.
- Moyen-Orient.
- Chine-Taiwan.
- tensions bancaires ou credit.

Risk-off fort = XAU peut monter meme si DXY monte. BTC peut baisser si fuite du risque.

## Blackout News

- Avant news rouge standard: aucune nouvelle entree 30 min avant.
- Apres news rouge standard: aucune nouvelle entree 15 min apres.
- FOMC/Powell/rate decision: blackout 60 min avant et 45 min apres par defaut.
- Apres news rouge: attendre au minimum cloture M15, ou M5 seulement si protocole post-news specifique.
- Si spread explose, ATR hors seuil ou slippage probable: no trade.
