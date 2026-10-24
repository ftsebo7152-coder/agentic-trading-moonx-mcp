"""Persistent SQLite worker fencing, replay-safe cycles and independent minute supervision."""
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import asyncio,json,os,signal,threading,time
from ..models import TradingError,now_utc,utc,dumps,fingerprint
from ..risk import IndependentRiskEngine
from ..enhancements.cli import write_json
from ..enhancements.feeds import FeedClient
from .engine import AutonomousPaperEngine
from .collection import collect_public,collect_moonx,merge_bundles,empty_bundle,public_series


class RuntimeLease:
    def __init__(self,store,account,seconds=180):
        if store.postgres:raise TradingError('AUTONOMY_SQLITE_ONLY_UNTIL_POSTGRES_QUALIFICATION')
        if not 30<=seconds<=1800:raise TradingError('INVALID_RUNTIME_LEASE')
        self.store,self.resource,self.seconds,self.token=store,'PAPER:'+account,seconds,str(uuid4())
        with store.transaction() as tx:
            tx.execute('CREATE TABLE IF NOT EXISTS autonomy_leases (resource TEXT PRIMARY KEY, token TEXT NOT NULL, expires TEXT NOT NULL, heartbeat TEXT NOT NULL)')
            tx.execute('CREATE TABLE IF NOT EXISTS autonomy_cycles (id TEXT PRIMARY KEY, account TEXT NOT NULL, status TEXT NOT NULL, payload TEXT)')

    def acquire(self,now):
        with self.store.transaction() as tx:
            row=tx.execute('SELECT * FROM autonomy_leases WHERE resource=?',(self.resource,)).fetchone()
            if row and utc(row['expires'])>utc(now):raise TradingError('PAPER_ACCOUNT_WORKER_ALREADY_RUNNING')
            tx.execute('INSERT INTO autonomy_leases(resource,token,expires,heartbeat) VALUES(?,?,?,?) ON CONFLICT(resource) DO UPDATE SET token=excluded.token,expires=excluded.expires,heartbeat=excluded.heartbeat',
                       (self.resource,self.token,(utc(now)+timedelta(seconds=self.seconds)).isoformat(),utc(now).isoformat()))

    def renew(self,now):
        with self.store.transaction() as tx:
            row=tx.execute('SELECT * FROM autonomy_leases WHERE resource=?',(self.resource,)).fetchone()
            if not row or row['token']!=self.token or utc(row['expires'])<=utc(now):raise TradingError('PAPER_RUNTIME_LEASE_LOST')
            tx.execute('UPDATE autonomy_leases SET expires=?,heartbeat=? WHERE resource=? AND token=?',
                       ((utc(now)+timedelta(seconds=self.seconds)).isoformat(),utc(now).isoformat(),self.resource,self.token))

    def valid(self,now):
        # This reader is also used inside a PaperBroker BEGIN IMMEDIATE transaction.
        conn=self.store.connect()
        try:row=conn.execute('SELECT token,expires FROM autonomy_leases WHERE resource=?',(self.resource,)).fetchone()
        finally:conn.close()
        return bool(row and row['token']==self.token and utc(row['expires'])>utc(now))

    def release(self):
        with self.store.transaction() as tx:tx.execute('DELETE FROM autonomy_leases WHERE resource=? AND token=?',(self.resource,self.token))


class FencedRisk(IndependentRiskEngine):
    def __init__(self,original,lease,clock=now_utc):
        super().__init__(original.limits,original.costs,original.timezone);self.lease,self.clock=lease,clock

    def evaluate(self,*args,**kwargs):
        result=super().evaluate(*args,**kwargs)
        if not self.lease.valid(self.clock()):
            result['status']='BLOCK';result['reasons'].append('PAPER_RUNTIME_LEASE_LOST')
        return result


class HealthLog:
    def __init__(self,store,account):
        self.store,self.account=store,account
        with store.transaction() as tx:tx.execute('CREATE TABLE IF NOT EXISTS autonomy_health (account TEXT NOT NULL,reason TEXT NOT NULL,active INTEGER NOT NULL,last_at TEXT NOT NULL,PRIMARY KEY(account,reason))')

    def incident(self,reason,now=None):
        now=utc(now) if now else now_utc()
        with self.store.transaction(self.account) as tx:
            old=tx.execute('SELECT active FROM autonomy_health WHERE account=? AND reason=?',(self.account,reason)).fetchone()
            tx.execute('INSERT INTO autonomy_health(account,reason,active,last_at) VALUES(?,?,1,?) ON CONFLICT(account,reason) DO UPDATE SET active=1,last_at=excluded.last_at',(self.account,reason,now.isoformat()))
            if not old or not old['active']:tx.event(self.account,'AUTONOMY_INCIDENT',{'reason':reason,'new_entries':'BLOCKED'},now,notify=True)

    def resolve(self,reason,now=None):
        now=utc(now) if now else now_utc()
        with self.store.transaction(self.account) as tx:
            old=tx.execute('SELECT active FROM autonomy_health WHERE account=? AND reason=?',(self.account,reason)).fetchone()
            if old and old['active']:
                tx.execute('UPDATE autonomy_health SET active=0,last_at=? WHERE account=? AND reason=?',(now.isoformat(),self.account,reason))
                tx.event(self.account,'AUTONOMY_RECOVERY',{'reason':reason},now,notify=True)


