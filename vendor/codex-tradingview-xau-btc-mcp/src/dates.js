import { DateTime } from "luxon";
import { config } from "./config.js";

export function nowIso(timezone = config.timezone) {
  return DateTime.now().setZone(timezone).toISO();
}

export function todayRange({ timezone = config.timezone, daysForward = 1, daysBack = 0 } = {}) {
  const start = DateTime.now().setZone(timezone).minus({ days: daysBack }).startOf("day");
  const end = DateTime.now().setZone(timezone).plus({ days: daysForward }).endOf("day");
  return { start, end, from: start.toISODate(), to: end.toISODate() };
}

export function parseEventTime(value, timezone = config.timezone) {
  if (!value) return null;
  if (typeof value === "number") {
    // Finnhub sometimes returns seconds; JavaScript timestamps are ms.
    const ms = value < 10_000_000_000 ? value * 1000 : value;
    return DateTime.fromMillis(ms, { zone: "utc" }).setZone(timezone);
  }
  const text = String(value);
  let dt = DateTime.fromISO(text, { setZone: true });
  if (dt.isValid) return dt.setZone(timezone);
  dt = DateTime.fromSQL(text, { zone: timezone });
  if (dt.isValid) return dt;
  dt = DateTime.fromRFC2822(text, { setZone: true });
  if (dt.isValid) return dt.setZone(timezone);
  return null;
}

export function minutesBetween(a, b) {
  return Math.round(b.diff(a, "minutes").minutes);
}
