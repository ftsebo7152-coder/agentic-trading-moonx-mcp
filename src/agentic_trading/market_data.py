"""Read-only official data providers, validated at their boundary."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .models import Candle, D, TradingError, utc, validate_candles


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise TradingError("unexpected provider redirect")


class PublicJSONClient:
    ALLOWED={"pro-api.coinmarketcap.com","api.stlouisfed.org","finnhub.io","cryptopanic.com","www.okx.com","api.bybit.com"}
    def get(self,url,headers=None):
        parsed=urlsplit(url)
        if parsed.scheme!="https" or parsed.hostname not in self.ALLOWED or parsed.username or parsed.password:
            raise TradingError("unapproved data origin")
        try:
            with build_opener(NoRedirect).open(Request(url,headers={"Accept":"application/json",**(headers or {})}),timeout=20) as response:
                raw=response.read(8_000_001)
            if len(raw)>8_000_000:raise TradingError("provider response too large")
            return json.loads(raw)
        except Exception:
            # Provider URLs can contain credentials. Never propagate them into logs.
            raise TradingError("DATA_PROVIDER_REQUEST_FAILED") from None


class FixtureProvider:
    def __init__(self,path):
        self.data=json.loads(Path(path).read_text(encoding="utf8"))
    def candles(self,symbol,now):
        bars=[Candle.from_dict(r) for r in self.data["markets"].get(symbol,[]) if utc(r["time"])<=utc(now)]
        validate_candles(bars)
        return bars


def moonx_candles(raw,interval_seconds,now):
    if raw.get("count")!=len(raw.get("candles",[])):
        raise TradingError("MCP candle count mismatch")
    out=[]
    for row in raw["candles"]:
        close_time=datetime.fromtimestamp(row["time"]/1000,timezone.utc)+timedelta(seconds=interval_seconds)
        if close_time<=utc(now):
            out.append(Candle(close_time,*(D(row[k]) for k in ("open","high","low","close","volume"))))
    validate_candles(out)
    return out


class CoinMarketCapUniverse:
    def __init__(self,client=None):self.client=client or PublicJSONClient()
    def top100(self,store,now):
        key=os.environ.get("CMC_API_KEY")
        if not key:raise TradingError("CMC_API_KEY_REQUIRED")
        url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?"+urlencode({"start":1,"limit":100,"sort":"market_cap","convert":"USD"})
        raw=self.client.get(url,{"X-CMC_PRO_API_KEY":key})
        if raw.get("status",{}).get("error_code",0)!=0 or len(raw.get("data",[]))!=100:
            raise TradingError("TOP100_RESPONSE_INCOMPLETE")
        rows=[{"id":r["id"],"symbol":r["symbol"],"name":r["name"],"slug":r["slug"],"rank":r["cmc_rank"],
               "tags":r.get("tags",[]),"quote":r["quote"]["USD"],"platform":r.get("platform"),
               "opportunity_excluded":"stablecoin" in r.get("tags",[])} for r in raw["data"]]
        if len({r["id"] for r in rows})!=100:raise TradingError("duplicate CMC IDs")
        if {r["rank"] for r in rows} != set(range(1,101)):
            raise TradingError("TOP100_RANKS_INVALID")
        with store.transaction() as tx:
            previous=tx.execute("SELECT payload FROM snapshots WHERE kind='CMC_TOP100' ORDER BY at DESC LIMIT 1").fetchone()
        previous_ids={r["id"] for r in json.loads(previous["payload"])["assets"]} if previous else set()
        current={r["id"] for r in rows}
        result={"source":"CoinMarketCap official API","asof":now,"assets":rows,"entered":sorted(current-previous_ids),"exited":sorted(previous_ids-current),
                "broker_availability":"UNVERIFIED","identity_note":"PUMP must be verified by CMC id/slug/platform; never match symbol alone."}
        store.snapshot("CMC_TOP100",result,now)
        return result


class FREDProvider:
    def __init__(self,client=None):self.client=client or PublicJSONClient()
    def observations(self,series_id,now):
        key=os.environ.get("FRED_API_KEY")
        if not key:raise TradingError("FRED_API_KEY_REQUIRED")
        raw=self.client.get("https://api.stlouisfed.org/fred/series/observations?"+urlencode({"series_id":series_id,"api_key":key,"file_type":"json","sort_order":"desc","limit":60}))
        # FRED daily series do not establish the exact intraday release/availability timestamp.
        return {"source":"FRED","series_id":series_id,"fetched_at":now,"observations":raw.get("observations",[]),
                "point_in_time_eligible":False,"limitation":"Supply ALFRED vintages/release availability before historical use."}


class FinnhubCalendarProvider:
    def __init__(self,client=None):self.client=client or PublicJSONClient()
    def events(self,start,end,now):
        key=os.environ.get("FINNHUB_API_KEY")
        if not key:raise TradingError("FINNHUB_API_KEY_REQUIRED")
        raw=self.client.get("https://finnhub.io/api/v1/calendar/economic?"+urlencode({"from":start,"to":end,"token":key}))
        if "economicCalendar" not in raw:raise TradingError("CALENDAR_SCHEMA_INVALID")
        return {"source":"Finnhub","fetched_at":now,"events":raw["economicCalendar"],"coverage_until":end,
                "limitation":"Normalize event timezone and availability before entry gating."}
