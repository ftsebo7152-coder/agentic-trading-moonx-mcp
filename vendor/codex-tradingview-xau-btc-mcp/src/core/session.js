import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import http from "node:http";
import { join } from "node:path";
import * as chart from "./chart.js";
import * as observeCore from "./observe.js";
import * as trading from "./trading.js";
import * as tradingExec from "./tradingExec.js";

const APP_DIR = process.env.CODEX_TV_MCP_HOME || join(process.cwd(), ".codex-tv-mcp");
const STATE_PATH = join(APP_DIR, "session-state.json");
const JOURNAL_DIR = join(APP_DIR, "journal");

const SESSION_WINDOWS = {
  london: {
    label: "London",
    briefing_start: "07:30",
    active_start: "08:00",
    active_end: "10:30",
    default_timeframe: "15",
    focus: ["asian liquidity sweep", "OPR", "OB + FVG retest", "Daily Sweep"],
  },
  new_york: {
    label: "New York",
    briefing_start: "14:00",
    active_start: "14:30",
    active_end: "16:30",
    default_timeframe: "15",
    focus: ["US news reaction", "DXY confirmation", "liquidity sweep", "OB + FVG retest"],
  },
  full_day: {
    label: "London + New York",
    briefing_start: "07:30",
    active_start: "08:00",
    active_end: "16:30",
    default_timeframe: "15",
    focus: ["London AM", "New York AM", "session handoff", "major liquidity pools"],
  },
};

const ASSET_PROFILES = {
  XAUUSD: {
    aliases: ["XAUUSD", "XAU/USD", "OANDA:XAUUSD", "FOREXCOM:XAUUSD", "TVC:GOLD"],
    default_symbol: "OANDA:XAUUSD",
    risk_point_value_hint: "Usually 1 USD per 1.00 price move per 1 CFD unit, broker-dependent.",
    preferred_sessions: ["london", "new_york"],
    primary_filters: ["DXY", "US10Y", "Fed expectations", "US high-impact news", "geopolitics"],
    strategies: ["OB_FVG_RETEST", "LIQUIDITY_SWEEP_REVERSAL", "DAILY_SWEEP", "OPR", "LONDON_BREAKOUT"],
  },
  BTCUSD: {
    aliases: ["BTCUSD", "BTC/USD", "BTCUSDT", "BINANCE:BTCUSDT", "COINBASE:BTCUSD"],
    default_symbol: "BINANCE:BTCUSDT",
    risk_point_value_hint: "Usually 1 USD per 1.00 price move per 1 BTC, exchange/broker-dependent.",
    preferred_sessions: ["new_york", "full_day"],
    primary_filters: ["ETF flows", "funding", "open interest", "liquidations", "DXY", "risk sentiment"],
    strategies: ["OB_FVG_RETEST", "LIQUIDITY_SWEEP_REVERSAL", "DAILY_SWEEP", "MITIGATION_BLOCK", "WEEKEND_FILTER"],
  },
  GENERIC: {
    aliases: [],
    default_symbol: null,
    risk_point_value_hint: "Set point_value manually before trusting sizing.",
    preferred_sessions: ["london", "new_york", "full_day"],
    primary_filters: ["session liquidity", "calendar risk", "spread", "ATR", "higher-timeframe bias"],
    strategies: ["OB_FVG_RETEST", "LIQUIDITY_SWEEP_REVERSAL", "FIB_618_OB", "BREAKOUT_RETEST"],
  },
};

function ensureDirs() {
  mkdirSync(APP_DIR, { recursive: true });
  mkdirSync(JOURNAL_DIR, { recursive: true });
}

function todayStamp() {
  return new Date().toISOString().slice(0, 10);
}

function normalizeAsset(asset = "XAUUSD") {
  const clean = String(asset).toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (clean.includes("XAU")) return "XAUUSD";
  if (clean.includes("BTC")) return "BTCUSD";
  return "GENERIC";
}

function scheduleFor(sessionName, intervalMinutes) {
  const session = SESSION_WINDOWS[sessionName] || SESSION_WINDOWS.full_day;
  const [h1, m1] = session.active_start.split(":").map(Number);
  const [h2, m2] = session.active_end.split(":").map(Number);
  const start = h1 * 60 + m1;
  const end = h2 * 60 + m2;
  const times = [];
  for (let t = start; t <= end; t += intervalMinutes) {
    times.push(`${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`);
  }
  return times;
}

