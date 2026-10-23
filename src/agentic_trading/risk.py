from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from .config import RiskLimits
from .models import D, Instrument, TradePlan, TradingError, floor_step, utc


@dataclass(frozen=True)
class Costs:
    fee_bps: Decimal = Decimal("5")  # each side
    spread_bps: Decimal = Decimal("2")  # full spread
    slippage_bps: Decimal = Decimal("2")  # each side, adverse
    funding_bps_per_8h: Decimal = Decimal("0")
    swap_bps_per_day: Decimal = Decimal("0")

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, D(getattr(self, name)))
            if getattr(self, name) < 0:
                raise TradingError("costs must be nonnegative stress assumptions")

    @property
    def adverse_bps(self):
        return self.spread_bps/2+self.slippage_bps

    def round_trip(self, notional, hours=0):
        return D(notional) * (2*self.fee_bps+self.spread_bps+2*self.slippage_bps+self.funding_bps_per_8h*D(hours)/8+self.swap_bps_per_day*D(hours)/24)/10000


def size_position(budget, entry, stop, instrument, costs=Costs()):
    budget, entry, stop = D(budget), D(entry), D(stop)
    distance = abs(entry-stop)*instrument.point_value
    # Reserve adverse entry movement and tick rounding in addition to the cost stress.
    loss_per_unit = (distance+costs.round_trip(entry*instrument.point_value)
                     +entry*instrument.point_value*costs.adverse_bps/10000
                     +2*instrument.tick_size*instrument.point_value)
    if budget <= 0 or distance <= 0:
        raise TradingError("positive risk budget and stop distance required")
    return floor_step(budget/loss_per_unit, instrument.quantity_step)


def economics(plan: TradePlan, spec: Instrument, costs=Costs()):
    notional = plan.entry*plan.quantity*spec.point_value
    risk = abs(plan.entry-plan.stop_loss)*plan.quantity*spec.point_value
    cost = costs.round_trip(notional)
    reward = sum(plan.sign*(t.price-plan.entry)*t.fraction for t in plan.take_profits)*plan.quantity*spec.point_value
    # Conservative isolated approximation. Never use as the provider's liquidation quote.
    liquidation_distance = plan.entry*(1/plan.leverage-spec.maintenance_margin_rate)
    return {"notional":notional, "margin":notional/plan.leverage, "gross_stop_risk":risk,
            "estimated_costs":cost, "net_stop_risk":risk+cost, "weighted_net_reward":reward-cost,
            "weighted_reward_risk":(reward-cost)/(risk+cost), "liquidation_distance_estimate":liquidation_distance,
            "gap_loss_2x_stop":2*risk+cost}


