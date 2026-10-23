from copy import deepcopy
from dataclasses import asdict,replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib,hmac,json,os,unittest
from agentic_trading.live import LiveExecution,approval_id
from agentic_trading.models import D,TakeProfit,TradingError,dumps,fingerprint
from agentic_trading.storage import Store
from agentic_trading.remote_mcp import SDKMCPTransport
from tests.test_engine import NOW,SPEC,plan,immediate


class Transport:
    def __init__(self):self.calls=[];self.positions=[];self.history=[];self.timeout=False;self.protected=True
    async def list_tools(self):
        return [{'name':'open_futures_position','inputSchema':{'properties':dict.fromkeys(
            ['symbol','side','marginUsdt','leverage','marginMode','mode','stopLossPrice','takeProfitPrice'],{})}}]
    async def call(self,name,args):
        self.calls.append((name,args))
        if name=='get_account_overview':return {'user':{'id':'test-account'},'unifiedBalance':{'availableFor':{'futures':'1250'}}}
        if name=='get_price':return {'price':'100'}
        if name=='list_futures_positions':return {'positions':deepcopy(self.positions)}
        if name in ('list_forex_positions',):return {'positions':[]}
        if name in ('list_futures_orders','list_forex_orders'):return {'orders':[]}
        if name=='open_futures_position':
            self.positions=[{'id':'p1','symbol':'BTC','side':'long','entryPrice':'100','quantity':'1'}]
            if self.timeout:raise TimeoutError('private_url_must_not_escape')
            return {'ok':True}
        if name=='list_futures_tp_sl_orders':
            return {'orders':[{'positionId':'p1','type':kind,'price':price} for kind,price in [('stop_loss','98'),('take_profit','104')]] if self.protected else []}
        if name=='get_futures_trade_history':return {'trades':self.history}
        if name=='close_futures_position':
            self.positions=[];self.history=[{'positionId':'p1','status':'closed','netPnl':'-2.5','closedAt':NOW.isoformat()}]
            return {'ok':True}
        raise AssertionError(name)


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'live.sqlite');self.transport=Transport()
        root=Path(__file__).resolve().parents[1]
        self.config=json.loads((root/'configs/live-moonx.example.json').read_text())
        self.config.update(enabled=True,schema_qualified=True,remote_account_id='test-account')
        p=replace(plan(),take_profits=(TakeProfit(D(104),D(1)),))
        body={'symbol':'BTC','strategy':p.strategy,'stage':'PAPER_VALIDATED','admitted':True,
              'artifact_hash':'fixture-only','issued_at':NOW.isoformat(),'expires_at':(NOW+timedelta(hours=1)).isoformat()}
        body['signature']=hmac.new(b'test-key',dumps(body).encode(),hashlib.sha256).hexdigest()
        self.packet=json.loads(dumps({'plan':p,'instrument':SPEC,'context':{'asof':NOW,'blackout':False,'liquidity_ok':True},'evidence':body}))
        self.env=patch.dict(os.environ,{'TRADING_LIVE_ENABLED':'YES','TRADING_VALIDATION_HMAC_KEY':'test-key'})
        self.env.start();self.addCleanup(self.env.stop)
        self.engine=LiveExecution(self.config,self.store,self.transport)

    def submit(self):return immediate(self.engine.submit(self.packet,approval_id(self.config,self.packet),NOW))
    def writes(self):return [c for c in self.transport.calls if c[0] in SDKMCPTransport.WRITE_TOOLS]

    def test_protected_open_and_native_stop(self):
        result=self.submit();self.assertEqual(result['status'],'OPEN_PROTECTED')
        name,args=self.writes()[0]
        self.assertEqual(args['stopLossPrice'],98);self.assertEqual(args['marginMode'],'isolated')
        self.assertEqual(args['mode'],'futures')

    def test_disabled_no_write(self):
        self.config['enabled']=False
        with self.assertRaises(TradingError):self.submit()
        self.assertEqual(self.writes(),[])

    def test_environment_activation_required(self):
        with patch.dict(os.environ,{'TRADING_LIVE_ENABLED':''}),self.assertRaises(TradingError):self.submit()
        self.assertEqual(self.writes(),[])

    def test_exact_plan_approval(self):
        approval=approval_id(self.config,self.packet);self.packet['plan']['quantity']='2'
        with self.assertRaises(TradingError):immediate(self.engine.submit(self.packet,approval,NOW))
        self.assertEqual(self.writes(),[])

    def test_unqualified_schema_blocked(self):
        self.config['schema_qualified']=False
        with self.assertRaises(TradingError):self.submit()
        self.assertEqual(self.writes(),[])

    def test_unsigned_strategy_blocked(self):
        self.packet['evidence']={}
        with self.assertRaisesRegex(TradingError,'STRATEGY_NOT_VALIDATED'):self.submit()
        self.assertEqual(self.writes(),[])

    def test_risk_and_stale_context_blocked(self):
        self.packet['plan']['quantity']='100'
        with self.assertRaisesRegex(TradingError,'LIVE_RISK_BLOCK'):self.submit()
        self.packet['context']['asof']=(NOW-timedelta(minutes=2)).isoformat()
        with self.assertRaisesRegex(TradingError,'STALE'):self.submit()
        self.assertEqual(self.writes(),[])

    def test_wrong_account_and_kill_switch(self):
        self.config['remote_account_id']='another-account'
        with self.assertRaisesRegex(TradingError,'ACCOUNT_MISMATCH'):self.submit()
        self.config['remote_account_id']='test-account';self.store.halt('live-moonx')
        with self.assertRaisesRegex(TradingError,'KILL_SWITCH'):self.submit()
        self.assertEqual(self.writes(),[])

    def test_timeout_restart_reconcile_never_resubmits(self):
        self.transport.timeout=True;result=self.submit()
        self.assertEqual(result['status'],'RECONCILIATION_REQUIRED')
        new=LiveExecution(self.config,self.store,self.transport)
        with self.assertRaises(TradingError):self.submit()
        confirmed=immediate(new.reconcile(result['attempt'],NOW))
        self.assertEqual(confirmed['status'],'OPEN_PROTECTED');self.assertEqual(len(self.writes()),1)

    def test_missing_protection_cannot_be_reported_as_success(self):
        self.transport.protected=False
        self.assertEqual(self.submit()['status'],'RECONCILIATION_REQUIRED')

    def test_close_reconciles_pnl_once_and_survives_halt(self):
        opened=self.submit();attempt=opened['attempt'];self.store.halt('live-moonx')
        approval=fingerprint({'purpose':'CLOSE_LIVE_POSITION','attempt':attempt})
        closed=immediate(self.engine.close(attempt,approval,NOW))
        self.assertEqual(closed['status'],'CLOSED')
        immediate(self.engine.reconcile(attempt,NOW))
        with self.store.transaction('live-moonx') as tx:
            events=[e for e in tx.events('live-moonx') if e['kind']=='EXIT']
        self.assertEqual(len(events),1);self.assertEqual(D(events[0]['payload']['pnl']),D('-2.5'))

    def test_paper_transport_rejects_writes(self):
        with self.assertRaisesRegex(TradingError,'MCP_WRITE_TOOL_BLOCKED'):
            immediate(SDKMCPTransport(object()).call('open_futures_position',{}))

    def test_missing_native_protection_capability_blocks_before_send(self):
        async def missing():return []
        self.transport.list_tools=missing
        with self.assertRaisesRegex(TradingError,'NATIVE_PROTECTED_ENTRY_UNAVAILABLE'):self.submit()
        self.assertEqual(self.writes(),[])

    def test_live_sdk_allows_only_narrow_write_tools(self):
        class Session:
            async def call_tool(self,name,args):
                return type('Response',(),{'isError':False,'content':[type('Text',(),{'type':'text','text':'{"ok":true}'})()]})()
        sdk=SDKMCPTransport(Session(),write_enabled=True)
        self.assertEqual(immediate(sdk.call('open_futures_position',{})),{'ok':True})
        with self.assertRaises(TradingError):immediate(sdk.call('clear_futures_tp_sl',{}))

    def test_three_targets_and_remote_exposure_are_explicitly_blocked(self):
        original=deepcopy(self.packet['plan']['take_profits'])
        self.packet['plan']['take_profits']=[{'price':'104','fraction':'.5'},{'price':'106','fraction':'.5'}]
        with self.assertRaisesRegex(TradingError,'SINGLE_NATIVE_TARGET'):self.submit()
        self.packet['plan']['take_profits']=original
        self.transport.positions=[{'id':'existing'}]
        with self.assertRaisesRegex(TradingError,'ACCOUNT_MUST_BE_FLAT'):self.submit()
        self.assertEqual(self.writes(),[])
