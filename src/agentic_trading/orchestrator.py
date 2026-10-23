from datetime import timedelta
from uuid import uuid4
from .models import D, Mode, TakeProfit, TradePlan, TradingError, dumps, floor_step, utc, validate_candles
from .analysis import MarketRegimeClassifier, RangeBreakout, SetupScoringEngine
from .fundamentals import context_at
from .paper import PaperBroker
from .risk import IndependentRiskEngine, size_position
from .safety import SafetySupervisor
from .permissions import verify_evidence


class AgenticTradingOrchestrator:
    def __init__(self,settings,store):
        self.settings,self.store=settings,store
        self.risk=IndependentRiskEngine(settings.limits,timezone=settings.timezone)
        self.paper=PaperBroker(store,settings.account,settings.capital,self.risk)

    def run(self,markets,specs,now,*,macro,liquidity,validation,synthetic_demonstration=False):
        if self.settings.mode not in (Mode.PAPER,Mode.BACKTEST,Mode.REPLAY):
            raise TradingError("this orchestrator only opens isolated simulated positions")
        if synthetic_demonstration and not macro.get("synthetic"):
            raise TradingError("demonstration bypass requires explicitly labelled synthetic data")
        run_id=str(uuid4());results=[]
        for symbol in self.settings.watchlist:
            try:
                bars=markets.get(symbol,[]);validate_candles(bars)
                bars=[b for b in bars if b.time<=utc(now)]
                if not bars:raise TradingError("NO_COMPLETED_CANDLES")
                # Existing-position management runs before every entry gate, including kill switch.
                for b in bars:self.paper.monitor(symbol,b)
                with self.store.transaction(self.settings.account) as tx:
                    positions=tx.positions(self.settings.account)
                safety=SafetySupervisor().inspect(positions,now,data_time=bars[-1].time,
                                                  maximum_age=self.settings.limits.max_data_age_seconds)
                if not safety["new_entries_allowed"]:
                    results.append({"symbol":symbol,"status":"NO_TRADE","safety":safety});continue
                liq=liquidity.get(symbol,{})
                liquidity_ok=(liq.get("source") is not None and liq.get("asof") is not None and
                              0<=(utc(now)-utc(liq["asof"])).total_seconds()<=self.settings.limits.max_data_age_seconds and
                              D(liq.get("volume_24h",0))>=1_000_000 and D(liq.get("depth_usd",0))>=100_000 and
                              D(liq.get("spread_bps",10000))<=D(self.settings.limits.max_spread_bps))
                context=context_at(macro.get("observations",[]),macro.get("events",[]),now,
                                   calendar_asof=macro.get("calendar_asof"),coverage_until=macro.get("coverage_until"),symbol=symbol)
                regime=MarketRegimeClassifier().classify(bars,blackout=context["blackout"],liquidity_ok=liquidity_ok)
                signal=RangeBreakout().detect(bars)
                if signal is None:
                    results.append({"symbol":symbol,"status":"NO_TRADE","reason":"NO_CONFIRMED_BREAKOUT","regime":regime,"fundamentals":context});continue
                evidence=validation.get(symbol,{})
                validated=verify_evidence(evidence,symbol,signal["strategy"],now)
                if synthetic_demonstration:validated=True
                score=SetupScoringEngine(minimum=self.settings.limits.minimum_setup_score).score({
                    "structure":1,"multi_timeframe":0, # missing HTF confirmation scores zero, never invented
                    "liquidity":int(liquidity_ok),"volume":1,"macro":int(not context["blackout"] and context["status"]=="OBSERVED"),
                    "regime":int(signal["strategy"] in regime["compatible_strategies"]),"costs":1,"historical":int(validated)})
                spec=specs[symbol]
                quantity=size_position(self.settings.limits.max_risk_per_trade,signal["entry"],signal["stop_loss"],spec,self.risk.costs)
                if quantity<spec.minimum_quantity:raise TradingError("SIZE_BELOW_MINIMUM")
                distance=abs(signal["entry"]-signal["stop_loss"]);sign=D(1 if signal["side"]=="LONG" else -1)
                targets=tuple(TakeProfit(floor_step(signal["entry"]+sign*distance*D(multiple),spec.tick_size),D(fraction))
                              for multiple,fraction in [(2,"0.25"),(3,"0.35"),(4,"0.40")])
                plan=TradePlan(symbol,signal["side"],signal["entry"],signal["stop_loss"],quantity,D(1),targets,
                               signal["strategy"],score["score"],bars[-1].time,symbol+":"+signal["signal_id"],
                               "SYNTHETIC DEMONSTRATION" if synthetic_demonstration else "Confirmed completed-bar range breakout")
                result=self.paper.open(plan,spec,now,strategy_validated=validated,blackout=context["blackout"],liquidity_ok=liquidity_ok)
                results.append({"symbol":symbol,**result,"score":score,"plan":plan,"regime":regime,"fundamentals":context,
                                "synthetic_demonstration":synthetic_demonstration})
            except (TradingError,KeyError,ValueError) as exc:
                results.append({"symbol":symbol,"status":"NO_TRADE","reason":str(exc)})
        report={"run_id":run_id,"mode":self.settings.mode,"at":now,"results":results,"synthetic_demonstration":synthetic_demonstration}
        with self.store.transaction(self.settings.account) as tx:
            tx.execute("INSERT INTO runs(id,account,at,payload) VALUES(?,?,?,?)",(run_id,self.settings.account,now.isoformat(),dumps(report)))
            tx.event(self.settings.account,"SCAN",report,now)
        return report


class HourlyMarketScanner:
    def __init__(self,orchestrator):self.orchestrator=orchestrator
    def scan(self,*args,**kwargs):return self.orchestrator.run(*args,**kwargs)


class PositionSafetyMonitor:
    def __init__(self,paper):self.paper=paper
    def tick(self,symbol,completed_bar):return self.paper.monitor(symbol,completed_bar)
