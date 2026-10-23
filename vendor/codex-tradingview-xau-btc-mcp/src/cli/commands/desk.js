import { register } from "../router.js";
import * as core from "../../core/session.js";

register("desk", {
  description: "Codex trading desk session controls for XAU/USD, BTC/USD, and generic pairs",
  subcommands: new Map([
    [
      "start",
      {
        description: "Start a structured desk session",
        options: {
          asset: { type: "string", description: "XAUUSD, BTCUSD, or another symbol" },
          session: { type: "string", description: "london, new_york, or full_day" },
          mode: { type: "string", description: "paper or live" },
          capital: { type: "string", description: "Capital, default 200" },
          risk: { type: "string", description: "Risk percent per trade, default 1" },
          interval: { type: "string", description: "Scan interval in minutes, default 15" },
          symbol: { type: "string", description: "TradingView symbol override" },
          timeframe: { type: "string", description: "TradingView timeframe override" },
          no_set_chart: { type: "boolean", description: "Do not change TradingView symbol/timeframe" },
        },
        handler: async ({ asset, session, mode, capital, risk, interval, symbol, timeframe, no_set_chart }) =>
          core.startSession({
            asset,
            session,
            mode,
            capital: capital ? Number(capital) : 200,
            risk_pct: risk ? Number(risk) : 1,
            scan_interval_minutes: interval ? Number(interval) : 15,
            symbol,
            timeframe,
            set_chart: !no_set_chart,
          }),
      },
    ],
    ["status", { description: "Show desk session status", handler: async () => core.getSessionStatus() }],
    [
      "scan",
      {
        description: "Run a scan now",
        options: {
          screenshot: { type: "boolean", description: "Include screenshot" },
          count: { type: "string", description: "OHLCV bars to summarize" },
          pine: { type: "string", description: "Pine study filter" },
        },
        handler: async ({ screenshot, count, pine }) =>
          core.scanNow({ include_screenshot: Boolean(screenshot), ohlcv_count: count ? Number(count) : 80, pine_filter: pine || "" }),
      },
    ],
    [
      "pause",
      {
        description: "Pause active session",
        options: { reason: { type: "string", description: "Pause reason" } },
        handler: async ({ reason }) => core.pauseSession({ reason }),
      },
    ],
    ["resume", { description: "Resume session", handler: async () => core.resumeSession() }],
    [
      "stop",
      {
        description: "Stop active session",
        options: { notes: { type: "string", description: "Session close notes" } },
        handler: async ({ notes }) => core.stopSession({ notes }),
      },
    ],
  ]),
});
