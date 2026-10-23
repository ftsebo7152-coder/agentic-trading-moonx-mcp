import { z } from "zod";
import { jsonResult } from "./_format.js";
import { providerStatus } from "../config.js";
import { getEconomicCalendar, getHeadlines, buildFundamentalContext } from "../core/context.js";
import { checkBlackout } from "../core/blackout.js";
import { getFredMacroContext, getFredSeries } from "../providers/fred.js";
import { getBtcMarketContext, getFundingRate, getOpenInterest, getOrderBook } from "../providers/binance.js";
import { getCoinGeckoBitcoinContext } from "../providers/coingecko.js";
import { clearCache } from "../http.js";

const assetSchema = z.enum(["XAUUSD", "XAU/USD", "BTCUSD", "BTC/USD", "BTCUSDT"]);
const sessionSchema = z.enum(["london", "new_york", "asia", "weekend", "custom"]);

export function registerNewsTools(server) {
  server.tool("news_fundamentals_health", "Check provider availability for the built-in news/fundamentals module.", {}, async () =>
    jsonResult({
      ok: true,
      module: "built-in-news-fundamentals",
      providers: providerStatus(),
      note: "These tools provide context filters only. They never create a trade signal by themselves.",
    }),
  );

  server.tool("news_clear_cache", "Clear in-memory API cache for fresh news/fundamental data.", {}, async () => {
    clearCache();
    return jsonResult({ ok: true, message: "News/fundamental cache cleared." });
  });

  server.tool(
    "news_get_calendar",
    "Fetch normalized economic calendar events from configured providers and manual calendar fallback.",
    {
      from: z.string().optional(),
      to: z.string().optional(),
      timezone: z.string().optional().default("Europe/Paris"),
    },
    async (args) => jsonResult(await getEconomicCalendar(args)),
  );

  server.tool(
    "news_get_high_impact_events",
    "Fetch calendar events and return the high-impact subset used for CPI, NFP, PCE, FOMC and Fed speaker risk.",
    {
      asset: assetSchema.default("XAUUSD"),
      from: z.string().optional(),
      to: z.string().optional(),
      timezone: z.string().optional().default("Europe/Paris"),
    },
    async ({ asset, from, to, timezone }) => {
      const calendar = await getEconomicCalendar({ from, to, timezone });
      const blackout = checkBlackout({ events: calendar.events, asset, timezone });
      return jsonResult({
        ok: true,
        asset,
        sources: calendar.sources,
        highImpactEvents: blackout.relevantHighImpactEvents,
        nextHighImpactEvent: blackout.nextHighImpactEvent,
      });
    },
  );

  server.tool(
    "news_get_next_event",
    "Return the next relevant high-impact event for the asset.",
    {
      asset: assetSchema.default("XAUUSD"),
      timezone: z.string().optional().default("Europe/Paris"),
    },
    async ({ asset, timezone }) => {
      const calendar = await getEconomicCalendar({ timezone });
      const blackout = checkBlackout({ events: calendar.events, asset, timezone });
      return jsonResult({ ok: true, asset, nextHighImpactEvent: blackout.nextHighImpactEvent, reason: blackout.reason });
    },
  );

  server.tool(
    "news_check_blackout",
    "Check whether a high-impact news blackout blocks new XAU/USD or BTC/USD entries.",
    {
      asset: assetSchema.default("XAUUSD"),
      from: z.string().optional(),
      to: z.string().optional(),
      timezone: z.string().optional().default("Europe/Paris"),
      now: z.string().optional(),
    },
    async ({ asset, from, to, timezone, now }) => {
      const calendar = await getEconomicCalendar({ from, to, timezone });
      return jsonResult({ calendarSources: calendar.sources, ...checkBlackout({ events: calendar.events, asset, timezone, now }) });
    },
  );

  server.tool(
    "news_get_headlines",
    "Fetch sourced macro or crypto headlines from Brave, RSS, and CryptoPanic when configured.",
    {
      asset: assetSchema.default("XAUUSD"),
      query: z.string().optional(),
      count: z.coerce.number().min(1).max(20).default(10),
    },
    async (args) => jsonResult(await getHeadlines(args)),
  );

  server.tool(
    "macro_get_fred_context",
    "Fetch FRED macro context: US10Y, Fed Funds, CPI, PCE and broad dollar index proxy.",
    {
      includeObservations: z.coerce.boolean().default(false),
    },
    async ({ includeObservations }) => jsonResult(await getFredMacroContext({ includeObservations })),
  );

  server.tool(
    "macro_get_series",
    "Fetch any FRED series by ID, for example DGS10, DFF, CPIAUCSL, PCEPI, DTWEXBGS.",
    {
      seriesId: z.string(),
      observationStart: z.string().optional(),
      observationEnd: z.string().optional(),
    },
    async ({ seriesId, observationStart, observationEnd }) => jsonResult(await getFredSeries(seriesId, { observationStart, observationEnd })),
  );

  server.tool("macro_get_us10y_context", "Fetch US10Y context from FRED series DGS10.", {}, async () =>
    jsonResult(await getFredSeries("DGS10")),
  );

  server.tool("macro_get_fed_context", "Fetch Fed Funds context from FRED series DFF.", {}, async () =>
    jsonResult(await getFredSeries("DFF")),
  );

  server.tool(
    "btc_get_market_context",
    "Fetch BTC futures context from Binance public API: funding, open interest, premium, ticker and optional order book.",
    {
      symbol: z.string().default("BTCUSDT"),
      includeOrderBook: z.coerce.boolean().default(false),
    },
    async (args) => jsonResult(await getBtcMarketContext(args)),
  );

  server.tool("btc_get_funding", "Fetch latest BTC/USDT funding-rate history from Binance Futures.", { symbol: z.string().default("BTCUSDT") }, async ({ symbol }) =>
    jsonResult(await getFundingRate(symbol)),
  );

  server.tool("btc_get_open_interest", "Fetch current BTC/USDT open interest from Binance Futures.", { symbol: z.string().default("BTCUSDT") }, async ({ symbol }) =>
    jsonResult(await getOpenInterest(symbol)),
  );

  server.tool(
    "btc_get_orderbook",
    "Fetch BTC/USDT futures order book snapshot from Binance public API as a lightweight liquidity proxy.",
    {
      symbol: z.string().default("BTCUSDT"),
      limit: z.coerce.number().min(5).max(1000).default(50),
    },
    async ({ symbol, limit }) => jsonResult(await getOrderBook(symbol, limit)),
  );

  server.tool("btc_get_coingecko_context", "Fetch BTC spot market context from CoinGecko Demo API when COINGECKO_API_KEY is configured.", {}, async () =>
    jsonResult(await getCoinGeckoBitcoinContext()),
  );

  server.tool(
    "fundamental_build_context",
    "Build full pre-session fundamental context JSON for Codex: calendar, blackout, macro, BTC data, headlines, score and trade permission.",
    {
      asset: assetSchema.default("XAUUSD"),
      session: sessionSchema.default("new_york"),
      timezone: z.string().optional().default("Europe/Paris"),
      from: z.string().optional(),
      to: z.string().optional(),
      includeOrderBook: z.coerce.boolean().default(false),
    },
    async (args) => jsonResult(await buildFundamentalContext(args)),
  );

  server.tool(
    "codex_pre_session_json",
    "Primary pre-session tool. Use before XAU/USD or BTC/USD London/New York sessions and merge with TradingView technical scan.",
    {
      asset: assetSchema.default("XAUUSD"),
      session: sessionSchema.default("new_york"),
      timezone: z.string().optional().default("Europe/Paris"),
      includeOrderBook: z.coerce.boolean().default(false),
    },
    async (args) => jsonResult(await buildFundamentalContext(args)),
  );
}
