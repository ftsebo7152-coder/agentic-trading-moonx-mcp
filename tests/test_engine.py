from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import asyncio
import hashlib
import hmac
import json
import math
import os
import unittest
from unittest.mock import patch

from agentic_trading.models import Candle,D,Instrument,Mode,TakeProfit,TradePlan,TradingError,dumps,floor_step,utc,validate_candles
from agentic_trading.config import RiskLimits,Settings
from agentic_trading.storage import Store
from agentic_trading.risk import Costs,IndependentRiskEngine,economics,size_position
from agentic_trading.paper import PaperBroker
from agentic_trading.indicators import sma,ema,rsi,atr,adx,bollinger,macd,vwap,summary
from agentic_trading.analysis import RangeBreakout,SetupScoringEngine,MarketRegimeClassifier,smc_features,volatility_rank
from agentic_trading.notifications import NotificationWorker,SMTPEmailSender
from agentic_trading.fundamentals import Observation,context_at
from agentic_trading.quantitative import performance,monte_carlo,calibration,walk_forward,bootstrap_mean_ci,QuantitativeValidationEngine
from agentic_trading.permissions import verify_evidence
from agentic_trading.brokers import MoonXBrokerAdapter,OKXBrokerAdapter,BybitBrokerAdapter
from agentic_trading.safety import SafetySupervisor
from agentic_trading.demo import scenario
from agentic_trading.orchestrator import AgenticTradingOrchestrator
from agentic_trading.market_data import PublicJSONClient,moonx_candles,CoinMarketCapUniverse

NOW=datetime(2026,10,23,12,tzinfo=timezone.utc)
SPEC=Instrument("BTC",specs_verified=True)

def plan(**changes):
    base=TradePlan("BTC","LONG",D(100),D(98),D(1),D(1),tuple(TakeProfit(D(p),D(f)) for p,f in [(104,".25"),(106,".35"),(108,".40")]),"range-breakout-v1",D(85),NOW,"signal", "unit fixture")
    return replace(base,**changes)

def bar(low=99,high=101,open=100,close=100,hours=1):
    return Candle(NOW+timedelta(hours=hours),D(open),D(high),D(low),D(close),D(1000))


def immediate(coroutine):
    """Run an immediate mock coroutine without opening OS event-loop sockets."""
    try:coroutine.send(None)
    except StopIteration as result:return result.value
    raise AssertionError("unit mock unexpectedly awaited IO")


class Models(unittest.TestCase):
    def test_decimal_rejects_nonfinite(self):
        for value in ["NaN","Infinity",float("nan"),True]:
            with self.subTest(value=value),self.assertRaises(TradingError):D(value)
    def test_timezone_required(self):
        with self.assertRaises(TradingError):utc("2026-10-23")
    def test_ohlc_consistency(self):
        with self.assertRaises(TradingError):bar(low=102)
    def test_zero_price(self):
        with self.assertRaises(TradingError):bar(open=0,low=0)
    def test_stop_side(self):
        with self.assertRaises(TradingError):plan(stop_loss=D(101))
    def test_short_stop_side(self):
        with self.assertRaises(TradingError):plan(side="SHORT")
    def test_target_fractions(self):
        with self.assertRaises(TradingError):plan(take_profits=(TakeProfit(104,".2"),))
    def test_target_order(self):
        with self.assertRaises(TradingError):plan(take_profits=(TakeProfit(108,".5"),TakeProfit(104,".5")))
    def test_roundtrip(self):self.assertEqual(plan(),TradePlan.from_dict(json.loads(dumps(plan()))))
    def test_floor_quantity(self):self.assertEqual(floor_step(D("1.239"),D(".01")),D("1.23"))
    def test_duplicate_candles(self):
        with self.assertRaises(TradingError):validate_candles([bar(),bar()])
    def test_invalid_limit(self):
        with self.assertRaises(TradingError):RiskLimits(max_trades_per_day=11)
    def test_live_mode_rejected(self):
        with self.assertRaises(TradingError):Settings(mode=Mode.LIVE_EXECUTION)
    def test_negative_cost(self):
        with self.assertRaises(TradingError):Costs(fee_bps=D(-1))


