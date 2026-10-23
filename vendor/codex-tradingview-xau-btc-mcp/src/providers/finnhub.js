import { config } from "../config.js";
import { fetchJson } from "../http.js";
import { todayRange, parseEventTime } from "../dates.js";

const HIGH_KEYWORDS = [
  "nonfarm", "nfp", "cpi", "core cpi", "pce", "core pce", "fomc", "fed interest rate",
  "interest rate decision", "powell", "unemployment rate", "average hourly earnings", "ppi",
  "retail sales", "ism", "gdp", "consumer confidence", "jobless claims"
];

export function inferImpact(eventName = "", rawImpact = "") {
  const impactText = String(rawImpact || "").toLowerCase();
  const name = String(eventName || "").toLowerCase();
  if (["high", "red", "3"].includes(impactText)) return "high";
  if (["medium", "orange", "2"].includes(impactText)) return "medium";
  if (["low", "yellow", "1"].includes(impactText)) return "low";
  if (HIGH_KEYWORDS.some((keyword) => name.includes(keyword))) return "high";
  if (/fed|ecb|boe|boj|inflation|employment|jobs|rate|minutes/.test(name)) return "medium";
  return "unknown";
}

export function normalizeEconomicEvent(raw, source = "finnhub", timezone = config.timezone) {
  const event = raw.event || raw.name || raw.title || raw.indicator || raw.release || "Unknown event";
  const time = raw.time || raw.datetime || raw.date || raw.period || raw.timestamp || raw.release_time;
  const dt = parseEventTime(time, timezone);
  const impact = inferImpact(event, raw.impact || raw.importance || raw.priority);
  return {
    source,
    time: dt ? dt.toISO() : time || null,
    date: dt ? dt.toISODate() : raw.date || null,
    country: raw.country || raw.region || raw.ccy || null,
    currency: raw.currency || raw.ccy || null,
    event,
    impact,
    actual: raw.actual ?? raw.value ?? null,
    forecast: raw.estimate ?? raw.forecast ?? raw.consensus ?? null,
    previous: raw.prev ?? raw.previous ?? null,
    unit: raw.unit || null,
    raw
  };
}

export async function getFinnhubEconomicCalendar({ from, to, timezone = config.timezone } = {}) {
  if (!config.finnhubApiKey) {
    return { ok: false, source: "finnhub", error: "missing_FINNHUB_API_KEY", events: [] };
  }
  const range = todayRange({ timezone, daysForward: 1 });
  const fromDate = from || range.from;
  const toDate = to || range.to;
  const url = new URL("https://finnhub.io/api/v1/calendar/economic");
  url.searchParams.set("from", fromDate);
  url.searchParams.set("to", toDate);
  url.searchParams.set("token", config.finnhubApiKey);

  const result = await fetchJson(url.toString(), {}, { source: "finnhub" });
  if (!result.ok) return { ...result, events: [] };
  const list = result.data?.economicCalendar || result.data?.calendar || result.data?.events || [];
  const events = Array.isArray(list) ? list.map((item) => normalizeEconomicEvent(item, "finnhub", timezone)) : [];
  return { ok: true, source: "finnhub", from: fromDate, to: toDate, events };
}