class IndependentRiskEngine:
    def __init__(self, limits=RiskLimits(), costs=Costs(), timezone="Africa/Lagos"):
        self.limits, self.costs, self.timezone = limits, costs, timezone

    def evaluate(self, plan, spec, account, positions, events, now, *, strategy_validated=False, blackout=True, liquidity_ok=False):
        limits, reasons = self.limits, []
        eco = economics(plan,spec,self.costs)
        local = utc(now).astimezone(ZoneInfo(self.timezone))
        day = local.date()
        monday = day-timedelta(days=day.weekday())
        def event_date(e):
            return utc(e["at"]).astimezone(ZoneInfo(self.timezone)).date()
        closed = [e for e in events if e["kind"] in ("EXIT", "FINANCING")]
        daily_losses = sum(max(-D(e["payload"].get("pnl",0)),D(0)) for e in closed if event_date(e)==day)
        weekly_losses = sum(max(-D(e["payload"].get("pnl",0)),D(0)) for e in closed if monday<=event_date(e)<=day)
        daily_losses += sum(D(e["payload"].get("fee",0)) for e in events if e["kind"]=="OPEN" and event_date(e)==day)
        weekly_losses += sum(D(e["payload"].get("fee",0)) for e in events if e["kind"]=="OPEN" and monday<=event_date(e)<=day)
        trades_today = sum(e["kind"]=="OPEN" and event_date(e)==day for e in events)
        # Count completed positions, not individual partial exits.
        completed = [p for p in positions if p["status"]=="CLOSED"]
        completed.sort(key=lambda p:p.get("closed_at",""),reverse=True)
        streak=0
        for p in completed:
            if D(p["net_pnl"])<0: streak+=1
            else: break
        opened = [p for p in positions if p["status"]=="OPEN"]
        open_risk = sum(D(p["remaining_risk"]) for p in opened)
        notional = sum(D(p["remaining_notional"]) for p in opened)
        margin = sum(D(p["remaining_margin"]) for p in opened)
        correlated = sum(D(p["remaining_risk"]) for p in opened if p["group"]==spec.correlation_group)
        asset_notional = sum(D(p["remaining_notional"]) for p in opened if p["symbol"]==plan.symbol)
        age = (utc(now)-plan.data_time).total_seconds()
        def block(condition, message):
            if condition: reasons.append(message)
        block(account["halted"], "KILL_SWITCH")
        block(not strategy_validated,"STRATEGY_NOT_VALIDATED")
        block(not spec.specs_verified,"CONTRACT_SPECS_UNVERIFIED")
        block(blackout,"MACRO_BLACKOUT_OR_UNKNOWN")
        block(not liquidity_ok,"LIQUIDITY_UNKNOWN_OR_LOW")
        block(age<0 or age>limits.max_data_age_seconds,"STALE_OR_FUTURE_DATA")
        block(plan.score<D(limits.minimum_setup_score),"SCORE_BELOW_THRESHOLD")
        block(plan.leverage>min(spec.max_leverage,D(limits.max_leverage)),"LEVERAGE_LIMIT")
        block(plan.quantity<spec.minimum_quantity or floor_step(plan.quantity,spec.quantity_step)!=plan.quantity,"QUANTITY_PRECISION")
        prices=[plan.entry,plan.stop_loss]+[t.price for t in plan.take_profits]
        block(any(p%spec.tick_size!=0 for p in prices),"PRICE_PRECISION")
        block(eco["net_stop_risk"]>D(limits.max_risk_per_trade),"TRADE_RISK_LIMIT")
        block(daily_losses+open_risk+eco["net_stop_risk"]>D(limits.max_daily_loss),"DAILY_LOSS_LIMIT")
        block(weekly_losses+open_risk+eco["net_stop_risk"]>D(limits.max_weekly_loss),"WEEKLY_LOSS_LIMIT")
        block(open_risk+eco["net_stop_risk"]>D(limits.max_aggregate_risk),"AGGREGATE_RISK_LIMIT")
        block(correlated+eco["net_stop_risk"]>D(limits.max_correlated_risk),"CORRELATED_RISK_LIMIT")
        block(notional+eco["notional"]>D(limits.max_notional),"NOTIONAL_LIMIT")
        block(asset_notional+eco["notional"]>D(limits.max_asset_notional),"ASSET_EXPOSURE_LIMIT")
        block(margin+eco["margin"]>min(D(limits.max_margin),D(account["balance"])),"MARGIN_LIMIT")
        block(trades_today>=limits.max_trades_per_day,"DAILY_TRADE_CEILING")
        block(streak>=limits.max_consecutive_losses,"LOSS_STREAK")
        block(self.costs.spread_bps>D(limits.max_spread_bps),"SPREAD_LIMIT")
        block(eco["estimated_costs"]>eco["gross_stop_risk"]*D(limits.max_cost_fraction_of_risk),"COST_LIMIT")
        block(eco["weighted_reward_risk"]<D(limits.minimum_reward_risk),"REWARD_RISK_LIMIT")
        block(eco["liquidation_distance_estimate"]<=abs(plan.entry-plan.stop_loss)+plan.entry*D(limits.liquidation_buffer_fraction),"LIQUIDATION_BEFORE_STOP")
        block(any(p["symbol"]==plan.symbol for p in opened),"EXISTING_POSITION")
        return {"status":"BLOCK" if reasons else "PASS","reasons":reasons,"economics":eco,
                "daily_losses":daily_losses,"weekly_losses":weekly_losses,"open_risk":open_risk,"trades_today":trades_today}
