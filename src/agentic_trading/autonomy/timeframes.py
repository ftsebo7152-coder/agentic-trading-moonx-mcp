"""Closed-bar aggregation and auditable higher-timeframe confirmation."""
from datetime import datetime,timezone,timedelta
from ..models import Candle,TradingError,utc
from ..indicators import ema,adx

INTERVALS={'1m':60,'5m':300,'15m':900,'30m':1800,'1h':3600,'2h':7200,'4h':14400,'1d':86400}


def closed_bars(bars,now,seconds,*,continuous=True,minimum=1,anchor=0):
    if seconds<1 or minimum<1:raise TradingError('INVALID_TIMEFRAME')
    result=[b for b in bars if b.time<=utc(now)]
    if len(result)<minimum:raise TradingError('TIMEFRAME_HISTORY_INSUFFICIENT')
    if any(a.time>=b.time for a,b in zip(result,result[1:])):raise TradingError('DUPLICATE_OR_UNORDERED_TIMEFRAME')
    if any((b.time.timestamp()-anchor)%seconds for b in result):raise TradingError('TIMEFRAME_ALIGNMENT_INVALID')
    tail=result[-minimum:]
    if continuous and any((b.time-a.time).total_seconds()!=seconds for a,b in zip(tail,tail[1:])):
        raise TradingError('TIMEFRAME_GAP')
    return result


def resample(bars,source_seconds,target_seconds,now,*,anchor=0):
    if target_seconds<=source_seconds or target_seconds%source_seconds:raise TradingError('INVALID_RESAMPLE_RATIO')
    data=closed_bars(bars,now,source_seconds,continuous=False,anchor=anchor)
    buckets={};needed=target_seconds//source_seconds
    for bar in data:
        stamp=int(bar.time.timestamp())
        end=((stamp-anchor-1)//target_seconds+1)*target_seconds+anchor
        buckets.setdefault(end,[]).append(bar)
    output=[];dropped=[]
    for stamp,rows in sorted(buckets.items()):
        expected=[stamp-target_seconds+source_seconds*(i+1) for i in range(needed)]
        if stamp>utc(now).timestamp() or [int(r.time.timestamp()) for r in rows]!=expected:
            dropped.append(stamp);continue
        output.append(Candle(datetime.fromtimestamp(stamp,timezone.utc),rows[0].open,max(r.high for r in rows),
                             min(r.low for r in rows),rows[-1].close,sum(r.volume for r in rows)))
    return {'bars':output,'dropped_incomplete_buckets':dropped,'method':'COMPLETE_CLOSED_BUCKETS_ONLY'}


def confirmation(bars,side,now,seconds,*,continuous=True,minimum=60,anchor=0,mode='trend'):
    try:
        data=closed_bars(bars,now,seconds,continuous=continuous,minimum=minimum,anchor=anchor)
        last=data[-1];expected=int((utc(now).timestamp()-anchor)//seconds)*seconds+anchor
        if int(last.time.timestamp())!=expected:raise TradingError('HIGHER_TIMEFRAME_STALE')
        closes=[float(b.close) for b in data];fast=ema(closes,20)[-1];slow=ema(closes,50)[-1];strength=adx(data)[-1]
        if fast is None or slow is None or strength is None:raise TradingError('TIMEFRAME_INDICATORS_INSUFFICIENT')
        direction='LONG' if fast>slow and closes[-1]>slow else 'SHORT' if fast<slow and closes[-1]<slow else 'NEUTRAL'
        matches=(direction==side) if mode=='trend' else strength<25 and direction in (side,'NEUTRAL')
        return {'confirmed':matches,'mode':mode,'direction':direction,'asof':last.time,'ema20':fast,'ema50':slow,'adx14':strength,
                'reason':'CONFIRMED' if matches else 'HIGHER_TIMEFRAME_CONFLICT','bars':len(data)}
    except (TradingError,ValueError,TypeError) as exc:
        return {'confirmed':False,'reason':str(exc),'mode':mode}
