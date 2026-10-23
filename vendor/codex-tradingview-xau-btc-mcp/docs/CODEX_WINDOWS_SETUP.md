# Codex + TradingView Desktop Windows Setup

This project targets TradingView Desktop on Windows 11, not a normal browser tab.

## Goal

Codex connects to TradingView Desktop through Chrome DevTools Protocol (CDP), then the MCP server exposes controlled tools for:

- reading chart state, timeframe, OHLCV and indicators;
- reading Pine drawings, labels, boxes and tables;
- changing symbol and timeframe;
- taking screenshots;
- preparing and validating trade plans;
- detecting Trading Panel mode;
- submitting paper/live orders only through consent-gated execution tools.

## Windows Flow

1. Install Node.js 20 LTS or newer.
2. Install TradingView Desktop.
3. Open this repository in PowerShell.
4. Run:

```powershell
npm install
copy .env.example .env
copy rules.xau-btc.json rules.json
npm run setup:codex:windows
```

You can also double-click:

```text
setup-codex-windows.bat
```

5. Start TradingView Desktop with CDP:

```powershell
npm run tv -- launch
```

or:

```powershell
.\scripts\launch_tv_debug.bat
```

6. Test terminal status:

```powershell
npm run tv -- status
```

7. Run the full diagnostic:

```powershell
npm run tv -- doctor
```

8. In Codex, verify that the MCP server appears and that `tv_health_check` works.

## Trading Desk Commands

London XAU/USD paper session:

```text
session_start asset=XAUUSD session=london mode=paper
```

New York XAU/USD paper session:

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

Session state and journal files are stored in `.codex-tv-mcp/` by default.
To store them somewhere else, set:

```powershell
$env:CODEX_TV_MCP_HOME="C:\Users\YourName\.codex-tradingview-xau-btc-mcp"
```

Optional news/fundamental API keys live in `.env`:

```text
FINNHUB_API_KEY=
FRED_API_KEY=
BRAVE_SEARCH_API_KEY=
CRYPTOPANIC_API_KEY=
```

## Safety

Paper trading is the default. Live execution must always be validated by the user and must pass the consent-gated execution tools.