class Indicators(unittest.TestCase):
    def test_sma(self):self.assertEqual(sma([1.,2.,3.,4.],3),[None,None,2.,3.])
    def test_ema(self):self.assertEqual(ema([1.,2.,3.,4.],3),[None,None,2.,3.])
    def test_rsi_rising(self):self.assertEqual(rsi(list(range(20)))[-1],100)
    def test_rsi_falling(self):self.assertEqual(rsi(list(range(20,0,-1)))[-1],0)
    def test_rsi_flat(self):self.assertEqual(rsi([1.]*20)[-1],50)
    def test_atr_constant_range(self):self.assertEqual(atr([bar(hours=i) for i in range(30)])[-1],2.)
    def test_bollinger_constant(self):self.assertEqual(bollinger([5.]*20)[-1],{"middle":5.,"upper":5.,"lower":5.})
    def test_macd_constant(self):self.assertEqual(macd([5.]*50)[-1]["histogram"],0.)
    def test_adx_flat(self):self.assertEqual(adx([bar(hours=i) for i in range(40)])[-1],0.)
    def test_adx_warmup(self):self.assertTrue(all(v is None for v in adx([bar(hours=i) for i in range(20)])))
    def test_vwap(self):self.assertEqual(vwap([bar(),bar(hours=2)])[-1],100.)
    def test_vwap_no_volume(self):self.assertEqual(vwap([replace(bar(),volume=D(0))]),[None])
    def test_no_lookahead(self):
        bars=scenario()["bars"]
        self.assertEqual(ema([float(b.close) for b in bars],20)[:50],ema([float(b.close) for b in bars[:50]],20))
    def test_atr_gap(self):
        bars=[bar(),bar(open=105,high=106,low=104,close=105,hours=2)]
        self.assertEqual(atr(bars,1)[-1],6.)
    def test_summary_missing_200(self):self.assertIsNone(summary(scenario()["bars"])["ema_200"])


class Risk(unittest.TestCase):
    def evaluate(self,p=None,limits=None,account=None,positions=None,events=None,**context):
        return IndependentRiskEngine(limits or RiskLimits()).evaluate(p or plan(),SPEC,account or {"balance":"1250","halted":0},positions or [],events or [],NOW,strategy_validated=context.get("validated",True),blackout=context.get("blackout",False),liquidity_ok=context.get("liquid",True))
    def test_valid(self):self.assertEqual(self.evaluate()["status"],"PASS")
    def test_margin_risk_separate(self):
        eco=economics(plan(leverage=D(5)),SPEC)
        self.assertEqual(eco["margin"],20);self.assertEqual(eco["notional"],100);self.assertGreater(eco["net_stop_risk"],2)
    def test_score_not_probability(self):self.assertNotIn("probability",self.evaluate())
    def test_low_score(self):self.assertIn("SCORE_BELOW_THRESHOLD",self.evaluate(plan(score=D(66)))["reasons"])
    def test_stale(self):self.assertIn("STALE_OR_FUTURE_DATA",self.evaluate(plan(data_time=NOW-timedelta(hours=2)))["reasons"])
    def test_future(self):self.assertIn("STALE_OR_FUTURE_DATA",self.evaluate(plan(data_time=NOW+timedelta(seconds=1)))["reasons"])
    def test_blackout(self):self.assertIn("MACRO_BLACKOUT_OR_UNKNOWN",self.evaluate(blackout=True)["reasons"])
    def test_unvalidated(self):self.assertIn("STRATEGY_NOT_VALIDATED",self.evaluate(validated=False)["reasons"])
    def test_unknown_liquidity(self):self.assertIn("LIQUIDITY_UNKNOWN_OR_LOW",self.evaluate(liquid=False)["reasons"])
    def test_halt(self):self.assertIn("KILL_SWITCH",self.evaluate(account={"balance":"1250","halted":1})["reasons"])
    def test_leverage(self):self.assertIn("LEVERAGE_LIMIT",self.evaluate(plan(leverage=D(5)))["reasons"])
    def test_quantity_precision(self):self.assertIn("QUANTITY_PRECISION",self.evaluate(plan(quantity=D("1.00001")))["reasons"])
    def test_price_precision(self):self.assertIn("PRICE_PRECISION",self.evaluate(plan(entry=D("100.001")))["reasons"])
    def test_trade_risk(self):self.assertIn("TRADE_RISK_LIMIT",self.evaluate(plan(quantity=D(100)))["reasons"])
    def test_sizing_never_rounds_up(self):
        qty=size_position(10,100,98,SPEC)
        self.assertLessEqual(economics(plan(quantity=qty),SPEC)["net_stop_risk"],10)
    def test_daily_ceiling(self):
        events=[{"kind":"OPEN","at":NOW.isoformat(),"payload":{}} for _ in range(10)]
        self.assertIn("DAILY_TRADE_CEILING",self.evaluate(events=events)["reasons"])
    def test_daily_loss(self):
        event={"kind":"EXIT","at":NOW.isoformat(),"payload":{"pnl":"-29"}}
        self.assertIn("DAILY_LOSS_LIMIT",self.evaluate(events=[event])["reasons"])
    def test_liquidation(self):
        spec=replace(SPEC,max_leverage=D(30))
        p=plan(leverage=D(30),stop_loss=D(90))
        risk=IndependentRiskEngine(replace(RiskLimits(),max_leverage="30"))
        result=risk.evaluate(p,spec,{"balance":"1250","halted":0},[],[],NOW,strategy_validated=True,blackout=False,liquidity_ok=True)
        self.assertIn("LIQUIDATION_BEFORE_STOP",result["reasons"])