function readState() {
  if (!existsSync(STATE_PATH)) return null;
  try {
    return JSON.parse(readFileSync(STATE_PATH, "utf8"));
  } catch {
    return null;
  }
}

function writeState(state) {
  ensureDirs();
  writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
}

function appendJournal(event) {
  ensureDirs();
  const file = join(JOURNAL_DIR, `${todayStamp()}.jsonl`);
  const row = JSON.stringify({ at: new Date().toISOString(), ...event });
  writeFileSync(file, existsSync(file) ? `${readFileSync(file, "utf8")}${row}\n` : `${row}\n`);
  return file;
}

function cdpAvailable(port = Number(process.env.TRADINGVIEW_CDP_PORT || 9222)) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/json/version`, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
    req.on("error", () => resolve(false));
  });
}

export async function startSession({
  asset = "XAUUSD",
  session = "london",
  mode = "paper",
  capital = 200,
  risk_pct = 1,
  scan_interval_minutes = 15,
  set_chart = true,
  symbol,
  timeframe,
} = {}) {
  const sessionName = SESSION_WINDOWS[session] ? session : "full_day";
  const assetKey = normalizeAsset(asset);
  const profile = ASSET_PROFILES[assetKey];
  const chosenSymbol = symbol || profile.default_symbol || asset;
  const chosenTimeframe = timeframe || SESSION_WINDOWS[sessionName].default_timeframe;
  const schedule = scheduleFor(sessionName, Math.max(5, Math.min(60, Number(scan_interval_minutes) || 15)));

  const state = {
    active: true,
    paused: false,
    asset,
    asset_profile: assetKey,
    symbol: chosenSymbol,
    session: sessionName,
    mode,
    capital: Number(capital),
    risk_pct: Number(risk_pct),
    scan_interval_minutes: Number(scan_interval_minutes),
    timeframe: chosenTimeframe,
    max_trades_per_day: 4,
    optimal_trades_per_day: "2-3",
    stop_daily_pct: 3,
    started_at: new Date().toISOString(),
    schedule,
    session_window: SESSION_WINDOWS[sessionName],
    profile,
    guardrails: [
      "Paper Trading first.",
      "Stop-loss required before every entry.",
      "No live execution without explicit human validation.",
      "Risk must be calculated before any order.",
      "No trade if spread/news/ATR/session context is not controlled.",
    ],
  };

  const chart_actions = [];
  if (set_chart) {
    try {
      chart_actions.push(await chart.setSymbol({ symbol: chosenSymbol }));
      chart_actions.push(await chart.setTimeframe({ timeframe: chosenTimeframe }));
    } catch (err) {
      chart_actions.push({ success: false, error: err.message, hint: "TradingView may not be running with CDP enabled yet." });
    }
  }

  writeState(state);
  const journal_path = appendJournal({ type: "session_start", state });

  return {
    success: true,
    state,
    chart_actions,
    journal_path,
    next_step: "Run session_scan_now during scheduled times or when price reaches a key level.",
  };
}

export function getSessionStatus() {
  const state = readState();
  return {
    success: true,
    active: Boolean(state?.active),
    state,
    state_path: STATE_PATH,
    journal_dir: JOURNAL_DIR,
  };
}

export function pauseSession({ reason = "" } = {}) {
  const state = readState();
  if (!state?.active) return { success: false, error: "No active session." };
  state.paused = true;
  state.pause_reason = reason;
  state.paused_at = new Date().toISOString();
  writeState(state);
  const journal_path = appendJournal({ type: "session_pause", reason });
  return { success: true, state, journal_path };
}

export function resumeSession() {
  const state = readState();
  if (!state?.active) return { success: false, error: "No active session." };
  state.paused = false;
  state.resumed_at = new Date().toISOString();
  delete state.pause_reason;
  writeState(state);
  const journal_path = appendJournal({ type: "session_resume" });
  return { success: true, state, journal_path };
}

export function stopSession({ notes = "" } = {}) {
  const state = readState();
  if (!state?.active) return { success: false, error: "No active session." };
  state.active = false;
  state.stopped_at = new Date().toISOString();
  state.stop_notes = notes;
  writeState(state);
  const journal_path = appendJournal({ type: "session_stop", notes, state });
  return { success: true, state, journal_path };
}

export async function scanNow({
  include_screenshot = false,
  include_pine_drawings = true,
  ohlcv_count = 80,
  pine_filter = "",
} = {}) {
  const state = readState();
  if (!state?.active) {
    return { success: false, error: "No active session. Run session_start first." };
  }
  if (state.paused) {
    return { success: false, error: "Session is paused.", reason: state.pause_reason || "" };
  }

  let observation = null;
  let trading_mode = null;
  let positions = null;
  const errors = [];

  if (!(await cdpAvailable())) {
    errors.push({
      area: "cdp",
      error: "TradingView CDP is not reachable on port 9222. Launch TradingView Desktop with CDP before scanning live chart data.",
    });
  } else {
    try {
      observation = await observeCore.observe({ include_screenshot, include_pine_drawings, ohlcv_count, pine_filter });
    } catch (err) {
      errors.push({ area: "observe", error: err.message });
    }

    try {
      trading_mode = await tradingExec.detectTradingMode();
    } catch (err) {
      errors.push({ area: "trading_mode", error: err.message });
    }

    try {
      positions = {
        positions: await trading.getPositions(),
        orders: await trading.getOrders(),
      };
    } catch (err) {
      errors.push({ area: "positions_orders", error: err.message });
    }
  }

  const report = {
    success: true,
    scanned_at: new Date().toISOString(),
    session: state,
    observation,
    trading_mode,
    positions,
    errors,
    decision_template: {
      allowed_outputs: ["NO_TRADE", "WATCH_ZONE", "SETUP_FORMING", "TRADE_PLAN_REQUIRES_VALIDATION"],
      minimum_score: state.asset_profile === "XAUUSD" ? "7/12 normal, 8/12 around high-impact news" : "7/12 to 9/12 depending liquidity regime",
      mandatory_checks: [
        "higher timeframe bias",
        "PDH/PDL/PDC/daily open",
        "premium/discount",
        "liquidity sweep or OB/FVG context",
        "spread and ATR acceptable",
        "news risk acceptable",
        "stop-loss structural",
        "risk <= configured risk_pct",
      ],
    },
    instruction:
      "Use this payload to decide whether the market is no-trade, watch-only, setup-forming, or ready for a validated trade plan. Never submit an order from this scan alone.",
  };

  const journal_path = appendJournal({ type: "session_scan", report });
  return { ...report, journal_path };
}

export function calculateRisk({
  capital = 200,
  risk_pct = 1,
  entry,
  stop_loss,
  point_value = 1,
} = {}) {
  const entryNum = Number(entry);
  const slNum = Number(stop_loss);
  const capitalNum = Number(capital);
  const riskPctNum = Number(risk_pct);
  const pointValueNum = Number(point_value);

  if (!Number.isFinite(entryNum) || !Number.isFinite(slNum) || entryNum === slNum) {
    return { success: false, error: "entry and stop_loss must be valid different numbers." };
  }
  if (!Number.isFinite(capitalNum) || capitalNum <= 0) {
    return { success: false, error: "capital must be positive." };
  }
  if (!Number.isFinite(pointValueNum) || pointValueNum <= 0) {
    return { success: false, error: "point_value must be positive." };
  }

  const riskAmount = capitalNum * (riskPctNum / 100);
  const stopDistance = Math.abs(entryNum - slNum);
  const quantity = riskAmount / (stopDistance * pointValueNum);

  return {
    success: true,
    capital: capitalNum,
    risk_pct: riskPctNum,
    risk_amount: Number(riskAmount.toFixed(4)),
    entry: entryNum,
    stop_loss: slNum,
    stop_distance: Number(stopDistance.toFixed(6)),
    point_value: pointValueNum,
    quantity: Number(quantity.toFixed(8)),
    warning: "Broker contract specs can differ. Verify point_value, tick size, margin, spread and fees before executing.",
  };
}

export function validateTradePlan({
  direction,
  entry,
  stop_loss,
  take_profit,
  score = 0,
  rr_min = 2,
  mode = "paper",
  human_validated = false,
} = {}) {
  const entryNum = Number(entry);
  const slNum = Number(stop_loss);
  const tpNum = Number(take_profit);
  if (!direction || !["buy", "sell", "long", "short"].includes(String(direction).toLowerCase())) {
    return { success: false, trade_allowed: false, reason: "direction must be buy/sell/long/short." };
  }
  if (![entryNum, slNum, tpNum].every(Number.isFinite)) {
    return { success: false, trade_allowed: false, reason: "entry, stop_loss and take_profit must be valid numbers." };
  }
  const risk = Math.abs(entryNum - slNum);
  const reward = Math.abs(tpNum - entryNum);
  const rr = reward / risk;
  const refusals = [];
  if (risk <= 0) refusals.push("stop_loss is invalid");
  if (rr < Number(rr_min)) refusals.push(`R:R ${rr.toFixed(2)} is below minimum ${rr_min}`);
  if (Number(score) < 7) refusals.push("setup score below 7/12");
  if (mode !== "paper" && !human_validated) refusals.push("live/non-paper mode requires explicit human validation");

  return {
    success: true,
    trade_allowed: refusals.length === 0,
    refusals,
    rr: Number(rr.toFixed(3)),
    risk_distance: risk,
    reward_distance: reward,
    execution_note: "Even when allowed, call trading_detect_mode before any trading_submit_order.",
  };
}

export function riskGuardCheck({
  has_stop_loss = true,
  rr = 0,
  risk_pct = 1,
  max_risk_pct = 1,
  daily_loss_pct = 0,
  max_daily_loss_pct = 3,
  consecutive_losses = 0,
  trades_today = 0,
  max_trades_per_day = 4,
  news_blackout_active = false,
  spread = null,
  max_spread = null,
  atr_state = "normal",
  mode = "paper",
  human_validated = false,
  score = 0,
  min_score = 7,
} = {}) {
  const refusals = [];

  if (!has_stop_loss) refusals.push("No predefined stop-loss.");
  if (Number(rr) < 2) refusals.push(`R:R ${Number(rr).toFixed(2)} is below minimum 1:2.`);
  if (Number(risk_pct) > Number(max_risk_pct)) refusals.push(`Risk ${risk_pct}% exceeds max ${max_risk_pct}%.`);
  if (Number(daily_loss_pct) >= Number(max_daily_loss_pct)) refusals.push(`Daily loss ${daily_loss_pct}% reached max ${max_daily_loss_pct}%.`);
  if (Number(consecutive_losses) >= 2) refusals.push("Two consecutive losses: pause or require exceptional reduced-risk setup.");
  if (Number(trades_today) >= Number(max_trades_per_day)) refusals.push(`Max trades reached: ${trades_today}/${max_trades_per_day}.`);
  if (news_blackout_active) refusals.push("High-impact news blackout active.");
  if (max_spread !== null && spread !== null && Number(spread) > Number(max_spread)) refusals.push(`Spread ${spread} exceeds max ${max_spread}.`);
  if (["too_low", "too_high", "uncontrolled"].includes(String(atr_state))) refusals.push(`ATR state not tradable: ${atr_state}.`);
  if (Number(score) < Number(min_score)) refusals.push(`Setup score ${score}/12 below minimum ${min_score}/12.`);
  if (mode !== "paper" && !human_validated) refusals.push("Live/non-paper mode requires explicit human validation.");

  return {
    success: true,
    trade_allowed: refusals.length === 0,
    refusals,
    guardrails_checked: {
      has_stop_loss,
      rr: Number(rr),
      risk_pct: Number(risk_pct),
      daily_loss_pct: Number(daily_loss_pct),
      consecutive_losses: Number(consecutive_losses),
      trades_today: Number(trades_today),
      news_blackout_active: Boolean(news_blackout_active),
      spread,
      max_spread,
      atr_state,
      mode,
      human_validated: Boolean(human_validated),
      score: Number(score),
      min_score: Number(min_score),
    },
  };
}
