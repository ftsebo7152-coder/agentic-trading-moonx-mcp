"""Reproducible, cost-aware research; never a profitability assertion."""
from dataclasses import dataclass
from math import sqrt
from random import Random
from statistics import mean, pstdev, stdev
from .models import D, TradingError


def quantile(values,p):
    if not values or not 0<=p<=1:raise TradingError("invalid quantile")
    ordered=sorted(values);index=(len(ordered)-1)*p
    lo=int(index);hi=min(lo+1,len(ordered)-1)
    return ordered[lo]*(hi-index)+ordered[hi]*(index-lo) if hi!=lo else ordered[lo]


def wilson(wins,n,z=1.96):
    if not n:return [0.0,1.0]
    p=wins/n;denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [max(0,center-half),min(1,center+half)]


def performance(pnls,initial_capital=1250,risks=None):
    values=[float(v) for v in pnls]
    if float(initial_capital)<=0:raise TradingError("positive capital required")
    equity=peak=float(initial_capital);max_dd=0;streak=max_streak=0
    curve=[equity]
    for value in values:
        equity+=value;peak=max(peak,equity);curve.append(equity)
        max_dd=max(max_dd,(peak-equity)/peak)
        streak=streak+1 if value<0 else 0;max_streak=max(max_streak,streak)
    gross_profit=sum(v for v in values if v>0);gross_loss=-sum(v for v in values if v<0)
    avg=mean(values) if values else None
    sd=stdev(values) if len(values)>1 else None
    downside=sqrt(mean(min(v,0)**2 for v in values)) if values else None
    ci=[avg-1.96*sd/sqrt(len(values)),avg+1.96*sd/sqrt(len(values))] if sd is not None else None
    return {"trades":len(values),"net_pnl":sum(values),"win_rate":sum(v>0 for v in values)/len(values) if values else None,
            "win_rate_wilson_95":wilson(sum(v>0 for v in values),len(values)),
            "profit_factor":gross_profit/gross_loss if gross_loss else None,"no_losses_observed":gross_loss==0,
            "expectancy":avg,"expectancy_normal_approximation_ci95":ci,"max_drawdown_fraction":max_dd,
            "trade_level_sharpe_unannualized":avg/sd if sd else None,"trade_level_sortino_unannualized":avg/downside if downside else None,
            "mean_r":mean(v/float(r) for v,r in zip(values,risks)) if risks and len(risks)==len(values) and all(float(r)>0 for r in risks) else None,
            "max_consecutive_losses":max_streak,"equity":curve,"distribution":values,
            "caution":"Trade-level ratios are unannualized. Normal CI can be unreliable for few/dependent trades; inspect bootstrap and out-of-sample results."}


def monte_carlo(pnls,*,initial_capital=1250,runs=10000,seed=19,block_size=3,ruin_fraction=0.5):
    values=[float(x) for x in pnls]
    if not values or runs<1 or block_size<1 or not 0<ruin_fraction<1:raise TradingError("invalid Monte Carlo input")
    random=Random(seed);final=[];drawdowns=[];ruined=0
    for _ in range(runs):
        sample=[]
        while len(sample)<len(values):
            start=random.randrange(len(values))
            sample.extend(values[(start+j)%len(values)] for j in range(block_size))
        stats=performance(sample[:len(values)],initial_capital)
        final.append(stats["equity"][-1]);drawdowns.append(stats["max_drawdown_fraction"])
        ruined+=min(stats["equity"])<=initial_capital*ruin_fraction
    return {"runs":runs,"seed":seed,"block_size":block_size,"final_equity_p05":quantile(final,.05),
            "final_equity_p50":quantile(final,.5),"final_equity_p95":quantile(final,.95),
            "drawdown_p95":quantile(drawdowns,.95),"ruin_probability_under_resampling_assumptions":ruined/runs,
            "ruin_threshold_fraction_of_initial":ruin_fraction,"scope":"historical block bootstrap; excludes unseen shocks"}


