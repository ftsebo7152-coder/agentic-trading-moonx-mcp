import { config } from "../config.js";
import { fetchJson } from "../http.js";

const BASE = "https://api.coingecko.com/api/v3";

function headers() {
  return config.coingeckoApiKey
    ? { "x-cg-demo-api-key": config.coingeckoApiKey }
    : {};
}

function marketBiasFromChange(change24h) {
  if (!Number.isFinite(change24h)) return "unknown";
  if (change24h >= 3) return "strong_risk_on";
  if (change24h >= 1) return "risk_on";
  if (change24h <= -3) return "strong_risk_off";
  if (change24h <= -1) return "risk_off";
  return "neutral";
}

export async function getCoinGeckoBitcoinContext() {
  const url = new URL(`${BASE}/simple/price`);
  url.searchParams.set("ids", "bitcoin");
  url.searchParams.set("vs_currencies", "usd");
  url.searchParams.set("include_market_cap", "true");
  url.searchParams.set("include_24hr_vol", "true");
  url.searchParams.set("include_24hr_change", "true");
  url.searchParams.set("include_last_updated_at", "true");

  const result = await fetchJson(url.toString(), { headers: headers() }, { source: "coingecko:bitcoin_simple_price", cacheTtlSeconds: 60 });
  if (!result.ok) return { ...result, configured: Boolean(config.coingeckoApiKey), bitcoin: null };

  const row = result.data?.bitcoin || {};
  const change24h = Number(row.usd_24h_change);
  return {
    ok: true,
    source: "coingecko:bitcoin_simple_price",
    configured: Boolean(config.coingeckoApiKey),
    bitcoin: {
      priceUsd: Number(row.usd),
      marketCapUsd: Number(row.usd_market_cap),
      volume24hUsd: Number(row.usd_24h_vol),
      change24hPercent: change24h,
      lastUpdatedAt: row.last_updated_at ? new Date(Number(row.last_updated_at) * 1000).toISOString() : null
    },
    interpretation: {
      marketBias24h: marketBiasFromChange(change24h),
      note: "CoinGecko is used as BTC spot/market context only, not as a standalone trade signal."
    }
  };
}

