import { config } from "../config.js";
import { fetchJson } from "../http.js";

export async function searchBraveNews({ query, count = 10, freshness = "pd" } = {}) {
  if (!config.braveSearchApiKey) {
    return { ok: false, source: "brave_news", error: "missing_BRAVE_SEARCH_API_KEY", results: [] };
  }
  const url = new URL("https://api.search.brave.com/res/v1/news/search");
  url.searchParams.set("q", query || "XAUUSD BTCUSD macro news");
  url.searchParams.set("count", String(Math.min(Math.max(Number(count) || 10, 1), 20)));
  if (freshness) url.searchParams.set("freshness", freshness);
  const result = await fetchJson(url.toString(), {
    headers: {
      "X-Subscription-Token": config.braveSearchApiKey,
      accept: "application/json"
    }
  }, { source: "brave_news", cacheTtlSeconds: 120 });
  if (!result.ok) return { ...result, results: [] };
  const rows = result.data?.results || [];
  return {
    ok: true,
    source: "brave_news",
    query,
    results: rows.map((item) => ({
      title: item.title,
      url: item.url,
      description: item.description,
      age: item.age,
      pageAge: item.page_age,
      source: item.meta_url?.hostname || item.source || null,
      thumbnail: item.thumbnail?.src || null
    }))
  };
}