class Stateful(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.path=Path(self.temp.name)/"state.sqlite";self.store=Store(self.path)
        self.broker=PaperBroker(self.store,"paper")
    def tearDown(self):self.temp.cleanup()
    def opened(self,p=None):
        return self.broker.open(p or plan(),SPEC,NOW,strategy_validated=True,blackout=False,liquidity_ok=True)
    def test_open_stop_and_targets_persist(self):
        self.assertEqual(self.opened()["status"],"SIMULATED_FILLED")
        position=self.store.report("paper")["positions"][0]
        self.assertEqual(position["stop_loss"],"98");self.assertEqual(len(position["plan"]["take_profits"]),3)
    def test_idempotence(self):
        self.opened();self.assertEqual(self.opened()["status"],"DUPLICATE")
        self.assertEqual(len(self.store.report("paper")["positions"]),1)
    def test_concurrent_same_signal(self):
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:self.opened(),range(4)))
        self.assertEqual(sum(r["status"]=="SIMULATED_FILLED" for r in results),1)
    def test_concurrent_distinct_signal(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda i:self.opened(plan(signal_id=str(i))),range(4)))
        self.assertEqual(sum(r["status"]=="SIMULATED_FILLED" for r in results),1)
    def test_stop_gap(self):
        self.opened();actions=self.broker.monitor("BTC",bar(open=95,low=94,high=96,close=95))
        self.assertEqual(actions[0]["reason"],"STOP");self.assertLess(actions[0]["price"],95)
    def test_stop_before_tp_intrabar(self):
        self.opened();actions=self.broker.monitor("BTC",bar(low=97,high=110))
        self.assertEqual([a["reason"] for a in actions],["STOP"])
    def test_three_partial_exits(self):
        self.opened();actions=self.broker.monitor("BTC",bar(high=110,close=109))
        self.assertEqual([a["quantity"] for a in actions],[D(".25"),D(".35"),D(".40")])
        self.assertEqual(self.store.report("paper")["positions"][0]["status"],"CLOSED")
    def test_exit_not_duplicated(self):
        self.opened();b=bar(high=110,close=109);self.broker.monitor("BTC",b)
        self.assertEqual(self.broker.monitor("BTC",b),[])
    def test_restart(self):
        self.opened();new=PaperBroker(Store(self.path),"paper")
        self.assertEqual(len(new.monitor("BTC",bar(high=110,close=109))),3)
    def test_halt_still_exits(self):
        self.opened();self.store.halt("paper")
        self.assertEqual(self.broker.monitor("BTC",bar(low=97))[0]["reason"],"STOP")
    def test_cannot_widen_stop(self):
        result=self.opened()
        with self.assertRaises(TradingError):self.broker.tighten_stop(result["position_id"],97)
    def test_stop_tightening(self):
        result=self.opened();self.broker.tighten_stop(result["position_id"],99)
        self.assertEqual(self.store.report("paper")["positions"][0]["stop_loss"],"99")
    def test_stop_cannot_cross_market(self):
        result=self.opened()
        with self.assertRaises(TradingError):self.broker.tighten_stop(result["position_id"],101)
    def test_fees_reconcile_balance(self):
        self.opened();self.broker.monitor("BTC",bar(high=110,close=109))
        report=self.store.report("paper")
        self.assertEqual(D(report["account"]["balance"])-1250,D(report["positions"][0]["net_pnl"]))
    def test_short(self):
        p=plan(side="SHORT",stop_loss=D(102),take_profits=tuple(TakeProfit(D(p),D(f)) for p,f in [(96,".25"),(94,".35"),(92,".40")]))
        self.opened(p);actions=self.broker.monitor("BTC",bar(low=90,close=91))
        self.assertEqual(len(actions),3);self.assertGreater(sum(a["pnl"] for a in actions),0)
    def test_notification_outbox(self):
        self.opened();self.broker.monitor("BTC",bar(high=110,close=109))
        self.assertEqual(len(self.store.report("paper")["notifications"]),4)
    def test_transaction_rollback(self):
        with self.assertRaises(RuntimeError):
            with self.store.transaction("paper") as tx:
                tx.event("paper","ROLLBACK",{},NOW);raise RuntimeError()
        self.assertFalse(self.store.report("paper")["events"])
    def test_resume_requires_operator(self):
        self.store.halt("paper")
        with self.assertRaises(TradingError):self.store.resume("paper")
    def test_email_failure_does_not_rollback_exit(self):
        self.opened();self.broker.monitor("BTC",bar(low=97))
        sender=SMTPEmailSender(env={})
        result=NotificationWorker(self.store,sender).flush(NOW+timedelta(hours=2))
        self.assertTrue(all(r["status"]=="PENDING" for r in result))
        self.assertEqual(self.store.report("paper")["positions"][0]["status"],"CLOSED")
    def test_email_provider_acceptance(self):
        self.opened()
        class Sender:
            def send(self,id,payload):return {"status":"SMTP_ACCEPTED","message_id":id,"delivered":False}
        result=NotificationWorker(self.store,Sender()).flush(NOW)
        self.assertEqual(result[0]["status"],"SMTP_ACCEPTED")
        self.assertFalse(result[0]["delivered"])
    def test_email_unconfirmed_not_sent(self):
        self.opened()
        class Sender:
            def send(self,id,payload):return {"status":"success"}
        self.assertEqual(NotificationWorker(self.store,Sender()).flush(NOW)[0]["status"],"PENDING")
    def test_demo_full_cycle(self):
        s=scenario();engine=AgenticTradingOrchestrator(Settings(account="demo",watchlist=("BTC",)),self.store)
        report=engine.run({"BTC":s["bars"]},{"BTC":s["spec"]},s["now"],macro=s["macro"],liquidity=s["liquidity"],validation={},synthetic_demonstration=True)
        self.assertEqual(report["results"][0]["status"],"SIMULATED_FILLED")
        for b in s["exit_bars"]:engine.paper.monitor("BTC",b)
        self.assertEqual(self.store.report("demo")["positions"][0]["status"],"CLOSED")
    def test_unvalidated_normal_scan_abstains(self):
        s=scenario();engine=AgenticTradingOrchestrator(Settings(account="normal",watchlist=("BTC",)),self.store)
        report=engine.run({"BTC":s["bars"]},{"BTC":s["spec"]},s["now"],macro=s["macro"],liquidity=s["liquidity"],validation={})
        self.assertEqual(report["results"][0]["status"],"BLOCK")
    def test_two_accounts_same_plan(self):
        self.opened();second=PaperBroker(self.store,"second")
        result=second.open(plan(),SPEC,NOW,strategy_validated=True,blackout=False,liquidity_ok=True)
        self.assertEqual(result["status"],"SIMULATED_FILLED")
    def test_performance_groups_confirmed_trades(self):
        from agentic_trading.reporting import performance_report
        self.opened();self.broker.monitor("BTC",bar(high=110,close=109))
        report=performance_report(self.store,"paper",NOW+timedelta(hours=2),reference_capital="1500")
        self.assertEqual(report["groups"][0]["mode"],"PAPER")
        self.assertEqual(report["groups"][0]["metrics"]["equity"][0],1500)
    def test_performance_future_trades_excluded(self):
        from agentic_trading.reporting import performance_report
        self.opened();self.broker.monitor("BTC",bar(high=110,close=109))
        self.assertEqual(performance_report(self.store,"paper",NOW)["groups"],[])
    def test_retry_backoff(self):
        self.opened();worker=NotificationWorker(self.store,SMTPEmailSender(env={}))
        self.assertEqual(worker.flush(NOW)[0]["status"],"PENDING")
        self.assertEqual(worker.flush(NOW),[])
    def test_funding_is_debited(self):
        risk=IndependentRiskEngine(costs=Costs(funding_bps_per_8h=D(8)))
        broker=PaperBroker(self.store,"funding",risk=risk)
        broker.open(plan(),SPEC,NOW,strategy_validated=True,blackout=False,liquidity_ok=True)
        broker.monitor("BTC",bar(hours=8))
        self.assertTrue(any(e["kind"]=="FINANCING" for e in self.store.report("funding")["events"]))


