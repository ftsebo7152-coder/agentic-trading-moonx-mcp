from datetime import timedelta
from .indicators import summary
from .models import D, TradingError, fingerprint


class MarketRegimeClassifier:
    def classify(self,bars,*,blackout=False,liquidity_ok=False):
        values=summary(bars)
        if blackout: regime="ECONOMIC_EVENT"
        elif not liquidity_ok: regime="DEGRADED"
        elif values["adx"] is None or values["ema_50"] is None: regime="INSUFFICIENT_DATA"
        elif values["normalized_atr"]>0.04: regime="HIGH_VOLATILITY"
        elif values["normalized_atr"]<0.001: regime="LOW_VOLATILITY"
        elif values["adx"]>=25: regime="TREND_UP" if values["ema_20"]>values["ema_50"] else "TREND_DOWN"
        else:
            band=values["bollinger"]
            width=(band["upper"]-band["lower"])/band["middle"]
            regime="COMPRESSION" if width<0.01 else "EXPANSION" if width>0.08 else "RANGE"
        allowed=[] if regime in ("DEGRADED","ECONOMIC_EVENT","INSUFFICIENT_DATA") else ["range-breakout-v1"]
        return {"classification":regime,"indicators":values,"uncertainty":"HEURISTIC_UNCALIBRATED",
                "valid_until":bars[-1].time+timedelta(hours=1),"compatible_strategies":allowed,
                "discouraged_strategies":["smc-experimental"],"probability":None}


class SetupScoringEngine:
    DEFAULT_WEIGHTS={"structure":25,"multi_timeframe":15,"liquidity":15,"volume":10,"macro":10,"regime":10,"costs":5,"historical":10}

    def __init__(self,weights=None,minimum=67):
        self.weights=dict(weights or self.DEFAULT_WEIGHTS);self.minimum=D(minimum)
        if not self.weights or sum(self.weights.values())!=100 or any(v<0 for v in self.weights.values()) or not 0<=self.minimum<=100:
            raise TradingError("nonnegative weights must sum to 100")

    def score(self,components):
        if set(components)!=set(self.weights) or any(not 0<=D(v)<=1 for v in components.values()):
            raise TradingError("complete bounded scoring components required")
        detail={k:D(components[k])*D(v) for k,v in self.weights.items()}
        score=sum(detail.values())
        return {"score":score,"components":detail,"minimum":self.minimum,"probability":None,
                "status":"SETUP_ELIGIBLE_FOR_RISK_VALIDATION" if score>=self.minimum else "NO_TRADE"}


class RangeBreakout:
    name="range-breakout-v1"
    def __init__(self,lookback=20,volume_multiplier=1.2):
        if lookback<2 or volume_multiplier<=0:raise TradingError("invalid breakout parameters")
        self.lookback,self.volume_multiplier=lookback,volume_multiplier

    def detect(self,bars):
        if len(bars)<self.lookback+2:return None
        # The previous close breaks the range; the latest close confirms it. All bars are complete.
        history=bars[-self.lookback-2:-2];trigger,confirm=bars[-2:]
        high=max(b.high for b in history);low=min(b.low for b in history)
        avg_volume=sum(b.volume for b in history)/len(history)
        if avg_volume<=0 or trigger.volume<avg_volume*D(self.volume_multiplier):return None
        if trigger.close>high and confirm.close>high:side="LONG";stop=low
        elif trigger.close<low and confirm.close<low:side="SHORT";stop=high
        else:return None
        return {"side":side,"entry":confirm.close,"stop_loss":stop,"range_high":high,"range_low":low,
                "strategy":self.name,"time":confirm.time,"signal_id":fingerprint([self.name,confirm.time,side])}


def smc_features(bars,window=10):
    """Experimental causal definitions; never promoted to an execution strategy."""
    if len(bars)<window+3:return {"execution_enabled":False,"features":[]}
    a,b,c=bars[-3:];prior=bars[-window-1:-1]
    high=max(x.high for x in prior);low=min(x.low for x in prior)
    center=(high+low)/2
    features=[]
    if c.low>a.high:features.append({"kind":"BULLISH_FVG","low":a.high,"high":c.low,"invalidation":a.high})
    if c.high<a.low:features.append({"kind":"BEARISH_FVG","low":c.high,"high":a.low,"invalidation":a.low})
    if c.high>high and c.close<high:features.append({"kind":"BUY_SIDE_LIQUIDITY_SWEEP","invalidation":c.high})
    if c.low<low and c.close>low:features.append({"kind":"SELL_SIDE_LIQUIDITY_SWEEP","invalidation":c.low})
    if c.close>high:features.append({"kind":"BULLISH_BOS","invalidation":low})
    if c.close<low:features.append({"kind":"BEARISH_BOS","invalidation":high})
    if b.close<b.open and c.close>b.high:features.append({"kind":"BULLISH_ORDER_BLOCK","low":b.low,"high":b.high,"invalidation":b.low})
    if b.close>b.open and c.close<b.low:features.append({"kind":"BEARISH_ORDER_BLOCK","low":b.low,"high":b.high,"invalidation":b.high})
    return {"execution_enabled":False,"features":features,"location":"DISCOUNT" if c.close<center else "PREMIUM",
            "not_implemented":["CHOCH","MSS","BREAKER_BLOCK","MITIGATION_BLOCK","SESSION_ORB","BREAKOUT_RETEST"]}


def volatility_rank(bars,*,volume_24h=None,spread_bps=None,depth_usd=None,funding=None,open_interest=None):
    values=summary(bars)
    missing=[k for k,v in {"volume":volume_24h,"spread":spread_bps,"depth":depth_usd,"funding":funding,"open_interest":open_interest}.items() if v is None]
    if missing or values["normalized_atr"] is None:label="INSUFFICIENT_DATA"
    elif volume_24h<1_000_000 or depth_usd<100_000:label="LOW_LIQUIDITY"
    elif spread_bps>20 or abs(funding)>0.001 or values["normalized_atr"]>0.05:label="HIGH_VOLATILITY_HIGH_RISK"
    else:label="HIGH_VOLATILITY_TRADABLE"
    return {"classification":label,"missing":missing,"metrics":values,"volume_24h":volume_24h,"spread_bps":spread_bps,"depth_usd":depth_usd,"funding":funding,"open_interest":open_interest}
