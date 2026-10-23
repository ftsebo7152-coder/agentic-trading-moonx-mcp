"""Chronological replay through the same local execution/risk engine."""
from tempfile import TemporaryDirectory
from pathlib import Path
from .analysis import RangeBreakout
from .config import RiskLimits
from .models import D, TakeProfit, TradePlan, validate_candles
from .paper import PaperBroker
from .quantitative import performance, monte_carlo, stress_costs
from .risk import IndependentRiskEngine, Costs, size_position
from .storage import Store


def backtest(bars,spec,*,capital="1250",lookback=20,costs=Costs(),limits=RiskLimits(),scratch=None):
    validate_candles(bars)
    with TemporaryDirectory(dir=scratch) as directory:
        store=Store(Path(directory)/"backtest.sqlite")
        broker=PaperBroker(store,"backtest",capital,IndependentRiskEngine(limits,costs))
        strategy=RangeBreakout(lookback)
        for index,bar in enumerate(bars):
            broker.monitor(spec.symbol,bar)
            signal=strategy.detect(bars[:index+1])
            if not signal:continue
            quantity=size_position(limits.max_risk_per_trade,signal["entry"],signal["stop_loss"],spec,costs)
            if quantity<spec.minimum_quantity:continue
            sign=D(1 if signal["side"]=="LONG" else -1)
            distance=abs(signal["entry"]-signal["stop_loss"])
            from .models import floor_step
            targets=tuple(TakeProfit(floor_step(signal["entry"]+sign*distance*D(r),spec.tick_size),D(f)) for r,f in [(2,"0.25"),(3,"0.35"),(4,"0.40")])
            plan=TradePlan(spec.symbol,signal["side"],signal["entry"],signal["stop_loss"],quantity,D(1),targets,
                           strategy.name,D(80),bar.time,signal["signal_id"],"RESEARCH_BACKTEST_ONLY")
            broker.open(plan,spec,bar.time,strategy_validated=True,blackout=False,liquidity_ok=True)
        # Mark final open trades explicitly, do not discard their unrealized outcome.
        with store.transaction("backtest") as tx:positions=tx.positions("backtest")
        for p in positions:broker.close(p["id"],bars[-1].close,bars[-1].time,"END_OF_SAMPLE")
        report=store.report("backtest")
        trades=[p for p in report["positions"] if p["status"]=="CLOSED"]
        pnl=[D(p["net_pnl"]) for p in trades]
        notionals=[D(p["entry"])*D(p["quantity"])*spec.point_value for p in trades]
        result={"scope":"RESEARCH_IN_SAMPLE_NOT_STRATEGY_VALIDATION","instrument":spec.symbol,"bars":len(bars),
                "metrics":performance(pnl,float(capital)),"trades":trades,"costs":costs,
                "limitations":["Single-instrument historical replay; no historical macro/order-book data.",
                               "Historical universe snapshots are required for multi-asset survivorship control.",
                               "Stop-first intrabar ambiguity policy; no tick queue model."]}
        if pnl:
            result["monte_carlo"]=monte_carlo(pnl,initial_capital=float(capital))
            result["cost_stress"]=stress_costs(pnl,notionals)
        return result
