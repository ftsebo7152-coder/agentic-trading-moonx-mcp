"""Six explicit closed-bar strategies. These rules are unqualified research hypotheses."""
from dataclasses import asdict
from datetime import timedelta
from ..models import D,TradingError,fingerprint,utc
from ..indicators import summary,ema,rsi,bollinger
from ..analysis import RangeBreakout
from ..enhancements.structure import structure_events,opening_range
from .timeframes import closed_bars,confirmation,INTERVALS


def signal(name,side,bars,stop,reason,volume=False):
    price=bars[-1].close;stop=D(stop)
    if stop<=0 or (price-stop)*(1 if side=='LONG' else -1)<=0:return None
    return {'strategy':name,'side':side,'entry':price,'stop_loss':stop,'time':bars[-1].time,
            'reason':reason,'volume_confirmed':bool(volume)}


def breakout_retest(bars,policy):
    av=summary(bars)['atr']
    if not av:return None
    last=bars[-1];tolerance=D(av)*D('.15')
    for i in range(len(bars)-2,max(19,len(bars)-policy.retest_lookback-2),-1):
        history=bars[i-20:i];trigger=bars[i]
        high=max(b.high for b in history);low=min(b.low for b in history)
        average=sum(b.volume for b in history)/20
        if average<=0 or trigger.volume<average*D('1.2'):continue
        if trigger.close>high and all(b.close>=high for b in bars[i+1:-1]) and last.low<=high+tolerance and last.close>high and last.close>last.open:
            return signal('breakout-retest-v1','LONG',bars,min(last.low,high)-D(av)*D('.1'),'Broken resistance retested and reclaimed after a prior close breakout',True)
        if trigger.close<low and all(b.close<=low for b in bars[i+1:-1]) and last.high>=low-tolerance and last.close<low and last.close<last.open:
            return signal('breakout-retest-v1','SHORT',bars,max(last.high,low)+D(av)*D('.1'),'Broken support retested and rejected after a prior close breakout',True)
    return None


def trend_pullback(bars,policy):
    values=summary(bars);closes=[float(b.close) for b in bars];fast=ema(closes,20);slow=ema(closes,50)
    strength=values['adx'];rv=values['relative_volume'];volume=rv is not None and rv>=1.2
    if strength is None or strength<20 or not values['atr']:return None
    if fast[-1]>slow[-1] and closes[-2]<=fast[-2] and closes[-1]>fast[-1] and 40<=values['rsi']<=70:
        return signal('trend-pullback-v1','LONG',bars,min(b.low for b in bars[-5:])-D(values['atr'])*D('.1'),'EMA20 reclaim in an EMA20/50 uptrend with ADX and RSI filters',volume)
    if fast[-1]<slow[-1] and closes[-2]>=fast[-2] and closes[-1]<fast[-1] and 30<=values['rsi']<=60:
        return signal('trend-pullback-v1','SHORT',bars,max(b.high for b in bars[-5:])+D(values['atr'])*D('.1'),'EMA20 rejection in an EMA20/50 downtrend with ADX and RSI filters',volume)
    return None


def bollinger_reversion(bars,policy):
    values=summary(bars);closes=[float(b.close) for b in bars];bands=bollinger(closes);strength=values['adx'];rs=rsi(closes)
    if strength is None or strength>=25 or not values['atr']:return None
    volume=values['relative_volume'] is not None and values['relative_volume']>=1.2
    if closes[-2]<bands[-2]['lower'] and bands[-1]['lower']<closes[-1]<bands[-1]['middle'] and rs[-2]<=35 and rs[-1]<=50:
        return signal('bollinger-reversion-v1','LONG',bars,min(b.low for b in bars[-3:])-D(values['atr'])*D('.1'),'Lower-band excursion followed by closed-bar re-entry in a weak-trend regime',volume)
    if closes[-2]>bands[-2]['upper'] and bands[-1]['middle']<closes[-1]<bands[-1]['upper'] and rs[-2]>=65 and rs[-1]>=50:
        return signal('bollinger-reversion-v1','SHORT',bars,max(b.high for b in bars[-3:])+D(values['atr'])*D('.1'),'Upper-band excursion followed by closed-bar re-entry in a weak-trend regime',volume)
    return None


