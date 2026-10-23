# XAU/USD and BTC/USD Trading Workflow

This repository is optimized first for XAU/USD and BTC/USD, then extended to other pairs through a generic profile.

## Session Schedule

London:

- 07:30 briefing
- 08:00 to 10:30 active scans
- 15-minute scan rhythm

New York:

- 14:00 briefing
- 14:30 to 16:30 active scans
- 15-minute scan rhythm

## XAU/USD Profile

Primary context:

- DXY
- US10Y
- Fed expectations
- US high-impact news
- geopolitical risk
- PDH, PDL, PDC, daily open
- Asian range
- OPR
- OB, FVG, breaker blocks, mitigation blocks
- premium/discount

Main strategies:

- OB + FVG Retest
- Liquidity Sweep + Reversal
- Daily Sweep
- OPR
- London Breakout

## BTC/USD Profile

Primary context:

- ETF flows
- funding
- open interest
- liquidations
- DXY
- risk sentiment
- weekend liquidity regime

Main strategies:

- OB + FVG Retest
- Liquidity Sweep + Reversal
- Daily Sweep
- Mitigation Block
- BTC weekend filter

## Default Scan Output

Every scan should lead to one of four states:

- `NO_TRADE`
- `WATCH_ZONE`
- `SETUP_FORMING`
- `TRADE_PLAN_REQUIRES_VALIDATION`

No scan should directly imply execution.

## Trade Plan Must Include

- asset;
- session;
- strategy;
- higher-timeframe bias;
- entry;
- stop-loss;
- take-profit;
- risk in USD and percent;
- quantity;
- effective leverage estimate;
- score out of 12;
- invalidation condition;
- human validation status.
