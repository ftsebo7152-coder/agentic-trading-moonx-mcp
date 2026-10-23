import { config } from "../config.js";
import { fetchJson } from "../http.js";
import { todayRange } from "../dates.js";

const DEFAULT_SERIES = {
  us10y: "DGS10",
  fedFunds: "DFF",
  cpi: "CPIAUCSL",
  pce: "PCEPI",
  dollarBroad: "DTWEXBGS"
};

function latestValid(observations = []) {
  const clean = observations.filter((obs) => obs.value !== "." && obs.value !== null && obs.value !== undefined);
  const latest = clean.at(-1);
  if (!latest) return null;
  return { date: latest.date, value: Number(latest.value) };
}

function trend(observations = []) {
  const clean = observations.filter((obs) => obs.value !== ".").map((obs) => ({ date: obs.date, value: Number(obs.value) })).filter((obs) => Number.isFinite(obs.value));
  if (clean.length < 2) return { direction: "unknown", change: null };
  const latest = clean.at(-1);
  const previous = clean[Math.max(0, clean.length - 6)];
  const change = latest.value - previous.value;
  return { direction: change > 0 ? "rising" : change < 0 ? "falling" : "flat", change };
}

export async function getFredSeries(seriesId, { observationStart, observationEnd } = {}) {
  if (!config.fredApiKey) {
    return { ok: false, source: "fred", error: "missing_FRED_API_KEY", seriesId, observations: [] };
  }
  const range = todayRange({ daysBack: 45, daysForward: 0 });
  const url = new URL("https://api.stlouisfed.org/fred/series/observations");
  url.searchParams.set("series_id", seriesId);
  url.searchParams.set("api_key", config.fredApiKey);
  url.searchParams.set("file_type", "json");
  url.searchParams.set("observation_start", observationStart || range.start.minus({ days: 45 }).toISODate());
  url.searchParams.set("observation_end", observationEnd || range.to);

  const result = await fetchJson(url.toString(), {}, { source: `fred:${seriesId}`, cacheTtlSeconds: 900 });
  if (!result.ok) return { ...result, seriesId, observations: [] };
  const observations = result.data?.observations || [];
  return { ok: true, source: "fred", seriesId, latest: latestValid(observations), trend: trend(observations), observations };
}

export async function getFredMacroContext({ includeObservations = false } = {}) {
  const entries = await Promise.all(Object.entries(DEFAULT_SERIES).map(async ([key, id]) => [key, await getFredSeries(id)]));
  const series = Object.fromEntries(entries);
  const context = {
    ok: Object.values(series).some((s) => s.ok),
    source: "fred",
    series: Object.fromEntries(Object.entries(series).map(([key, value]) => [key, includeObservations ? value : { ok: value.ok, seriesId: value.seriesId, latest: value.latest, trend: value.trend, error: value.error || null }]))
  };
  return context;
}