class ContextAndScoring(unittest.TestCase):
    def test_score_exact_threshold(self):
        engine=SetupScoringEngine({"quality":100})
        self.assertEqual(engine.score({"quality":".67"})["status"],"SETUP_ELIGIBLE_FOR_RISK_VALIDATION")
    def test_score_under_threshold(self):
        self.assertEqual(SetupScoringEngine({"q":100}).score({"q":".669"})["status"],"NO_TRADE")
    def test_score_not_probability(self):self.assertIsNone(SetupScoringEngine({"q":100}).score({"q":1})["probability"])
    def test_missing_score_component(self):
        with self.assertRaises(TradingError):SetupScoringEngine().score({})
    def test_unknown_calendar_blocks(self):self.assertTrue(context_at([],[],NOW)["blackout"])
    def test_covered_empty_calendar(self):
        self.assertFalse(context_at([],[],NOW,calendar_asof=NOW,coverage_until=NOW+timedelta(hours=1))["blackout"])
    def test_future_macro_not_visible(self):
        row=Observation("CPI",2,"BLS","2026-10-01",(NOW+timedelta(hours=1)).isoformat(),(NOW+timedelta(hours=1)).isoformat(),NOW.isoformat(),1)
        self.assertEqual(context_at([row],[],NOW)["status"],"INSUFFICIENT_DATA")
    def test_event_blackout(self):
        event={"time":NOW.isoformat(),"available_at":(NOW-timedelta(days=1)).isoformat(),"impact":"high"}
        self.assertTrue(context_at([],[event],NOW,calendar_asof=NOW,coverage_until=NOW+timedelta(hours=1))["blackout"])
    def test_irrelevant_event(self):
        event={"time":NOW.isoformat(),"available_at":(NOW-timedelta(days=1)).isoformat(),"impact":"high","symbols":["XAUUSD"]}
        self.assertFalse(context_at([],[event],NOW,calendar_asof=NOW,coverage_until=NOW+timedelta(hours=1),symbol="BTC")["blackout"])
    def test_strategy_closed_confirmation(self):
        s=scenario();self.assertIsNotNone(RangeBreakout().detect(s["bars"]))
        self.assertIsNone(RangeBreakout().detect(s["bars"][:-1]))
    def test_smc_not_executable(self):self.assertFalse(smc_features(scenario()["bars"])["execution_enabled"])
    def test_regime_abstention(self):self.assertEqual(MarketRegimeClassifier().classify(scenario()["bars"])["classification"],"DEGRADED")
    def test_volatility_missing_depth(self):self.assertEqual(volatility_rank(scenario()["bars"])["classification"],"INSUFFICIENT_DATA")
    def test_safety_missing_stop(self):
        result=SafetySupervisor().inspect([{"id":"1","mode":"PAPER","status":"OPEN","stop_loss":None}],NOW,data_time=NOW)
        self.assertIn("MISSING_STOP",result["issues"])
    def test_reconciliation(self):
        self.assertIn("RECONCILIATION_MISMATCH",SafetySupervisor().inspect([],NOW,data_time=NOW,broker_position_ids=["unseen"])["issues"])


