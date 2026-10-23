# Intraday Strategy Library

These strategies are selected for day trading intraday M15/H1. They are not guaranteed to win. They are considered statistically testable because they define objective setup conditions, invalidation, risk and journal fields.

## Strategy Admission Rule

A strategy can be traded only after:

- at least 20 backtested examples;
- at least 30 forward-test demo trades before size increase;
- Profit Factor target above 1.5;
- R:R at least 1:2;
- journal evidence by asset and session.

## Core Strategies

### OB + FVG Retest

Best first strategy for XAU/USD and BTC/USD. Uses higher-timeframe bias, displacement, fair value gap and order-block retest.

### Liquidity Sweep + Reversal

Wait for a clear sweep of obvious liquidity, then MSS/CHoCH and retest. Strong around London and New York opens.

### Liquidity Sweep + Volume Zone

New advanced module. Combines a liquidity sweep with a high-volume node, volume profile zone, order-book imbalance, or visible volume expansion. It is valid only when the sweep rejects from a meaningful volume/liquidity zone and a structural stop exists.

### Daily Sweep

Targets previous day high/low, daily open, PDH/PDL/PDC and rejection after a false move.

### OPR

Opening price range strategy. Best used during London or New York session starts, not in dead liquidity.

### Fibonacci 61.8 + OB

Trend-continuation retracement strategy. Requires clear HTF trend and structural stop.

### London Breakout

XAU/USD only by default. Uses Asian range and London liquidity expansion, with filters for fakeouts.

### Breakout Retest

Generic multi-asset fallback. Requires range compression, clean breakout, retest, volume confirmation and no high-impact news blackout.

## Mandatory Filters

- `codex_pre_session_json`
- `news_check_blackout`
- `session_scan_now`
- `risk_calculate_position`
- `trade_validate_plan`
- `risk_guard_check`

If any mandatory filter rejects the setup, the strategy is not tradable.
