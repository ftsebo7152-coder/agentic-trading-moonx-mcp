"""Point-in-time macro context. Missing calendar coverage blocks new entries."""
from dataclasses import dataclass
from datetime import timedelta
from .models import utc, TradingError


@dataclass(frozen=True)
class Observation:
    name: str
    value: float
    source: str
    economic_date: str
    published_at: str
    available_at: str
    fetched_at: str
    confidence: float

    def __post_init__(self):
        if not self.source or not 0<=self.confidence<=1:
            raise TradingError("source and bounded confidence required")
        if utc(self.available_at)<utc(self.published_at):
            raise TradingError("availability precedes publication")


def context_at(observations,events,now,*,calendar_asof=None,coverage_until=None,max_age_seconds=86400,before_minutes=30,after_minutes=30,symbol="BTC"):
    now=utc(now)
    eligible=[];missing=[]
    for row in observations:
        obs=row if isinstance(row,Observation) else Observation(**row)
        age=(now-utc(obs.available_at)).total_seconds()
        if 0<=age<=max_age_seconds and utc(obs.fetched_at)<=now:
            eligible.append(obs)
        else: missing.append(obs.name)
    known=(calendar_asof is not None and coverage_until is not None and
           0<=(now-utc(calendar_asof)).total_seconds()<=max_age_seconds and utc(coverage_until)>=now)
    active=[]
    for event in events:
        if utc(event["available_at"])>now: continue
        if event.get("symbols") and symbol not in event["symbols"]: continue
        when=utc(event["time"])
        if event.get("impact")=="high" and when-timedelta(minutes=before_minutes)<=now<=when+timedelta(minutes=after_minutes):
            active.append(event)
    return {"observations":eligible,"missing_or_stale":missing,"calendar_coverage_known":known,
            "blackout":bool(active) or not known,"events":active,
            "status":"OBSERVED" if eligible else "INSUFFICIENT_DATA",
            "bias":"UNCLASSIFIED","probability":None,
            "note":"Context filter only. Untrusted headlines cannot change risk limits or execution permissions."}