def run_cycle(engine,bundle,now,*,lease=None,clock=now_utc):
    if lease and not lease.valid(clock()):raise TradingError('PAPER_RUNTIME_LEASE_LOST')
    # Protection always runs, even when the entry cycle was completed before restart.
    protection=engine.protect(bundle,now)
    identity=fingerprint({'account':engine.settings.account,'policy':asdict(engine.policy),
                          'bars':{s:rows[-1]['time'] if isinstance(rows[-1],dict) else rows[-1].time for s,rows in bundle.get('markets',{}).items() if rows}})
    with engine.store.transaction() as tx:
        row=tx.execute('SELECT * FROM autonomy_cycles WHERE id=?',(identity,)).fetchone()
        if row and row['status']=='DONE':
            return {'status':'ALREADY_PROCESSED','cycle_id':identity,'protection':protection,'previous_run':json.loads(row['payload'])['run_id']}
        tx.execute("INSERT INTO autonomy_cycles(id,account,status) VALUES(?,?,'RUNNING') ON CONFLICT(id) DO NOTHING",(identity,engine.settings.account))
    original=engine.paper.risk
    if lease:
        engine.paper.risk=FencedRisk(original,lease,clock);engine.paper.runtime_token=lease.token
    try:report=engine.scan(bundle,now,universe=bundle.get('collection',{}).get('universe'),protection=protection)
    finally:
        engine.paper.risk=original
        if lease:del engine.paper.runtime_token
    with engine.store.transaction() as tx:tx.execute("UPDATE autonomy_cycles SET status='DONE',payload=? WHERE id=?",(dumps(report),identity))
    return {**report,'cycle_id':identity,'replay_policy':'Paper signal IDs are unique across retries; never used for remote orders.'}


def load_context(path):return json.loads(Path(path).read_text(encoding='utf8')) if path else {}


def configured_moonx_url():
    """Use the user's existing private connection without exporting or logging its URL."""
    if os.environ.get('MOONX_MCP_URL'):return os.environ['MOONX_MCP_URL']
    import tomllib
    path=Path.home()/'.codex/config.toml'
    try:return tomllib.loads(path.read_text(encoding='utf8')).get('mcp_servers',{}).get('moonx',{}).get('url')
    except (OSError,ValueError,AttributeError):return None


def collect(settings,policy,store,source,now,*,context=None,monitor_symbols=(),symbols=None):
    if source not in ('public','moonx','hybrid','file'):raise TradingError('UNKNOWN_COLLECTION_SOURCE')
    bundle=empty_bundle(now,context)
    if source=='file':
        external=(context or {}).get('external_data')
        if not isinstance(external,dict):raise TradingError('EXTERNAL_DATA_BUNDLE_REQUIRED')
        for name in ('markets','higher_markets','monitor_markets','market_metadata','asset_identities'):
            bundle[name]=external.get(name,{})
        return bundle
    if source in ('public','hybrid'):
        bundle=collect_public(settings,policy,store,now,context=context,monitor_symbols=monitor_symbols,symbols=symbols)
    if source in ('moonx','hybrid'):
        from ..remote_mcp import moonx_session
        url=configured_moonx_url()
        candidates=[s for s in (symbols or settings.watchlist) if source=='moonx' or policy.asset_class(s)!='crypto']
        if candidates:
            if not url:
                bundle['collection']['failures']['moonx']='PRIVATE_MOONX_MCP_URL_REQUIRED'
            else:
                async def read():
                    async with moonx_session(url,write_enabled=False) as broker:
                        return await collect_moonx(settings,policy,now,broker,context=context,symbols=candidates,
                                                  monitor_symbols=[s for s in monitor_symbols if source=='moonx' or policy.asset_class(s)!='crypto'])
                try:merge_bundles(bundle,asyncio.run(read()))
                except TradingError:bundle['collection']['failures']['moonx']='MOONX_READ_SESSION_UNAVAILABLE'
    bundle['collection']['completed_at']=now_utc()
    return bundle


