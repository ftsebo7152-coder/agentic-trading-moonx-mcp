# MCP News/Fundamentals

Outils recommandes quand le serveur MCP news/fundamentals est disponible:

## News

- `news_get_calendar`
- `news_get_high_impact_events`
- `news_get_next_event`
- `news_check_blackout`
- `news_get_headlines`

## Macro

- `macro_get_fred_context`
- `macro_get_series`
- `macro_get_us10y_context`
- `macro_get_fed_context`

## BTC

- `btc_get_market_context`
- `btc_get_funding`
- `btc_get_open_interest`
- `btc_get_orderbook`

## Decision

- `codex_pre_session_json`
- `fundamental_build_context`
- `risk_guard_check`

## Regle D'Utilisation

Ces outils ne donnent jamais une entree directe. Ils filtrent le contexte:

- trade autorise ou bloque;
- biais fondamental long, short ou neutre;
- confiance;
- sources disponibles ou absentes;
- raisons de prudence.

Un trade reste valide seulement si:

1. contexte fondamental compatible;
2. pas de blackout;
3. setup technique confirme;
4. SL structurel;
5. sizing calcule;
6. R:R >= 1:2;
7. risk guard accepte;
8. validation humaine en mode reel.
