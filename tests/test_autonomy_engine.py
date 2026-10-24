from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import os,unittest
from unittest.mock import patch
from agentic_trading.models import Candle,Mode,TradingError,D
from agentic_trading.config import Settings
from agentic_trading.storage import Store
from agentic_trading.risk import Costs
from agentic_trading.autonomy.policy import StrategyPolicy
from agentic_trading.autonomy.engine import AutonomousPaperEngine,liquidity_check
from agentic_trading.autonomy.runtime import RuntimeLease,run_cycle,FencedRisk
from tests.autonomy_helpers import runtime_bundle,KEY


class EngineFixture:
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(Path(self.tmp.name)/'db.sqlite')
        self.settings=Settings(watchlist=('BTC','XAUUSD'));self.policy=StrategyPolicy(strategies=('range-breakout-v1',))
        self.bundle,self.now=runtime_bundle(self.policy);self.engine=AutonomousPaperEngine(self.settings,self.policy,self.store)
        self.env=patch.dict(os.environ,{'TRADING_VALIDATION_HMAC_KEY':KEY});self.env.start();self.addCleanup(self.env.stop)

class EngineTests(EngineFixture,unittest.TestCase):
    def test_both_assets_share_one_paper_account(self):
        report=self.engine.scan(self.bundle,self.now)
        self.assertEqual([r['status'] for r in report['results']],['SIMULATED_FILLED','SIMULATED_FILLED'])
        positions=self.store.report(self.settings.account)['positions']
        self.assertEqual(len(positions),2);self.assertLessEqual(sum(D(p['remaining_risk']) for p in positions),30)

    def test_live_mode_rejected(self):
        with self.assertRaisesRegex(TradingError,'PAPER_ONLY'):AutonomousPaperEngine(replace(self.settings,mode=Mode.LIVE_EXECUTION),self.policy,self.store)

    def test_no_attestation_blocks_entry(self):
        self.bundle['validation']={}
        result=self.engine.scan(self.bundle,self.now)
        self.assertTrue(all('STRATEGY_NOT_VALIDATED' in r['reasons'] for r in result['results']))

    def test_policy_change_invalidates_old_attestation(self):
        changed=replace(self.policy,retest_lookback=11)
        engine=AutonomousPaperEngine(self.settings,changed,self.store)
        result=engine.scan(self.bundle,self.now)
        self.assertTrue(all('STRATEGY_NOT_VALIDATED' in r['reasons'] for r in result['results']))

    def test_basis_change_invalidates_old_attestation(self):
        for row in self.bundle['market_metadata'].values():row['basis']='DIFFERENT_VENUE'
        self.assertTrue(all('STRATEGY_NOT_VALIDATED' in r['reasons'] for r in self.engine.scan(self.bundle,self.now)['results']))

    def test_unverified_specs_block(self):
        self.bundle['instruments']['BTC']['specs_verified']=False
        self.assertIn('CONTRACT_SPECS_UNVERIFIED',self.engine.scan(self.bundle,self.now)['results'][0]['reasons'])

    def test_unknown_calendar_blocks(self):
        self.bundle['macro']['coverage_until']=None
        self.assertTrue(all('MACRO_BLACKOUT_OR_UNKNOWN' in r['reasons'] for r in self.engine.scan(self.bundle,self.now)['results']))

    def test_missing_fundamental_observations_cannot_be_offset_by_technical_score(self):
        self.bundle['macro']['observations']=[]
        self.assertTrue(all('MACRO_BLACKOUT_OR_UNKNOWN' in r['reasons'] for r in self.engine.scan(self.bundle,self.now)['results']))

    def test_missing_liquidity_blocks(self):
        self.bundle['liquidity']={}
        self.assertTrue(all('LIQUIDITY_UNKNOWN_OR_LOW' in r['reasons'] for r in self.engine.scan(self.bundle,self.now)['results']))

    def test_future_metadata_blocks(self):
        self.bundle['market_metadata']['BTC']['fetched_at']=self.now+timedelta(seconds=1)
        self.assertEqual(self.engine.scan(self.bundle,self.now)['results'][0]['reason'],'MARKET_DATA_NOT_AVAILABLE_YET')

    def test_missing_higher_data_cannot_get_mtf_points(self):
        self.bundle['higher_markets']={}
        self.assertTrue(all(r['status']=='NO_TRADE' for r in self.engine.scan(self.bundle,self.now)['results']))

    def test_repeat_signal_is_not_duplicated(self):
        self.engine.scan(self.bundle,self.now);self.engine.scan(self.bundle,self.now)
        self.assertEqual(len(self.store.report(self.settings.account)['positions']),2)

    def test_global_halt_blocks_new_strategies(self):
        self.store.halt(self.settings.account)
        result=self.engine.scan(self.bundle,self.now)
        self.assertTrue(all('KILL_SWITCH' in r['reasons'] for r in result['results']))

    def test_monitor_runs_when_entries_disabled(self):
        self.engine.scan(self.bundle,self.now)
        minute=Candle(self.now+timedelta(minutes=1),102.5,103,98,100,100)
        self.bundle['monitor_markets']={s:[minute] for s in self.settings.watchlist}
        self.engine.scan(self.bundle,self.now+timedelta(minutes=1),entries=False)
        self.assertTrue(all(p['status']=='CLOSED' for p in self.store.report(self.settings.account)['positions']))

    def test_removed_symbol_still_gets_stop_management(self):
        self.engine.scan(self.bundle,self.now)
        minute=Candle(self.now+timedelta(minutes=1),102.5,103,98,100,100)
        self.bundle['monitor_markets']={s:[minute] for s in self.settings.watchlist}
        smaller=AutonomousPaperEngine(replace(self.settings,watchlist=('XAUUSD',)),self.policy,self.store)
        smaller.scan(self.bundle,self.now+timedelta(minutes=1))
        btc=next(p for p in self.store.report(self.settings.account)['positions'] if p['symbol']=='BTC')
        self.assertEqual(btc['status'],'CLOSED')

    def test_monitor_gap_survives_restart_and_needs_review(self):
        self.engine.scan(self.bundle,self.now)
        minute=Candle(self.now+timedelta(minutes=5),102.5,103,100,101,100)
        self.bundle['monitor_markets']={'BTC':[minute]}
        outcome=self.engine.protect(self.bundle,self.now+timedelta(minutes=5))
        self.assertTrue(any(i['reason']=='UNREVIEWED_PAPER_HISTORY_GAP' for i in outcome['issues']))
        restarted=AutonomousPaperEngine(self.settings,self.policy,self.store)
        self.assertFalse(restarted.protect({},self.now+timedelta(minutes=5))['new_entries_allowed'])
        with self.assertRaises(TradingError):restarted.acknowledge_gap('BTC','reviewed',False)
        restarted.acknowledge_gap('BTC','Operator checked missing minute history',True)
        with self.store.transaction() as tx:self.assertIsNone(tx.execute('SELECT * FROM autonomy_monitor_gaps WHERE symbol=?',('BTC',)).fetchone())

    def test_zero_cfd_volume_not_fabricated_or_required_as_crypto_volume(self):
        row={**self.bundle['liquidity']['XAUUSD']};row.pop('volume_24h');row.pop('depth_usd')
        self.assertTrue(liquidity_check(row,'metal',self.now,3900,Costs()))
        self.assertFalse(liquidity_check(row,'crypto',self.now,3900,Costs()))

    def test_spread_above_cost_model_blocks(self):
        row={**self.bundle['liquidity']['BTC'],'bid':100,'ask':101}
        self.assertFalse(liquidity_check(row,'crypto',self.now,3900,Costs()))

    def test_usdt_parity_not_assumed(self):
        row={**self.bundle['liquidity']['BTC'],'quote_currency':'USDT'}
        self.assertFalse(liquidity_check(row,'crypto',self.now,3900,Costs()))