class Quant(unittest.TestCase):
    def test_drawdown(self):self.assertAlmostEqual(performance([10,-20,5],100)["max_drawdown_fraction"],20/110)
    def test_profit_factor(self):self.assertEqual(performance([10,-5,5])["profit_factor"],3)
    def test_no_trades(self):self.assertIsNone(performance([])["win_rate"])
    def test_monte_carlo_reproducible(self):
        self.assertEqual(monte_carlo([1,-2,3],runs=50),monte_carlo([1,-2,3],runs=50))
    def test_negative_ruin(self):
        self.assertEqual(monte_carlo([-100,-100],initial_capital=100,runs=50)["ruin_probability_under_resampling_assumptions"],1)
    def test_bootstrap_ci(self):self.assertEqual(bootstrap_mean_ci([2,2,2],runs=20),[2.,2.])
    def test_brier_score(self):self.assertEqual(calibration([.5,.5],[0,1])["brier_score"],.25)
    def test_bad_probability(self):
        with self.assertRaises(TradingError):calibration([1.1],[1])
    def test_stage_denies_insufficient_evidence(self):
        self.assertFalse(QuantitativeValidationEngine().assess([1,1],["RANGE"],out_of_sample=True)["admitted"])
    def test_no_auto_live(self):self.assertFalse(QuantitativeValidationEngine().assess([1]*100,["A","B","C"],out_of_sample=True)["live_eligible"])
    def test_walk_forward_separation(self):
        bars=scenario()["bars"];seen=[]
        def evaluate(rows,param):seen.append([b.time for b in rows]);return float(rows[-1].close)-float(rows[0].close)
        windows=walk_forward(bars,30,10,evaluate,[{"lookback":10},{"lookback":20}])
        self.assertTrue(windows);self.assertTrue(all(w["train_end"]<w["test_start"] for w in windows))


