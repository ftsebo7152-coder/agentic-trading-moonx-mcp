import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import dotenv from "dotenv";

// Load .env from current working directory first, then from package root.
dotenv.config();
const packageRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
dotenv.config({ path: path.join(packageRoot, ".env"), override: false });

function numberEnv(name, fallback) {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const config = {
  packageRoot,
  timezone: process.env.TIMEZONE || "Europe/Paris",
  requestTimeoutMs: numberEnv("REQUEST_TIMEOUT_MS", 12000),
  cacheTtlSeconds: numberEnv("CACHE_TTL_SECONDS", 120),
  finnhubApiKey: process.env.FINNHUB_API_KEY || "",
  fredApiKey: process.env.FRED_API_KEY || "",
  coingeckoApiKey: process.env.COINGECKO_API_KEY || "",
  braveSearchApiKey: process.env.BRAVE_SEARCH_API_KEY || "",
  cryptoPanicApiKey: process.env.CRYPTOPANIC_API_KEY || "",
  manualCalendarPath: process.env.MANUAL_CALENDAR_PATH || "./data/manual_calendar.json",
  rssSourcesPath: process.env.RSS_SOURCES_PATH || "./data/rss_sources.json",
  blackoutBeforeMinutes: numberEnv("BLACKOUT_BEFORE_MINUTES", 15),
  blackoutAfterMinutes: numberEnv("BLACKOUT_AFTER_MINUTES", 15),
  fomcBlackoutBeforeMinutes: numberEnv("FOMC_BLACKOUT_BEFORE_MINUTES", 60),
  fomcBlackoutAfterMinutes: numberEnv("FOMC_BLACKOUT_AFTER_MINUTES", 45)
};

export function resolvePathMaybeRelative(filePath) {
  if (!filePath) return filePath;
  return path.isAbsolute(filePath) ? filePath : path.join(config.packageRoot, filePath);
}

export function readJsonIfExists(filePath, fallback) {
  try {
    const resolved = resolvePathMaybeRelative(filePath);
    if (!resolved || !fs.existsSync(resolved)) return fallback;
    return JSON.parse(fs.readFileSync(resolved, "utf8"));
  } catch (error) {
    return fallback;
  }
}

export function providerStatus() {
  return {
    finnhub: Boolean(config.finnhubApiKey),
    fred: Boolean(config.fredApiKey),
    coingecko: Boolean(config.coingeckoApiKey),
    braveSearch: Boolean(config.braveSearchApiKey),
    cryptoPanic: Boolean(config.cryptoPanicApiKey),
    rss: true,
    binancePublic: true,
    manualCalendar: Boolean(readJsonIfExists(config.manualCalendarPath, null))
  };
}
