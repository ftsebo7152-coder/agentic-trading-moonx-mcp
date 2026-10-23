import { DateTime } from "luxon";
import { config } from "../config.js";
import { parseEventTime, minutesBetween } from "../dates.js";

const HIGH_IMPACT_KEYWORDS = [
  "nfp", "nonfarm", "non-farm", "cpi", "core cpi", "pce", "core pce", "fomc", "powell",
  "interest rate", "rate decision", "fed funds", "unemployment", "average hourly earnings",
  "ppi", "retail sales", "ism manufacturing", "ism services", "gdp", "jobs report"
];

const ASSET_EVENT_FILTERS = {
  XAUUSD: ["us", "usd", "fed", "fomc", "cpi", "pce", "nfp", "powell", "geopolitic", "war", "gold"],
  BTCUSD: ["us", "usd", "fed", "fomc", "cpi", "pce", "nfp", "powell", "bitcoin", "btc", "crypto", "etf", "regulation"]
};

export function isHighImpactEvent(event = {}) {
  const impact = String(event.impact || event.importance || "").toLowerCase();
  const title = String(event.event || event.title || event.name || "").toLowerCase();
  if (["high", "red", "3"].includes(impact)) return true;
  return HIGH_IMPACT_KEYWORDS.some((keyword) => title.includes(keyword));
}

export function isRelevantForAsset(event = {}, asset = "XAUUSD") {
  const assetKey = String(asset || "").toUpperCase().replace("/", "");
  const filters = ASSET_EVENT_FILTERS[assetKey] || [];
  const text = `${event.country || ""} ${event.currency || ""} ${event.event || event.title || event.name || ""} ${(event.assets || []).join(" ")}`.toLowerCase();
  if (Array.isArray(event.assets) && event.assets.map((a) => String(a).toUpperCase().replace("/", "")).includes(assetKey)) return true;
  if (!filters.length) return true;
  return filters.some((word) => text.includes(word));
}

function eventBlackoutWindow(event) {
  const name = String(event.event || event.title || event.name || "").toLowerCase();
  const isFomc = /fomc|powell|rate decision|interest rate/.test(name);
  return {
    before: Number(event.blackoutBeforeMinutes ?? (isFomc ? config.fomcBlackoutBeforeMinutes : config.blackoutBeforeMinutes)),
    after: Number(event.blackoutAfterMinutes ?? (isFomc ? config.fomcBlackoutAfterMinutes : config.blackoutAfterMinutes))
  };
}

export function checkBlackout({ events = [], asset = "XAUUSD", now = null, timezone = config.timezone } = {}) {
  const nowDt = now ? parseEventTime(now, timezone) : DateTime.now().setZone(timezone);
  const relevant = events
    .filter((event) => isHighImpactEvent(event))
    .filter((event) => isRelevantForAsset(event, asset))
    .map((event) => {
      const eventTime = parseEventTime(event.time || event.datetime || event.date, timezone);
      if (!eventTime?.isValid) return null;
      const { before, after } = eventBlackoutWindow(event);
      const start = eventTime.minus({ minutes: before });
      const end = eventTime.plus({ minutes: after });
      const active = nowDt >= start && nowDt <= end;
      const minutesToEvent = minutesBetween(nowDt, eventTime);
      return { ...event, eventTime: eventTime.toISO(), blackoutStart: start.toISO(), blackoutEnd: end.toISO(), blackoutBeforeMinutes: before, blackoutAfterMinutes: after, active, minutesToEvent };
    })
    .filter(Boolean)
    .sort((a, b) => Math.abs(a.minutesToEvent) - Math.abs(b.minutesToEvent));

  const activeEvents = relevant.filter((event) => event.active);
  const upcoming = relevant.filter((event) => event.minutesToEvent > 0).sort((a, b) => a.minutesToEvent - b.minutesToEvent);
  return {
    asset,
    timezone,
    now: nowDt.toISO(),
    blackoutActive: activeEvents.length > 0,
    tradeAllowed: activeEvents.length === 0,
    activeEvents,
    nextHighImpactEvent: upcoming[0] || null,
    relevantHighImpactEvents: relevant,
    reason: activeEvents.length > 0
      ? `High-impact news blackout active: ${activeEvents.map((e) => e.event).join(", ")}`
      : upcoming[0]
        ? `No active blackout. Next high-impact event in ${upcoming[0].minutesToEvent} minutes: ${upcoming[0].event}`
        : "No relevant high-impact event found in the loaded calendar."
  };
}
