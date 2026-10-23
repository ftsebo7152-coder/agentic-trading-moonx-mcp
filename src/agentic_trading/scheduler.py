"""Persistent worker. A scan interval is separate from position supervision."""
import signal
import time
from .models import now_utc,dumps
from .notifications import NotificationWorker,SMTPEmailSender
from .orchestrator import AgenticTradingOrchestrator


def worker(settings,store,bundle_path,*,once=False,send_email=False,monitor_seconds=15):
    from .cli import load_bundle
    engine=AgenticTradingOrchestrator(settings,store)
    running=True;next_scan=0.0
    def stop(signum,frame):
        nonlocal running
        running=False
    if not once:
        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    while running:
        now=now_utc()
        try:
            data,markets,specs=load_bundle(bundle_path)
            for symbol,bars in markets.items():
                for bar in bars:
                    if bar.time<=now:engine.paper.monitor(symbol,bar)
            if time.monotonic()>=next_scan:
                result=engine.run(markets,specs,now,macro=data.get("macro",{}),liquidity=data.get("liquidity",{}),validation=data.get("validation",{}))
                print(dumps(result),flush=True);next_scan=time.monotonic()+settings.scan_interval_minutes*60
            if send_email:
                NotificationWorker(store,SMTPEmailSender()).flush(now)
        except Exception:
            with store.transaction(settings.account) as tx:
                tx.event(settings.account,"WORKER_INCIDENT",{"reason":"INPUT_OR_INFRASTRUCTURE_FAILED","new_entries":"BLOCKED"},now,notify=True)
        if once:break
        # The input bundle must be atomically refreshed by a separate authenticated data collector.
        time.sleep(monitor_seconds)
