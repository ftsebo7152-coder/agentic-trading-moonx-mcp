import { config } from "../config.js";
import { fetchJson } from "../http.js";

export async function getCryptoPanicNews({ currencies = "BTC", filter = "important", publicOnly = true } = {}) {
  if (!config.cryptoPanicApiKey) {
    return { ok: false, source: "cryptopanic", error: "missing_CRYPTOPANIC_API_KEY", results: [] };
  }
  const url = new URL("https://cryptopanic.com/api/v1/posts/");
  url.searchParams.set("auth_token", config.cryptoPanicApiKey);
  url.searchParams.set("currencies", currencies);
  if (filter) url.searchParams.set("filter", filter);
  if (publicOnly) url.searchParams.set("public", "true");
  const result = await fetchJson(url.toString(), {}, { source: "cryptopanic", cacheTtlSeconds: 120 });
  if (!result.ok) return { ...result, results: [] };
  const rows = result.data?.results || [];
  return {
    ok: true,
    source: "cryptopanic",
    results: rows.map((item) => ({
      title: item.title,
      url: item.url,
      publishedAt: item.published_at,
      domain: item.domain,
      kind: item.kind,
      currencies: item.currencies,
      votes: item.votes
    }))
  };
}
