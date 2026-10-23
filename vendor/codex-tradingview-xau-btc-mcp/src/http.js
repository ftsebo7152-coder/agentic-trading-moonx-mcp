import { config } from "./config.js";

const cache = new Map();

function cacheKey(url, options = {}) {
  return JSON.stringify({ url, method: options.method || "GET", body: options.body || null });
}

export function clearCache() {
  cache.clear();
}

export async function fetchJson(url, options = {}, meta = {}) {
  const ttlMs = (meta.cacheTtlSeconds ?? config.cacheTtlSeconds) * 1000;
  const key = cacheKey(url, options);
  const cached = cache.get(key);
  if (cached && Date.now() - cached.time < ttlMs) return cached.value;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), meta.timeoutMs ?? config.requestTimeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "user-agent": "news-fundamentals-mcp/1.0",
        accept: "application/json",
        ...(options.headers || {})
      }
    });
    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }
    if (!response.ok) {
      return {
        ok: false,
        source: meta.source || "unknown",
        status: response.status,
        error: data?.error || data?.message || response.statusText,
        data
      };
    }
    const value = { ok: true, source: meta.source || "unknown", status: response.status, data };
    cache.set(key, { time: Date.now(), value });
    return value;
  } catch (error) {
    return {
      ok: false,
      source: meta.source || "unknown",
      error: error.name === "AbortError" ? "request_timeout" : error.message
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchText(url, options = {}, meta = {}) {
  const ttlMs = (meta.cacheTtlSeconds ?? config.cacheTtlSeconds) * 1000;
  const key = cacheKey(url, options);
  const cached = cache.get(key);
  if (cached && Date.now() - cached.time < ttlMs) return cached.value;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), meta.timeoutMs ?? config.requestTimeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "user-agent": "news-fundamentals-mcp/1.0",
        accept: "application/rss+xml, application/xml, text/xml, text/plain, */*",
        ...(options.headers || {})
      }
    });
    const text = await response.text();
    if (!response.ok) {
      return { ok: false, source: meta.source || "unknown", status: response.status, error: response.statusText, text };
    }
    const value = { ok: true, source: meta.source || "unknown", status: response.status, text };
    cache.set(key, { time: Date.now(), value });
    return value;
  } catch (error) {
    return {
      ok: false,
      source: meta.source || "unknown",
      error: error.name === "AbortError" ? "request_timeout" : error.message
    };
  } finally {
    clearTimeout(timeout);
  }
}