def bootstrap_mean_ci(values,runs=2000,seed=19):
    values=[float(v) for v in values]
    if len(values)<2: return None
    random=Random(seed)
    samples=[mean(random.choices(values,k=len(values))) for _ in range(runs)]
    return [quantile(samples,.025),quantile(samples,.975)]


def calibration(probabilities,outcomes,bins=10):
    if not probabilities or len(probabilities)!=len(outcomes) or bins<1 or any(not 0<=p<=1 for p in probabilities) or any(y not in (0,1) for y in outcomes):
        raise TradingError("bounded probabilities and binary outcomes required")
    groups=[]
    for i in range(bins):
        rows=[(p,y) for p,y in zip(probabilities,outcomes) if min(int(p*bins),bins-1)==i]
        groups.append({"bin":i,"n":len(rows),"mean_prediction":mean(p for p,y in rows) if rows else None,
                       "observed_rate":mean(y for p,y in rows) if rows else None,"wilson_95":wilson(sum(y for p,y in rows),len(rows))})
    return {"brier_score":mean((p-y)**2 for p,y in zip(probabilities,outcomes)),"bins":groups}


def walk_forward(bars,train_size,test_size,evaluate,parameters):
    if min(train_size,test_size)<2 or not parameters:raise TradingError("invalid walk-forward windows")
    windows=[]
    for start in range(0,len(bars)-train_size-test_size+1,test_size):
        train=bars[start:start+train_size];test=bars[start+train_size:start+train_size+test_size]
        # Parameter selection sees training observations exclusively.
        scores=[(evaluate(train,param),param) for param in parameters]
        best=max(scores,key=lambda pair:pair[0])[1]
        windows.append({"train_start":train[0].time,"train_end":train[-1].time,"test_start":test[0].time,
                        "test_end":test[-1].time,"parameters":best,"out_of_sample_result":evaluate(test,best)})
    return windows


@dataclass(frozen=True)
class ValidationCriteria:
    maximum_drawdown: float = .15
    minimum_distinct_regimes: int = 3
    maximum_win_rate_ci_width: float = .25


class QuantitativeValidationEngine:
    def assess(self,pnls,regimes,*,out_of_sample,forward_test=False,paper_test=False,criteria=ValidationCriteria()):
        metrics=performance(pnls);ci=bootstrap_mean_ci(pnls)
        reasons=[]
        if not out_of_sample:reasons.append("OUT_OF_SAMPLE_REQUIRED")
        if ci is None or ci[0]<=0:reasons.append("POSITIVE_EXPECTANCY_NOT_ESTABLISHED")
        if len(set(regimes))<criteria.minimum_distinct_regimes:reasons.append("REGIME_DIVERSITY_INSUFFICIENT")
        if metrics["max_drawdown_fraction"]>criteria.maximum_drawdown:reasons.append("DRAWDOWN_LIMIT")
        bounds=metrics["win_rate_wilson_95"]
        if bounds[1]-bounds[0]>criteria.maximum_win_rate_ci_width:reasons.append("STATISTICAL_UNCERTAINTY_TOO_HIGH")
        stage="RESEARCH" if reasons else "PAPER_VALIDATED" if paper_test and forward_test else "FORWARD_TEST" if forward_test else "BACKTESTED"
        return {"stage":stage,"admitted":not reasons,"reasons":reasons,"metrics":metrics,"bootstrap_expectancy_ci95":ci,
                "live_eligible":False,"note":"Live eligibility requires separate operational and administrative qualification."}


def stress_costs(pnls,notionals,extra_round_trip_bps=(5,10,25,50)):
    if len(pnls)!=len(notionals):raise TradingError("matching trade notionals required")
    return {str(bps):performance([float(p)-float(n)*bps/10000 for p,n in zip(pnls,notionals)]) for bps in extra_round_trip_bps}
