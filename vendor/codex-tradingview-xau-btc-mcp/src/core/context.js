import { config, providerStatus } from "../config.js";
import { todayRange, nowIso } from "../dates.js";
import { getFinnhubEconomicCalendar } from "../providers/finnhub.js";
import { getManualCalendar } from "../providers/manualCalendar.js";
import { getFredMacroContext } from "../providers/fred.js";
import { getBtcMarketContext } from "../providers/binance.js";
import { getCoinGeckoBitcoinContext } from "../providers/coingecko.js";
import { searchBraveNews } from "../providers/brave.js";
import { getCryptoPanicNews } from "../providers/cryptopanic.js";
import { getRssHeadlines } from "../providers/rss.js";
import { checkBlackout } from "./blackout.js";
import { scoreFundamentals } from "./scoring.js";

function dedupeEvents(events) {
  const seen = new Set();
  return events.filter((e) => {
    const key = `${e.time || e.date}|${e.country || ""}|${e.event || ""}`.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeAsset(asset) {
  const value = String(asset || "XAUUSD").toUpperCase().replace("/", "");
  if (["XAU", "GOLD", "XAUUSD"].includes(value)) return "XAUUSD";
  if (["BTC", "BITCOIN", "BTCUSD", "BTCUSDT"].includes(value)) return "BTCUSD";
  return value;
}

function buildNewsQuery(asset, session) {
  const assetKey = normalizeAsset(asset);
  if (assetKey === "BTCUSD") {
    return `Bitcoin BTC macro Fed ETF funding regulation ${session || "intraday"}`;
  }
  return `XAUUSD gold US dollar DXY US10Y Fed CPI NFP ${session || "intraday"}`;
}

export async function getEconomicCalendar({ from, to, timezone = config.timezone } = {}) {
  const [finnhub, manual] = await Promise.all([
    getFinnhubEconomicCalendar({ from, to, timezone }),
    Promise.resolve(getManualCalendar({ timezone }))
  ]);
  const events = dedupeEvents([...(finnhub.events || []), ...(manual.events || [])]);
  return {
    ok: events.length > 0,
    timezone,
    from,
    to,
    sources: { finnhub: finnhub.ok, manual: manual.ok },
    sourceErrors: [finnhub.ok ? null : { source: "finnhub", error: finnhub.error }, manual.ok ? null : { source: "manual", error: manual.error }].filter(Boolean),
    events
  };
}

export async function getHeadlines({ asset = "XAUUSD", query = null, count = 10 } = {}) {
  const assetKey = normalizeAsset(asset);
  const q = query || buildNewsQuery(assetKey);
  const [brave, rssMacro, rssCrypto, cryptoPanic] = await Promise.all([
    searchBraveNews({ query: q, count, freshness: "pd" }),
    getRssHeadlines({ category: "macro", maxPerFeed: 5 }),
    assetKey === "BTCUSD" ? getRssHeadlines({ category: "crypto", maxPerFeed: 5 }) : Promise.resolve({ ok: false, results: [] }),
    assetKey === "BTCUSD" ? getCryptoPanicNews({ currencies: "BTC" }) : Promise.resolve({ ok: false, results: [] })
  ]);
  const results = [
    ...(brave.results || []),
    ...(rssMacro.results || []),
    ...(rssCrypto.results || []),
    ...(cryptoPanic.results || [])
  ].slice(0, 30);
  return {
    ok: results.length > 0,
    asset: assetKey,
    query: q,
    sources: { brave: brave.ok, rssMacro: rssMacro.ok, rssCrypto: rssCrypto.ok, cryptoPanic: cryptoPanic.ok },
    sourceErrors: [brave, rssMacro, rssCrypto, cryptoPanic].filter((s) => s && !s.ok).map((s) => ({ source: s.source, error: s.error || s.errors || "unavailable" })),
    results
  };
}

export async function buildFundamentalContext({ asset = "XAUUSD", session = "new_york", timezone = config.timezone, from = null, to = null, includeOrderBook = false } = {}) {
  const assetKey = normalizeAsset(asset);
  const range = todayRange({ timezone, daysForward: 1 });
  const calendar = await getEconomicCalendar({ from: from || range.from, to: to || range.to, timezone });
  const [macro, headlines, btc, coingecko] = await Promise.all([
    getFredMacroContext(),
    getHeadlines({ asset: assetKey, query: buildNewsQuery(assetKey, session), count: 10 }),
    assetKey === "BTCUSD" ? getBtcMarketContext({ symbol: "BTCUSDT", includeOrderBook }) : Promise.resolve(null),
    assetKey === "BTCUSD" ? getCoinGeckoBitcoinContext() : Promise.resolve(null)
  ]);
  const btcContext = btc ? { ...btc, coingecko } : null;

  const blackout = checkBlackout({ events: calendar.events, asset: assetKey, timezone });
  const score = scoreFundamentals({ asset: assetKey, macro, btc: btcContext, headlines: headlines.results, blackout });

  return {
    schemaVersion: "1.0.0",
    generatedAt: nowIso(timezone),
    timezone,
    asset: assetKey,
    session,
    mode: "context_filter_only_not_trade_signal",
    providerStatus: providerStatus(),
    calendar,
    blackout,
    macro,
    btc: btcContext,
    headlines,
    fundamentalScore: score,
    codexInstructions: [
      "Use this JSON as pre-session fundamental context only.",
      "If blackout.tradeAllowed is false, refuse new entries and wait for post-news stabilization.",
      "Never invent missing data. If a provider is unavailable, lower confidence.",
      "A technical setup, SL, sizing, R:R >= 1:2, session rules, and human live validation remain mandatory."
    ]
  };
}
