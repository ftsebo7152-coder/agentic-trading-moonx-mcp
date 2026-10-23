"""Resolve the current CMC universe; never turn a ranking into broker permissions."""
from collections import Counter
from .market_data import CoinMarketCapUniverse
from .models import Mode, TradingError

PINNED_SLUGS = {
    "BTC":"bitcoin", "ETH":"ethereum", "SOL":"solana", "INJ":"injective",
    "TRX":"tron", "PUMP":"pump-fun", "XRP":"xrp", "BNB":"bnb",
    "HYPE":"hyperliquid", "UNI":"uniswap", "AVAX":"avalanche",
    "AAVE":"aave", "POL":"polygon-ecosystem-token", "ALGO":"algorand",
}


def resolve_universe(settings, store, now, provider=None):
    result={"requested":settings.universe, "status":"STATIC", "symbols":list(settings.watchlist),
            "asof":now, "assets":[], "excluded":{}, "identities":{},
            "entered":[], "exited":[], "broker_availability":"UNVERIFIED"}
    if settings.universe != "cmc_top100":return result
    if settings.mode != Mode.PAPER:
        result.update(status="HISTORICAL_UNIVERSE_REQUIRED", error="LIVE_RANKING_DISABLED_FOR_HISTORICAL_RUN")
        return result
    try:
        snapshot=(provider or CoinMarketCapUniverse()).top100(store,now)
    except (TradingError,ValueError,KeyError,TypeError):
        # No cached ranking is silently promoted to a current Top 100.
        result.update(status="FALLBACK_PINNED_ONLY", error="CMC_UNAVAILABLE_OR_INVALID")
        return result
    rows=snapshot["assets"]
    result.update(status="CMC_TOP100_PLUS_PINNED", assets=rows,
                  entered=snapshot["entered"], exited=snapshot["exited"])
    counts=Counter(r["symbol"] for r in rows)
    for row in rows:
        symbol=row["symbol"]
        if symbol not in result["symbols"]:result["symbols"].append(symbol)
        if (counts[symbol]>1 or symbol=="HOOD" or
                (symbol in PINNED_SLUGS and row["slug"]!=PINNED_SLUGS[symbol])):
            result["excluded"][symbol]="AMBIGUOUS_CMC_IDENTITY"
        elif row["opportunity_excluded"]:
            result["excluded"][symbol]="STABLECOIN_RESEARCH_ONLY"
        else:
            result["identities"][symbol]={"cmc_id":row["id"],"cmc_slug":row["slug"]}
    return result


def identity_error(symbol, universe, supplied):
    expected=universe["identities"].get(symbol)
    if expected:
        if not isinstance(supplied,dict) or supplied.get("cmc_id")!=expected["cmc_id"]:
            return "CMC_IDENTITY_UNVERIFIED"
    elif symbol=="HOOD":
        if not isinstance(supplied,dict) or any(supplied.get(k)!=v for k,v in
                {"asset_class":"equity","exchange":"NASDAQ","symbol":"HOOD"}.items()):
            return "HOOD_EQUITY_IDENTITY_UNVERIFIED"
    elif symbol=="PUMP" or universe["requested"]=="cmc_top100":
        slug=PINNED_SLUGS.get(symbol)
        if not slug or not isinstance(supplied,dict) or supplied.get("cmc_slug")!=slug:
            return "PINNED_IDENTITY_UNVERIFIED"
    return None
