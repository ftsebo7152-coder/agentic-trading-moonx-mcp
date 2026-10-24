from dataclasses import replace
from datetime import datetime,timedelta,timezone
from math import sin
import unittest
from unittest.mock import patch
from agentic_trading.models import Candle,TradingError
from agentic_trading.indicators import ema
from agentic_trading.autonomy.timeframes import closed_bars,resample,confirmation
from agentic_trading.autonomy.policy import StrategyPolicy
from agentic_trading.autonomy.strategies import StrategyRouter,breakout_retest,trend_pullback,bollinger_reversion,smc_retest,session_breakout
from tests.autonomy_helpers import runtime_bundle

START=datetime(2026,10,1,tzinfo=timezone.utc)


def bars(values,seconds=3600):
    return [Candle(START+timedelta(seconds=i*seconds),v,v+.5,v-.5,v,100) for i,v in enumerate(values)]


def mirror(data):return [Candle(b.time,200-b.open,200-b.low,200-b.high,200-b.close,b.volume) for b in data]


class TimeframeTests(unittest.TestCase):
    def test_resample_uses_complete_buckets(self):
        data=[Candle(START+timedelta(hours=i),100,102,99,101,10) for i in range(1,9)]
        result=resample(data,3600,14400,START+timedelta(hours=8))
        self.assertEqual(len(result['bars']),2);self.assertEqual(result['bars'][0].volume,40)

    def test_partial_bucket_and_future_data_excluded(self):
        data=[Candle(START+timedelta(hours=i),100,102,99,101,10) for i in range(1,9)]
        result=resample(data,3600,14400,START+timedelta(hours=7))
        self.assertEqual(len(result['bars']),1);self.assertTrue(result['dropped_incomplete_buckets'])

    def test_gap_not_filled(self):
        data=[Candle(START+timedelta(hours=i),100,102,99,101,10) for i in (1,2,4)]
        self.assertEqual(resample(data,3600,14400,START+timedelta(hours=4))['bars'],[])
        with self.assertRaisesRegex(TradingError,'GAP'):closed_bars(data,START+timedelta(hours=4),3600,minimum=3)

    def test_duplicate_or_wrong_alignment_rejected(self):
        data=bars([100,101,102])
        with self.assertRaises(TradingError):closed_bars(data+[data[-1]],data[-1].time,3600)
        with self.assertRaisesRegex(TradingError,'ALIGNMENT'):closed_bars([Candle(START+timedelta(seconds=1),100,101,99,100,1)],START+timedelta(hours=1),3600)

    def test_single_required_bar_does_not_compare_to_first(self):
        data=bars([100,101,102]);self.assertEqual(len(closed_bars(data,data[-1].time,3600)),3)

    def test_stale_higher_timeframe_rejected(self):
        p=StrategyPolicy();data,now=runtime_bundle(p)
        high=[Candle.from_dict(r) for r in data['higher_markets']['BTC']]
        self.assertFalse(confirmation(high,'LONG',now+timedelta(hours=4),14400)['confirmed'])

    def test_higher_side_conflict(self):
        data,now=runtime_bundle(StrategyPolicy());high=[Candle.from_dict(r) for r in data['higher_markets']['BTC']]
        self.assertTrue(confirmation(high,'LONG',now,14400)['confirmed'])
        self.assertFalse(confirmation(high,'SHORT',now,14400)['confirmed'])

    def test_future_higher_bars_do_not_change_confirmation(self):
        data,now=runtime_bundle(StrategyPolicy());high=[Candle.from_dict(r) for r in data['higher_markets']['BTC']]
        first=confirmation(high,'LONG',now,14400)
        high.append(Candle(now+timedelta(days=1),1,2,.5,1,100))
        self.assertEqual(first,confirmation(high,'LONG',now,14400))


class PolicyTests(unittest.TestCase):
    def test_unknown_and_duplicate_strategy_rejected(self):
        for names in [('made-up',),('range-breakout-v1','range-breakout-v1')]:
            with self.assertRaises(TradingError):StrategyPolicy(strategies=names)

    def test_higher_interval_must_be_higher(self):
        with self.assertRaises(TradingError):StrategyPolicy(base_interval='4h',higher_interval='1h')

    def test_history_cannot_be_weakened(self):
        with self.assertRaises(TradingError):StrategyPolicy(minimum_higher_bars=20)

    def test_invalid_asset_class_rejected(self):
        with self.assertRaises(TradingError):StrategyPolicy(asset_classes={'HOOD':'token'})


