# Setup Guide for Codex + TradingView Desktop Windows 11

This guide is for this repository:

```text
https://github.com/ftsebo7152-coder/codex-tradingview-xau-btc-mcp
```

It targets Codex and TradingView Desktop on Windows 11.

## 1. Clone and Install

```powershell
git clone https://github.com/ftsebo7152-coder/codex-tradingview-xau-btc-mcp.git
cd codex-tradingview-xau-btc-mcp
npm install
```

## 2. Configure Environment

```powershell
copy .env.example .env
notepad .env
```

Default CDP values:

```text
TRADINGVIEW_CDP_HOST=127.0.0.1
TRADINGVIEW_CDP_PORT=9222
```

News/fundamentals keys are optional at first. Binance BTC public market data and RSS/manual calendar can work without keys.

## 3. Configure Rules

```powershell
copy rules.xau-btc.json rules.json
```

`rules.xau-btc.json` is the full XAU/USD and BTC/USD profile. It keeps sessions, asset profiles, bias criteria, risk rules and news rules.

## 4. Add MCP Server To Codex

Recommended:

```powershell
codex mcp add tradingview -- node .\src\server.js
```

Alternative template files:

- `codex-config.example.toml` for `%USERPROFILE%\.codex\config.toml`
- `codex-mcp.example.json` for older JSON-style MCP clients

The Codex config path on Windows is usually:

```text
%USERPROFILE%\.codex\config.toml
```

If your Codex build still uses JSON MCP configuration, use:

```text
%USERPROFILE%\.codex\mcp.json
```

Do not overwrite other MCP servers. Merge entries.

## 5. Launch TradingView Desktop With CDP

Do not use the normal desktop icon when you need Codex control. Use:

```powershell
npm run tv -- launch
```

or:

```powershell
.\scripts\launch_tv_debug.bat
```

This launches TradingView Desktop with:

```text
--remote-debugging-port=9222
```

## 6. Verify

Terminal command:

```powershell
npm run tv -- status
```

Full diagnostic:

```powershell
npm run tv -- doctor
```

Codex MCP tool:

```text
tv_health_check
```

Expected:

```json
{
  "success": true,
  "cdp_connected": true,
  "api_available": true
}
```

## 7. Pre-Session Fundamental Context

Before XAU/USD New York:

```text
codex_pre_session_json asset=XAUUSD session=new_york timezone=Europe/Paris
```

Before BTC/USD New York:

```text
codex_pre_session_json asset=BTCUSD session=new_york timezone=Europe/Paris includeOrderBook=true
```

If `blackout.tradeAllowed` is false, refuse new trades until the post-news stabilization window is complete.

## 8. Trading Desk Session

London XAU/USD:

```text
session_start asset=XAUUSD session=london mode=paper
```

New York XAU/USD:

```text
session_start asset=XAUUSD session=new_york mode=paper
```

Immediate scan:

```text
session_scan_now
```

Stop session:

```text
session_stop
```

## 9. Safety

- Paper Trading first.
- No trade without stop-loss.
- Run `risk_calculate_position`.
- Run `trade_validate_plan`.
- Run `risk_guard_check`.
- Run `news_check_blackout`.
- Live execution always requires explicit human validation and consent-gated execution.

## 10. Stability

For reliable intraday operation:

- keep TradingView Desktop version pinned during testing;
- avoid auto-updating TradingView during a demo evaluation period;
- run `npm run tv -- doctor` before each major session until setup is stable.
