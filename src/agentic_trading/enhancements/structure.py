"""Explicit, causal SMC/ICT research definitions; not a validated trading strategy."""
from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from ..models import TradingError,validate_candles


def structure_events(bars,left=2,right=2,order_block_lookback=10):
    validate_candles(bars)
    if min(left,right,order_block_lookback)<1:raise TradingError('INVALID_STRUCTURE_WINDOW')
    events=[];last_high=None;last_low=None;trend=None;broken=set()
    for i,c in enumerate(bars):
        pivot=i-right
        if pivot>=left:
            neighbors=bars[pivot-left:pivot]+bars[pivot+1:i+1];p=bars[pivot]
            if all(p.high>x.high for x in neighbors):
                last_high=(pivot,p.high)
                events.append({'kind':'CONFIRMED_SWING_HIGH','bar':pivot,'available_at':c.time,'level':p.high})
            if all(p.low<x.low for x in neighbors):
                last_low=(pivot,p.low)
                events.append({'kind':'CONFIRMED_SWING_LOW','bar':pivot,'available_at':c.time,'level':p.low})
        if i>=2:
            a=bars[i-2]
            if c.low>a.high:events.append({'kind':'BULLISH_FVG','bar':i,'available_at':c.time,'low':a.high,'high':c.low})
            if c.high<a.low:events.append({'kind':'BEARISH_FVG','bar':i,'available_at':c.time,'low':c.high,'high':a.low})
        for direction,pivot_data in [('bullish',last_high),('bearish',last_low)]:
            if pivot_data is None:continue
            index,level=pivot_data;up=direction=='bullish'
            key=(direction,index)
            sweep=(c.high>level and c.close<level) if up else (c.low<level and c.close>level)
            if sweep and key not in broken:events.append({'kind':'BUY_SIDE_SWEEP' if up else 'SELL_SIDE_SWEEP','bar':i,'available_at':c.time,'level':level})
            crossing=(c.close>level) if up else (c.close<level)
            if crossing and key not in broken:
                kind='CHOCH' if trend is not None and trend!=direction else 'BOS'
                events.append({'kind':direction.upper()+'_'+kind,'bar':i,'available_at':c.time,'level':level})
                broken.add(key);trend=direction
                candidates=[j for j in range(max(0,i-order_block_lookback),i) if (bars[j].close<bars[j].open if up else bars[j].close>bars[j].open)]
                if candidates:
                    j=candidates[-1]
                    events.append({'kind':direction.upper()+'_ORDER_BLOCK','bar':j,'available_at':c.time,'low':bars[j].low,'high':bars[j].high})
    return {'school':'ICT_SMC_EXPLICIT_RESEARCH_DEFINITIONS','events':events,'execution_enabled':False,
            'parameters':{'left':left,'right':right,'order_block_lookback':order_block_lookback},
            'limitations':['Pivot availability is delayed until right-side confirmation.',
                           'Heuristic structures are not statistically validated signals; no mixing of analysis schools or score overrides.']}


def opening_range(bars,session_open='09:30',minutes=30,timezone='America/New_York',interval_seconds=60):
    validate_candles(bars)
    if minutes<1 or interval_seconds<1 or minutes*60%interval_seconds:raise TradingError('INVALID_SESSION_RANGE')
    zone=ZoneInfo(timezone);hour,minute=map(int,session_open.split(':'));local_day=bars[-1].time.astimezone(zone).date()
    start=datetime.combine(local_day,time(hour,minute),tzinfo=zone);end=start+timedelta(minutes=minutes)
    window=[b for b in bars if start<b.time.astimezone(zone)<=end]
    expected=minutes*60//interval_seconds
    times={b.time.astimezone(zone) for b in window}
    if len(window)!=expected or any(start+timedelta(seconds=(i+1)*interval_seconds) not in times for i in range(expected)):
        return {'status':'INSUFFICIENT_DATA','reason':'COMPLETE_SESSION_RANGE_REQUIRED','execution_enabled':False}
    if bars[-1].time.astimezone(zone)<=end:return {'status':'WAIT_FOR_RANGE_CLOSE','execution_enabled':False}
    high=max(b.high for b in window);low=min(b.low for b in window);close=bars[-1].close
    return {'status':'OBSERVED','high':high,'low':low,'direction':'LONG' if close>high else 'SHORT' if close<low else 'INSIDE',
            'range_available_at':end,'signal_available_at':bars[-1].time,'execution_enabled':False,
            'note':'Session calendar/holidays must be verified separately; no automatic entry.'}