class StrategyTests(unittest.TestCase):
    def test_range_breakout_has_real_higher_confirmation(self):
        p=StrategyPolicy(strategies=('range-breakout-v1',));data,now=runtime_bundle(p)
        base=[Candle.from_dict(r) for r in data['markets']['BTC']];higher=[Candle.from_dict(r) for r in data['higher_markets']['BTC']]
        result=StrategyRouter(p).evaluate('BTC',base,higher,now)
        self.assertEqual(result['status'],'CANDIDATES');self.assertTrue(result['candidates'][0]['multi_timeframe_confirmed'])

    def test_no_higher_history_no_candidate(self):
        p=StrategyPolicy();data,now=runtime_bundle(p);base=[Candle.from_dict(r) for r in data['markets']['BTC']]
        self.assertFalse(StrategyRouter(p).evaluate('BTC',base,[],now)['candidates'])

    def test_base_stale_is_rejected(self):
        p=StrategyPolicy();data,now=runtime_bundle(p)
        result=StrategyRouter(p).evaluate('BTC',[Candle.from_dict(r) for r in data['markets']['BTC']],[],now+timedelta(days=1))
        self.assertEqual(result['reason'],'BASE_TIMEFRAME_STALE')

    def test_breakout_retest_requires_prior_volume_break(self):
        data=bars([100.0]*60)
        data+=[Candle(START+timedelta(hours=60),100,103,99.5,102,200),Candle(START+timedelta(hours=61),101,102,100.4,101.5,100)]
        self.assertEqual(breakout_retest(data,StrategyPolicy())['side'],'LONG')
        self.assertEqual(breakout_retest(mirror(data),StrategyPolicy())['side'],'SHORT')
        data[-2]=Candle(data[-2].time,100,103,99.5,102,10)
        self.assertIsNone(breakout_retest(data,StrategyPolicy()))

    def test_trend_pullback_actual_indicators(self):
        values=[100+.1*i+.4*sin(i) for i in range(80)];level=ema(values,20)[-1]
        found=trend_pullback(bars(values+[level-.1,level+.3]),StrategyPolicy())
        self.assertEqual(found['side'],'LONG');self.assertLess(found['stop_loss'],found['entry'])
        self.assertEqual(trend_pullback(mirror(bars(values+[level-.1,level+.3])),StrategyPolicy())['side'],'SHORT')

    def test_bollinger_reentry_actual_indicators(self):
        found=bollinger_reversion(bars([100+sin(i*1.2) for i in range(80)]+[95,97]),StrategyPolicy())
        self.assertEqual(found['side'],'LONG')
        self.assertEqual(bollinger_reversion(mirror(bars([100+sin(i*1.2) for i in range(80)]+[95,97])),StrategyPolicy())['side'],'SHORT')

    def test_smc_retest_requires_known_zone_and_structure(self):
        data=bars([100.0]*60+[100,102,108,104,103,99,105,110,106])
        data[65]=Candle(data[65].time,100,100.5,98,99,100)
        data.append(Candle(START+timedelta(hours=len(data)),100,102,99.5,101.5,100))
        self.assertEqual(smc_retest(data,StrategyPolicy())['side'],'LONG')
        self.assertEqual(smc_retest(mirror(data),StrategyPolicy())['side'],'SHORT')
        data[-1]=Candle(data[-1].time,100,102,90,101.5,100)
        self.assertIsNone(smc_retest(data,StrategyPolicy()))

    def test_opening_range_requires_compatible_timeframe(self):
        with self.assertRaisesRegex(TradingError,'SMALLER'):session_breakout(bars([100]*60),StrategyPolicy())

    def test_opening_range_first_cross(self):
        start=datetime(2026,10,23,13,30,tzinfo=timezone.utc)
        data=[Candle(start+timedelta(minutes=5*i),100,101,99,100,100) for i in range(-60,7)]
        data.append(Candle(start+timedelta(minutes=35),100,103,99.5,102,100))
        p=StrategyPolicy(strategies=('opening-range-v1',),base_interval='5m',higher_interval='1h')
        self.assertEqual(session_breakout(data,p)['side'],'LONG')
        self.assertEqual(session_breakout(mirror(data),p)['side'],'SHORT')

    def test_future_base_candle_does_not_change_candidates(self):
        p=StrategyPolicy(strategies=('range-breakout-v1',));data,now=runtime_bundle(p)
        base=[Candle.from_dict(r) for r in data['markets']['BTC']];higher=[Candle.from_dict(r) for r in data['higher_markets']['BTC']]
        first=StrategyRouter(p).evaluate('BTC',base,higher,now)
        base.append(Candle(now+timedelta(hours=1),1,2,.5,1,100))
        self.assertEqual(first,StrategyRouter(p).evaluate('BTC',base,higher,now))


if __name__=='__main__':unittest.main()
