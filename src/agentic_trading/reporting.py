from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo
from .models import utc,D,TradingError
from .quantitative import performance


def performance_report(store,account,now,*,period="all",group_by="symbol",timezone="Africa/Lagos",reference_capital="1250"):
    if group_by not in ("symbol","strategy","platform","regime","mode") or period not in ("all","day","week","month"):
        raise TradingError("unsupported reporting dimension")
    now=utc(now);local=now.astimezone(ZoneInfo(timezone));day=local.date()
    report=store.report(account);groups=defaultdict(list)
    for p in report["positions"]:
        if p["status"]!="CLOSED":continue
        when=utc(p["closed_at"]).astimezone(ZoneInfo(timezone))
        if when>local:continue
        if period=="day" and when.date()!=day:continue
        if period=="week" and when.date()<day-timedelta(days=day.weekday()):continue
        if period=="month" and (when.year,when.month)!=(local.year,local.month):continue
        value=p["plan"]["strategy"] if group_by=="strategy" else p.get(group_by,"UNRECORDED")
        # Mode is always part of the key: no accidental mixing of live and simulated results.
        groups[(p["mode"],value)].append(p)
    return {"account":account,"period":period,"group_by":group_by,"asof":now,"groups":[
        {"mode":mode,"group":key,"metrics":performance([p["net_pnl"] for p in positions],float(D(reference_capital))),
         "fees":sum(D(p["fees"]) for p in positions),"positions":len(positions)}
        for (mode,key),positions in sorted(groups.items())],
        "limitation":"Capital-normalized metrics use the default reference capital until account cash-flow history is configured."}