def worker(settings,policy,store,*,source='public',context_path=None,bundle_path='state/autonomous-latest.json',once=False,monitor_seconds=15,refresh_seconds=60,costs=None):
    if min(monitor_seconds,refresh_seconds)<5:raise TradingError('WORKER_INTERVAL_TOO_SMALL')
    from ..risk import Costs
    engine=AutonomousPaperEngine(settings,policy,store,costs=costs or Costs());lease=RuntimeLease(store,settings.account)
    lease.acquire(now_utc());stopping=threading.Event();shared={'bundle':empty_bundle(now_utc()),'monitor_error':False};lock=threading.Lock()
    health=HealthLog(store,settings.account);incident=health.incident
    def monitor():
        while not stopping.is_set():
            try:
                lease.renew(now_utc())
                with store.transaction(settings.account) as tx:opened=tx.positions(settings.account)
                if opened:
                    # Dedicated refresh is independent of the longer universe collection.
                    try:
                        context=load_context(context_path);health.resolve('CONTEXT_UNAVAILABLE_MONITOR_ONLY')
                    except (OSError,ValueError):
                        context={};incident('CONTEXT_UNAVAILABLE_MONITOR_ONLY')
                    symbols=[p['symbol'] for p in opened]
                    sample=empty_bundle(now_utc(),context)
                    public_symbols=[s for s in symbols if source in ('public','hybrid') and policy.asset_class(s)=='crypto']
                    client=FeedClient(store,budget=max(1,len(public_symbols)*2))
                    for symbol in public_symbols:
                        with lock:provider=shared['bundle'].get('market_metadata',{}).get(symbol,{}).get('source')
                        sample['monitor_markets'][symbol]=public_series(client,symbol,'1m',now_utc(),provider=provider)['bars']
                    remaining=[s for s in symbols if s not in public_symbols]
                    if source=='file':sample['monitor_markets']=context.get('external_data',{}).get('monitor_markets',{})
                    if remaining and source in ('moonx','hybrid'):
                        # Reuses the read-only MCP path; position protection requires only minute bars.
                        other=collect(settings,policy,store,'moonx',now_utc(),context=context,monitor_symbols=remaining,symbols=remaining)
                        sample['monitor_markets'].update(other['monitor_markets'])
                    outcome=engine.protect(sample,now_utc())
                    with lock:shared['monitor_error']=bool(outcome['issues'])
                    if outcome['issues']:incident('MINUTE_MONITOR_COVERAGE_INCOMPLETE')
                    else:
                        health.resolve('MINUTE_MONITOR_COVERAGE_INCOMPLETE');health.resolve('MINUTE_MONITOR_OR_LEASE_FAILED')
                else:
                    outcome=engine.protect(empty_bundle(now_utc()),now_utc())
                    with lock:shared['monitor_error']=bool(outcome['issues'])
            except Exception:
                with lock:shared['monitor_error']=True
                incident('MINUTE_MONITOR_OR_LEASE_FAILED')
            stopping.wait(monitor_seconds)
    thread=None
    if not once:
        for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stopping.set())
        thread=threading.Thread(target=monitor,name='paper-minute-supervisor',daemon=True);thread.start()
    try:
        while not stopping.is_set():
            lease.renew(now_utc())
            try:
                context=load_context(context_path)
                with store.transaction(settings.account) as tx:opened=[p['symbol'] for p in tx.positions(settings.account)]
                bundle=collect(settings,policy,store,source,now_utc(),context=context,monitor_symbols=opened)
                write_json(bundle_path,bundle)
                with lock:shared['bundle']=bundle;monitor_error=shared['monitor_error']
                if monitor_error:
                    report={'status':'NO_TRADE','reason':'INDEPENDENT_MONITOR_UNHEALTHY','protection':engine.protect(bundle,now_utc())}
                else:report=run_cycle(engine,bundle,now_utc(),lease=lease)
                health.resolve('COLLECTION_OR_PAPER_CYCLE_FAILED')
                print(dumps(report),flush=True)
            except Exception:
                incident('COLLECTION_OR_PAPER_CYCLE_FAILED')
                if once:raise TradingError('AUTONOMOUS_ONCE_FAILED') from None
            if once:break
            stopping.wait(refresh_seconds)
    finally:
        stopping.set()
        if thread:thread.join(timeout=20)
        lease.release()


def runtime_status(store,account,now):
    RuntimeLease(store,account)
    HealthLog(store,account)
    with store.transaction() as tx:
        row=tx.execute('SELECT * FROM autonomy_leases WHERE resource=?',('PAPER:'+account,)).fetchone()
        cycles=tx.execute('SELECT id,status FROM autonomy_cycles WHERE account=? ORDER BY rowid DESC LIMIT 5',(account,)).fetchall()
        health=tx.execute('SELECT reason,active,last_at FROM autonomy_health WHERE account=?',(account,)).fetchall()
    return {'account':account,'worker_lease_active':bool(row and utc(row['expires'])>utc(now)),
            'heartbeat':row['heartbeat'] if row else None,'recent_cycles':[dict(r) for r in cycles],
            'positions':store.report(account)['positions'],'health':[dict(r) for r in health],'environment':'LOCAL_PAPER_ONLY'}