def smc_retest(bars,policy):
    events=structure_events(bars[:-1])['events'];last=bars[-1];values=summary(bars)
    if not values['atr']:return None
    lower=bars[-min(len(bars),policy.retest_lookback+1)].time
    zones=[e for e in events if e['available_at']>=lower and e['kind'] in ('BULLISH_ORDER_BLOCK','BEARISH_ORDER_BLOCK','BULLISH_FVG','BEARISH_FVG')]
    for zone in reversed(zones):
        up=zone['kind'].startswith('BULLISH')
        structure=[e for e in events if e['available_at']<=zone['available_at'] and e['kind'] in (('BULLISH_BOS','BULLISH_CHOCH') if up else ('BEARISH_BOS','BEARISH_CHOCH'))]
        if not structure:continue
        intermediate=[b for b in bars[:-1] if b.time>zone['available_at']]
        invalid=any(b.low<zone['low'] if up else b.high>zone['high'] for b in intermediate)
        if invalid or last.low>zone['high'] or last.high<zone['low']:continue
        if up and last.low>=zone['low'] and last.close>zone['high'] and last.close>last.open:
            return signal('smc-retest-v1','LONG',bars,zone['low']-D(values['atr'])*D('.1'),'Confirmed bullish structure, causal zone and rejection on retest')
        if not up and last.high<=zone['high'] and last.close<zone['low'] and last.close<last.open:
            return signal('smc-retest-v1','SHORT',bars,zone['high']+D(values['atr'])*D('.1'),'Confirmed bearish structure, causal zone and rejection on retest')
    return None


def session_breakout(bars,policy):
    seconds=INTERVALS[policy.base_interval]
    if policy.opening_range_minutes*60%seconds:raise TradingError('OPENING_RANGE_REQUIRES_SMALLER_BASE_TIMEFRAME')
    result=opening_range(bars,policy.session_open,policy.opening_range_minutes,policy.session_timezone,seconds)
    if result.get('status')!='OBSERVED' or result['direction']=='INSIDE':return None
    # One close must cross the range; continuation bars do not create another signal.
    previous=bars[-2].close
    if result['direction']=='LONG' and previous<=result['high']:
        return signal('opening-range-v1','LONG',bars,result['low'],'Complete opening range and first close above its high')
    if result['direction']=='SHORT' and previous>=result['low']:
        return signal('opening-range-v1','SHORT',bars,result['high'],'Complete opening range and first close below its low')
    return None


DETECTORS={'breakout-retest-v1':breakout_retest,'trend-pullback-v1':trend_pullback,
           'bollinger-reversion-v1':bollinger_reversion,'smc-retest-v1':smc_retest,'opening-range-v1':session_breakout}


class StrategyRouter:
    def __init__(self,policy):self.policy=policy

    def evaluate(self,symbol,base,higher,now):
        policy=self.policy;continuous=policy.asset_class(symbol)=='crypto'
        try:
            bars=closed_bars(base,now,INTERVALS[policy.base_interval],continuous=continuous,minimum=policy.minimum_base_bars)
            age=(utc(now)-bars[-1].time).total_seconds()
            if age<0 or age>policy.maximum_signal_age_seconds:raise TradingError('BASE_TIMEFRAME_STALE')
        except (TradingError,ValueError,TypeError) as exc:return {'symbol':symbol,'status':'NO_TRADE','reason':str(exc),'candidates':[],'diagnostics':[]}
        candidates=[];diagnostics=[]
        for name in policy.strategies:
            try:
                found=RangeBreakout().detect(bars) if name=='range-breakout-v1' else DETECTORS[name](bars,policy)
                if not found:
                    diagnostics.append({'strategy':name,'status':'NO_SETUP'});continue
                found=dict(found);found.setdefault('reason','Two closed bars confirm a volume-supported range breakout')
                found.setdefault('volume_confirmed',True if name=='range-breakout-v1' else False)
                confirm=confirmation(higher,found['side'],now,INTERVALS[policy.higher_interval],continuous=continuous,
                          minimum=policy.minimum_higher_bars,mode='range' if name=='bollinger-reversion-v1' else 'trend')
                if not confirm['confirmed']:
                    diagnostics.append({'strategy':name,'status':'TIMEFRAME_REJECTED','confirmation':confirm});continue
                found.update(multi_timeframe_confirmed=True,regime_compatible=True,confirmation=confirm,
                             signal_id=fingerprint([symbol,name,asdict(policy),bars[-1].time,found['side']]))
                candidates.append(found);diagnostics.append({'strategy':name,'status':'CANDIDATE'})
            except (TradingError,ValueError,TypeError,KeyError) as exc:diagnostics.append({'strategy':name,'status':'UNAVAILABLE','reason':str(exc)})
        conflict=len({c['side'] for c in candidates})>1
        return {'symbol':symbol,'status':'CONFLICT' if conflict else 'CANDIDATES' if candidates else 'NO_TRADE',
                'reason':'OPPOSING_STRATEGY_SIGNALS' if conflict else 'NO_CONFIRMED_SETUP' if not candidates else 'CONFIGURED_PRIORITY_ORDER',
                'candidates':[] if conflict else candidates,'diagnostics':diagnostics,'policy_hash':fingerprint(asdict(policy))}
