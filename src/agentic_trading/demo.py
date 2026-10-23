"""Explicit synthetic scenario exercising entries and three partial exits."""
from datetime import datetime,timedelta,timezone
from .models import Candle,D,Instrument,utc


def scenario():
    start=datetime(2026,10,1,tzinfo=timezone.utc)
    bars=[]
    for i in range(65):
        price=D("100")+D(i%3)/100
        bars.append(Candle(start+timedelta(hours=i),price,D("101"),D("99"),price,D("1000")))
    bars.extend([
        Candle(start+timedelta(hours=65),D("100"),D("102.2"),D("99.9"),D("102"),D("2000")),
        Candle(start+timedelta(hours=66),D("102"),D("102.8"),D("101.8"),D("102.5"),D("1600"))])
    now=bars[-1].time
    return {"bars":bars,"now":now,"spec":Instrument("BTC",specs_verified=True),
            "macro":{"synthetic":True,"calendar_asof":now.isoformat(),"coverage_until":(now+timedelta(days=1)).isoformat(),"events":[],
                     "observations":[{"name":"SYNTHETIC_CONTEXT","value":0,"source":"SYNTHETIC_FIXTURE",
                     "economic_date":now.date().isoformat(),"published_at":now.isoformat(),"available_at":now.isoformat(),"fetched_at":now.isoformat(),"confidence":1}]},
            "liquidity":{"BTC":{"source":"SYNTHETIC_FIXTURE","asof":now.isoformat(),"volume_24h":10_000_000,"depth_usd":1_000_000,"spread_bps":2}},
            "exit_bars":[Candle(now+timedelta(hours=i+1),D(o),D(h),D(l),D(c),D(2000))
                         for i,(o,h,l,c) in enumerate([("102.5","110","102.4","109.8"),("109.8","114","109.5","113.8"),("113.8","118","113.5","117")])]}
