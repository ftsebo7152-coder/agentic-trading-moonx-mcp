# Codex Operating Guide

This repository connects Codex to TradingView Desktop on Windows 11 through MCP/CDP.

## Priorities

1. Keep Paper Trading as the default operating mode.
2. Optimize first for XAU/USD and BTC/USD.
3. Support other pairs only through the generic profile until their contract specs and session behavior are verified.
4. Never propose or execute a trade without a predefined stop-loss.
5. Always calculate risk before any order.
6. Never submit live orders without explicit human validation.

## Tool Selection

Start a session:

- `session_start`

Pre-session fundamentals:

- `codex_pre_session_json`
- `news_check_blackout`
- `fundamental_build_context`
- `btc_get_market_context`
- `macro_get_fred_context`

Scan during a session:

- `session_scan_now`

Risk and validation:

- `risk_calculate_position`
- `trade_validate_plan`
- `risk_guard_check`

Chart context:

- `chart_observe`
- `chart_get_state`
- `quote_get`
- `data_get_ohlcv`
- `data_get_study_values`
- `data_get_pine_lines`
- `data_get_pine_labels`
- `data_get_pine_tables`
- `data_get_pine_boxes`

Trading mode and execution:

- call `trading_detect_mode` before any execution;
- use `trading_submit_order` only with explicit consent and only after plan validation;
- never infer consent from prior messages.

## Session Defaults

London:

```text
session_start asset=XAUUSD session=london mode=paper
```

New York:

```text
session_start asset=XAUUSD session=new_york mode=paper
```

BTC New York:

```text
session_start asset=BTCUSD session=new_york mode=paper
```

## Response Discipline

When a setup is not good enough, say `NO_TRADE` and explain why.

When a setup is forming, say `WATCH_ZONE` or `SETUP_FORMING`.

When a setup is tradable, output a full plan with:

- direction;
- entry;
- stop-loss;
- take-profit;
- risk;
- quantity;
- R:R;
- score;
- invalidation;
- execution permission status.

Before any trade plan becomes executable, run news/fundamental context and risk guard checks. If `blackout.tradeAllowed` is false or `risk_guard_check.trade_allowed` is false, refuse the trade.
