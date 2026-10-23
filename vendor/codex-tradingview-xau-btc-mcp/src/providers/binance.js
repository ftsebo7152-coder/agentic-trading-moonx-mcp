import { fetchJson } from "../http.js";

const BASE = "https://fapi.binance.com";

export async function getFundingRate(symbol = "BTCUSDT") {
  const url = new URL(`${BASE}/fapi/v1/fundingRate`);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("limit", "8");
  const result = await fetchJson(url.toString(), {}, { source: "binance:futures_funding", cacheTtlSeconds: 60 });
  if (!result.ok) return { ...result, symbol, latest: null };
  const rows = Array.isArray(result.data) ? result.data : [];
  const latest = rows.at(-1) || null;
  return {
    ok: true,
    source: "binance:futures_funding",
    symbol,
    latest: latest ? {
      fundingRate: Number(latest.fundingRate),
      fundingTime: latest.fundingTime ? new Date(Number(latest.fundingTime)).toISOString() : null,
      markPrice: latest.markPrice ? Number(latest.markPrice) : null
    } : null,
    history: rows
  };
}

export async function getOpenInterest(symbol = "BTCUSDT") {
  const url = new URL(`${BASE}/fapi/v1/openInterest`);
  url.searchParams.set("symbol", symbol);
  const result = await fetchJson(url.toString(), {}, { source: "binance:futures_open_interest", cacheTtlSeconds: 30 });
  if (!result.ok) return { ...result, symbol, openInterest: null };
  return {
    ok: true,
    source: "binance:futures_open_interest",
    symbol,
    openInterest: Number(result.data?.openInterest),
    time: result.data?.time ? new Date(Number(result.data.time)).toISOString() : null
  };
}

export async function getPremiumIndex(symbol = "BTCUSDT") {
  const url = new URL(`${BASE}/fapi/v1/premiumIndex`);
  url.searchParams.set("symbol", symbol);
  const result = await fetchJson(url.toString(), {}, { source: "binance:futures_premium_index", cacheTtlSeconds: 30 });
  if (!result.ok) return { ...result, symbol };
  return {
    ok: true,
    source: "binance:futures_premium_index",
    symbol,
    markPrice: Number(result.data?.markPrice),
    indexPrice: Number(result.data?.indexPrice),
    lastFundingRate: Number(result.data?.lastFundingRate),
    nextFundingTime: result.data?.nextFundingTime ? new Date(Number(result.data.nextFundingTime)).toISOString() : null,
    time: result.data?.time ? new Date(Number(result.data.time)).toISOString() : null
  };
}

export async function getTicker24h(symbol = "BTCUSDT") {
  const url = new URL(`${BASE}/fapi/v1/ticker/24hr`);
  url.searchParams.set("symbol", symbol);
  const result = await fetchJson(url.toString(), {}, { source: "binance:futures_ticker_24h", cacheTtlSeconds: 30 });
  if (!result.ok) return { ...result, symbol };
  return {
    ok: true,
    source: "binance:futures_ticker_24h",
    symbol,
    priceChangePercent: Number(result.data?.priceChangePercent),
    lastPrice: Number(result.data?.lastPrice),
    volume: Number(result.data?.volume),
    quoteVolume: Number(result.data?.quoteVolume),
    highPrice: Number(result.data?.highPrice),
    lowPrice: Number(result.data?.lowPrice)
  };
}

export async function getOrderBook(symbol = "BTCUSDT", limit = 50) {
  const url = new URL(`${BASE}/fapi/v1/depth`);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("limit", String(limit));
  const result = await fetchJson(url.toString(), {}, { source: "binance:futures_depth", cacheTtlSeconds: 10 });
  if (!result.ok) return { ...result, symbol };
  const bestBid = result.data?.bids?.[0] ? { price: Number(result.data.bids[0][0]), qty: Number(result.data.bids[0][1]) } : null;
  const bestAsk = result.data?.asks?.[0] ? { price: Number(result.data.asks[0][0]), qty: Number(result.data.asks[0][1]) } : null;
  return {
    ok: true,
    source: "binance:futures_depth",
    symbol,
    lastUpdateId: result.data?.lastUpdateId,
    bestBid,
    bestAsk,
    spread: bestBid && bestAsk ? bestAsk.price - bestBid.price : null,
    bids: result.data?.bids || [],
    asks: result.data?.asks || []
  };
}

function classifyFunding(rate) {
  if (!Number.isFinite(rate)) return "unknown";
  if (rate >= 0.0004) return "dangerously_positive"; // +0.04%
  if (rate >= 0.0001) return "positive";
  if (rate <= -0.0001) return "negative";
  return "neutral";
}

export async function getBtcMarketContext({ symbol = "BTCUSDT", includeOrderBook = false } = {}) {
  const [funding, openInterest, premium, ticker, orderBook] = await Promise.all([
    getFundingRate(symbol),
    getOpenInterest(symbol),
    getPremiumIndex(symbol),
    getTicker24h(symbol),
    includeOrderBook ? getOrderBook(symbol, 50) : Promise.resolve(null)
  ]);
  const fundingRate = funding.latest?.fundingRate ?? premium.lastFundingRate;
  return {
    ok: [funding, openInterest, premium, ticker].some((x) => x?.ok),
    source: "binance_public_futures",
    symbol,
    funding,
    openInterest,
    premium,
    ticker,
    orderBook,
    interpretation: {
      fundingState: classifyFunding(fundingRate),
      fundingRate,
      notes: [
        classifyFunding(fundingRate) === "dangerously_positive" ? "Funding very positive: avoid late longs; watch for long squeeze risk." : null,
        classifyFunding(fundingRate) === "negative" ? "Funding negative: potential short squeeze if price structure turns bullish." : null,
        openInterest.ok ? "Open interest available; compare with price structure before decision." : "Open interest unavailable."
      ].filter(Boolean)
    }
  };
}
