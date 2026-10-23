# Multi-Asset Extension

The first-class assets are XAU/USD and BTC/USD. Other pairs are supported through a generic profile.

## Generic Pair Rules

For any non-XAU and non-BTC instrument:

- require manual confirmation of broker contract specs;
- require `point_value` before trusting position sizing;
- require spread and ATR checks;
- require a session liquidity map;
- require strategy validation before autonomous paper-trading.

## Generic Profile

Default strategies:

- OB + FVG Retest
- Liquidity Sweep + Reversal
- Fibonacci 61.8 + OB
- Breakout + Retest

Default filters:

- higher-timeframe bias;
- session liquidity;
- high-impact calendar risk;
- spread;
- ATR minimum and maximum;
- structural stop-loss;
- R:R at least 1:2.

## Promotion To Dedicated Profile

A generic pair can become a dedicated profile only after:

- at least 80 journaled demo trades;
- Profit Factor above 1.5;
- drawdown under control;
- contract specs verified;
- session behavior documented.
