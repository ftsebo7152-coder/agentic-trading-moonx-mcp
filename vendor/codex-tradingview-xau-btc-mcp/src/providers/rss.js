import { XMLParser } from "fast-xml-parser";
import { config, readJsonIfExists } from "../config.js";
import { fetchText } from "../http.js";

const parser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@_" });

function asArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function normalizeRssItem(item, feed) {
  const link = typeof item.link === "string" ? item.link : item.link?.href || item.guid || null;
  return {
    source: feed.name,
    trust: feed.trust || "unknown",
    title: item.title || item["media:title"] || "Untitled",
    url: link,
    publishedAt: item.pubDate || item.published || item.updated || item["dc:date"] || null,
    description: item.description || item.summary || null,
    assetTags: feed.assetTags || []
  };
}

export async function getRssHeadlines({ category = "macro", maxPerFeed = 5 } = {}) {
  const sources = readJsonIfExists(config.rssSourcesPath, {});
  const feeds = asArray(sources[category] || []).slice(0, 10);
  const results = [];
  const errors = [];
  for (const feed of feeds) {
    const response = await fetchText(feed.url, {}, { source: `rss:${feed.name}`, cacheTtlSeconds: 180 });
    if (!response.ok) {
      errors.push({ source: feed.name, error: response.error || response.status });
      continue;
    }
    try {
      const xml = parser.parse(response.text);
      const items = asArray(xml.rss?.channel?.item || xml.feed?.entry || []).slice(0, maxPerFeed);
      results.push(...items.map((item) => normalizeRssItem(item, feed)));
    } catch (error) {
      errors.push({ source: feed.name, error: error.message });
    }
  }
  return { ok: results.length > 0, source: "rss", category, results, errors };
}
