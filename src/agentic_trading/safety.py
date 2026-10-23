from .models import D, utc


class SafetySupervisor:
    def inspect(self,positions,now,*,data_time=None,maximum_age=3900,broker_reachable=True,broker_position_ids=None):
        issues=[]
        if not broker_reachable:issues.append("BROKER_UNREACHABLE")
        if data_time is None or not 0<=(utc(now)-utc(data_time)).total_seconds()<=maximum_age:issues.append("DATA_STALE_OR_UNKNOWN")
        ids=[p["id"] for p in positions]
        if len(ids)!=len(set(ids)):issues.append("DUPLICATE_POSITION")
        for p in positions:
            if p["status"]=="OPEN" and (not p.get("stop_loss") or D(p["stop_loss"])<=0):issues.append("MISSING_STOP")
            if p.get("mode") not in ("PAPER","LIVE"):issues.append("UNKNOWN_POSITION_ENVIRONMENT")
        if broker_position_ids is not None and set(ids)!=set(broker_position_ids):issues.append("RECONCILIATION_MISMATCH")
        return {"new_entries_allowed":not issues,"issues":issues,"continue_protective_management":True}
