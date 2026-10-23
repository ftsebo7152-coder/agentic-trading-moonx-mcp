function headlineRiskScore(headlines = []) {
  const text = headlines.map((h) => `${h.title || ""} ${h.description || ""}`).join(" ").toLowerCase();
  const riskOffWords = ["war", "missile", "attack", "default", "crisis", "banking crisis", "inflation shock", "hawkish", "selloff", "sanctions"];
  const riskOnWords = ["dovish", "rate cut", "soft landing", "risk appetite", "etf inflow", "inflows", "stimulus", "ceasefire"];
  return {
    riskOffHits: riskOffWords.filter((word) => text.includes(word)),
    riskOnHits: riskOnWords.filter((word) => text.includes(word))
  };
}

function trendDirection(series) {
  return series?.trend?.direction || "unknown";
}

export function scoreFundamentals({ asset = "XAUUSD", macro = {}, btc = null, headlines = [], blackout = null } = {}) {
  const assetKey = String(asset).toUpperCase().replace("/", "");
  const reasons = [];
  let longScore = 0;
  let shortScore = 0;
  let confidence = 35;

  const fred = macro?.series || {};
  const us10y = trendDirection(fred.us10y);
  const dollar = trendDirection(fred.dollarBroad);
  const fedFunds = trendDirection(fred.fedFunds);
  const newsRisk = headlineRiskScore(headlines);

  if (blackout?.blackoutActive) {
    reasons.push("Blackout news actif: pas de nouveau trade avant stabilisation.");
    confidence += 15;
  }

  if (assetKey === "XAUUSD") {
    if (us10y === "rising") { shortScore += 2; reasons.push("US10Y rising: pressure on gold unless geopolitical hedge dominates."); }
    if (us10y === "falling") { longScore += 2; reasons.push("US10Y falling: supportive for gold."); }
    if (dollar === "rising") { shortScore += 2; reasons.push("Dollar broad index rising: usually negative for XAU/USD."); }
    if (dollar === "falling") { longScore += 2; reasons.push("Dollar broad index falling: supportive for XAU/USD."); }
    if (newsRisk.riskOffHits.length) { longScore += 1; reasons.push(`Risk-off/geopolitical words detected: ${newsRisk.riskOffHits.join(", ")}.`); }
  }

  if (assetKey === "BTCUSD") {
    if (dollar === "rising" || us10y === "rising") { shortScore += 2; reasons.push("Dollar/yields rising: tighter liquidity, usually negative for BTC."); }
    if (dollar === "falling" || us10y === "falling") { longScore += 2; reasons.push("Dollar/yields falling: easier liquidity, usually supportive for BTC."); }
    const fundingState = btc?.interpretation?.fundingState;
    const coingeckoBias = btc?.coingecko?.interpretation?.marketBias24h;
    if (fundingState === "dangerously_positive") { shortScore += 2; reasons.push("BTC funding very positive: avoid late longs; long squeeze risk."); }
    if (fundingState === "negative") { longScore += 1; reasons.push("BTC funding negative: possible short squeeze if structure confirms."); }
    if (coingeckoBias === "strong_risk_on") { longScore += 1; reasons.push("CoinGecko BTC 24h context strongly positive; avoid aggressive shorts without technical confirmation."); }
    if (coingeckoBias === "strong_risk_off") { shortScore += 1; reasons.push("CoinGecko BTC 24h context strongly negative; avoid aggressive longs without reversal confirmation."); }
    if (newsRisk.riskOnHits.some((x) => x.includes("etf") || x.includes("inflow"))) { longScore += 1; reasons.push("ETF/inflow positive language detected; avoid aggressive shorts without technical confirmation."); }
  }

  if (fedFunds === "rising") { shortScore += 1; reasons.push("Fed funds trend rising: restrictive context."); }
  if (fedFunds === "falling") { longScore += 1; reasons.push("Fed funds trend falling: liquidity support context."); }

  let bias = "neutral";
  const diff = longScore - shortScore;
  if (diff >= 2) bias = "long";
  if (diff <= -2) bias = "short";
  confidence = Math.min(90, Math.max(20, confidence + Math.abs(diff) * 8));

  const tradePermission = blackout?.blackoutActive
    ? { allowed: false, reason: blackout.reason }
    : { allowed: true, reason: "No active fundamental/news blackout. Technical setup and risk rules still required." };

  return {
    asset: assetKey,
    bias,
    confidence,
    scores: { longScore, shortScore, diff },
    tradePermission,
    reasons,
    caution: [
      "This is a context filter, not a signal by itself.",
      "Do not enter without the technical setup, SL, R:R >= 1:2, sizing and human validation in live mode."
    ]
  };
}