class ContractAndSecurity(unittest.TestCase):
    def test_moonx_prepare_mandatory_stop(self):
        result=MoonXBrokerAdapter(None).prepare(plan(),SPEC)
        self.assertEqual(result["arguments"]["stopLossPrice"],98)
        self.assertEqual(result["status"],"PREPARED_NOT_SENT")
    def test_live_adapters_cannot_send(self):
        for adapter in (MoonXBrokerAdapter(None),OKXBrokerAdapter(),BybitBrokerAdapter()):
            with self.subTest(adapter=adapter.name),self.assertRaises(TradingError):adapter.submit(plan())
    def test_mcp_write_not_called(self):
        class Transport:
            async def call(self,*args):raise AssertionError("write escaped")
        with self.assertRaises(TradingError):immediate(MoonXBrokerAdapter(Transport()).read("open_futures_position",{}))
    def test_mcp_read_contract(self):
        class Transport:
            async def call(self,name,args):return {"name":name,"arguments":args}
        result=immediate(MoonXBrokerAdapter(Transport()).read("get_price",{"symbol":"BTC"}))
        self.assertEqual(result["name"],"get_price")
    def test_bybit_demo_domain(self):
        prepared=BybitBrokerAdapter().prepare_demo(plan(),SPEC,symbol="BTCUSDT")
        self.assertEqual(prepared["base_url"],"https://api-demo.bybit.com")
        self.assertEqual(prepared["body"]["stopLoss"],"98")
    def test_okx_demo_header(self):
        self.assertEqual(OKXBrokerAdapter().prepare_demo(plan(),SPEC,instrument_id="BTC-USDT-SWAP",contracts_per_unit=100)["required_headers"],{"x-simulated-trading":"1"})
    def test_unsigned_validation_rejected(self):self.assertFalse(verify_evidence({"stage":"PAPER_VALIDATED"},"BTC","range-breakout-v1",NOW,key="secret"))
    def test_signed_validation_bound_to_instrument(self):
        data={"symbol":"BTC","strategy":"range-breakout-v1","stage":"PAPER_VALIDATED","admitted":True,"artifact_hash":"abc",
              "issued_at":(NOW-timedelta(days=1)).isoformat(),"expires_at":(NOW+timedelta(days=1)).isoformat()}
        data["signature"]=hmac.new(b"key",dumps(data).encode(),hashlib.sha256).hexdigest()
        self.assertTrue(verify_evidence(data,"BTC","range-breakout-v1",NOW,key="key"))
        self.assertFalse(verify_evidence(data,"ETH","range-breakout-v1",NOW,key="key"))
    def test_signed_validation_tamper(self):
        self.assertFalse(verify_evidence({"signature":"forged","admitted":True},"BTC","range-breakout-v1",NOW,key="key"))
    def test_public_client_denies_arbitrary_url(self):
        for url in ["http://localhost/","https://attacker.invalid/","https://api.bybit.com@attacker.invalid/"]:
            with self.subTest(url=url),self.assertRaises(TradingError):PublicJSONClient().get(url)
    def test_incomplete_mcp_response(self):
        with self.assertRaises(TradingError):moonx_candles({"count":2,"candles":[]},3600,NOW)
    def test_current_candle_excluded(self):
        raw={"count":1,"candles":[{"time":int(NOW.timestamp()*1000),"open":100,"high":101,"low":99,"close":100,"volume":2}]}
        with self.assertRaises(TradingError):moonx_candles(raw,3600,NOW)
    def test_future_timestamp_calendar_unknown(self):
        self.assertTrue(context_at([],[],NOW,calendar_asof=NOW+timedelta(seconds=1),coverage_until=NOW+timedelta(days=1))["blackout"])
    def test_top100_snapshots_and_changes(self):
        class Client:
            start=1
            def get(self,url,headers):
                return {"status":{"error_code":0},"data":[{"id":i,"symbol":str(i),"name":str(i),"slug":str(i),"cmc_rank":i-self.start+1,"quote":{"USD":{"price":1}},"tags":[]} for i in range(self.start,self.start+100)]}
        with TemporaryDirectory() as temp,patch.dict(os.environ,{"CMC_API_KEY":"UNIT_TEST_NOT_A_SECRET"}):
            store=Store(Path(temp)/"cmc.sqlite");client=Client();provider=CoinMarketCapUniverse(client)
            first=provider.top100(store,NOW);client.start=2;second=provider.top100(store,NOW+timedelta(hours=1))
            self.assertEqual(len(first["assets"]),100);self.assertEqual(second["entered"],[101]);self.assertEqual(second["exited"],[1])
    def test_invalid_mcp_payload_sanitized(self):
        from agentic_trading.remote_mcp import SDKMCPTransport
        class Response:
            isError=False
            content=[type('Text',(),{'type':'text','text':'not-json'})()]
        class Session:
            async def call_tool(self,*args):return Response()
        with self.assertRaises(TradingError):immediate(SDKMCPTransport(Session()).call("get_price",{"symbol":"BTC"}))


if __name__=="__main__":unittest.main()