class LeaseTests(EngineFixture,unittest.TestCase):
    def test_exclusive_account_lease(self):
        first=RuntimeLease(self.store,self.settings.account);first.acquire(self.now)
        with self.assertRaisesRegex(TradingError,'ALREADY_RUNNING'):RuntimeLease(self.store,self.settings.account).acquire(self.now)

    def test_expiry_takeover_and_old_release_fenced(self):
        first=RuntimeLease(self.store,self.settings.account,30);first.acquire(self.now)
        second=RuntimeLease(self.store,self.settings.account,30);second.acquire(self.now+timedelta(seconds=31))
        first.release();self.assertTrue(second.valid(self.now+timedelta(seconds=32)))
        with self.assertRaisesRegex(TradingError,'LOST'):first.renew(self.now+timedelta(seconds=32))

    def test_replay_safe_cycle_ledger(self):
        lease=RuntimeLease(self.store,self.settings.account);lease.acquire(self.now)
        first=run_cycle(self.engine,self.bundle,self.now,lease=lease,clock=lambda:self.now)
        second=run_cycle(self.engine,self.bundle,self.now,lease=lease,clock=lambda:self.now)
        self.assertEqual(second['status'],'ALREADY_PROCESSED');self.assertEqual(second['cycle_id'],first['cycle_id'])
        self.assertEqual(len(self.store.report(self.settings.account)['positions']),2)

    def test_fence_inside_risk_transaction(self):
        lease=RuntimeLease(self.store,self.settings.account,30);lease.acquire(self.now)
        self.engine.paper.risk=FencedRisk(self.engine.paper.risk,lease,clock=lambda:self.now+timedelta(seconds=31))
        result=self.engine.scan(self.bundle,self.now)
        self.assertTrue(all('PAPER_RUNTIME_LEASE_LOST' in r['reasons'] for r in result['results']))
        self.assertEqual(self.store.report(self.settings.account)['positions'],[])


if __name__=='__main__':unittest.main()
