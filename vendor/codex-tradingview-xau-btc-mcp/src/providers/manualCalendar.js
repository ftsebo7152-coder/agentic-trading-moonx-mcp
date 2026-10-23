import { config, readJsonIfExists } from "../config.js";
import { normalizeEconomicEvent } from "./finnhub.js";

export function getManualCalendar({ timezone = config.timezone } = {}) {
  const rows = readJsonIfExists(config.manualCalendarPath, []);
  if (!Array.isArray(rows)) return { ok: false, source: "manual_calendar", error: "manual_calendar_not_array", events: [] };
  return {
    ok: true,
    source: "manual_calendar",
    events: rows.map((item) => ({ ...normalizeEconomicEvent(item, "manual", timezone), assets: item.assets || ["XAUUSD", "BTCUSD"], blackoutBeforeMinutes: item.blackoutBeforeMinutes, blackoutAfterMinutes: item.blackoutAfterMinutes }))
  };
}
