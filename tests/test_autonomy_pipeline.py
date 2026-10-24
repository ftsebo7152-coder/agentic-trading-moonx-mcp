from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from unittest.mock import patch,AsyncMock
import asyncio,json,os,unittest
from agentic_trading.models import Candle,TradingError,now_utc,dumps
from agentic_trading.config import Settings
from agentic_trading.storage import Store
from agentic_trading.risk import Costs
from agentic_trading.autonomy.policy import StrategyPolicy
from agentic_trading.autonomy.collection import public_series,collect_moonx,merge_bundles,empty_bundle
from agentic_trading.autonomy.replay import replay,walk_forward
from agentic_trading.autonomy.runtime import collect,worker,RuntimeLease,run_cycle,HealthLog
from agentic_trading.autonomy.engine import AutonomousPaperEngine
from agentic_trading.autonomy.preflight import preflight
from agentic_trading.autonomy.cli import main
from agentic_trading.autonomy.demo import synthetic_bundle
from agentic_trading.enhancements.feeds import FeedClient
from tests.autonomy_helpers import runtime_bundle,KEY


class PipelineFixture:
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.store=Store(self.folder/'db.sqlite');self.settings=Settings(watchlist=('BTC','XAUUSD'))
        self.policy=StrategyPolicy(strategies=('range-breakout-v1',));self.bundle,self.now=runtime_bundle(self.policy)


class CollectionTests(PipelineFixture,unittest.TestCase):
    def test_explicit_interval_and_closed_candles(self):
        client=FeedClient(self.store,clock=lambda:self.now)
        stamp=int((self.now-timedelta(hours=4)).timestamp()*1000)
        raw={'code':'0','data':[[str(stamp),'100','102','99','101','10','0','0','1'],
                              [str(stamp+14400000),'101','103','100','102','10','0','0','0']]}
        with patch.object(client,'get',return_value=raw) as request:
            result=public_series(client,'BTC','4h',self.now)
        self.assertIn('bar=4H',request.call_args.args[0]);self.assertEqual(len(result['bars']),1)

    def test_provider_is_not_mixed_across_timeframes(self):
        client=FeedClient(self.store)
        with patch.object(client,'get',side_effect=TradingError('FAIL')) as request:
            with self.assertRaises(TradingError):public_series(client,'BTC','4h',self.now,provider='OKX_SPOT')
        self.assertEqual(request.call_count,1)

    def test_bybit_base_fallback(self):
        client=FeedClient(self.store);stamp=int((self.now-timedelta(hours=1)).timestamp()*1000)
        raw={'retCode':0,'result':{'list':[[str(stamp),'100','102','99','101','10']]}}
        with patch.object(client,'get',side_effect=[TradingError('FAIL'),raw]):result=public_series(client,'BTC','1h',self.now)
        self.assertEqual(result['source'],'BYBIT_SPOT')

    def test_moonx_collection_calls_read_tools_only_and_preserves_zero_volume(self):
        class Broker:
            def __init__(self,now):self.calls=[];self.now=now
            async def read(self,name,args):
                self.calls.append((name,args));seconds=3600 if args['interval']=='1h' else 14400
                return {'symbol':args['symbol'],'interval':args['interval'],'market':'forex','count':1,
                        'candles':[{'time':int((self.now-timedelta(seconds=seconds)).timestamp()*1000),
                                    'open':100,'high':102,'low':99,'close':101,'volume':0}]}
        broker=Broker(self.now)
        result=asyncio.run(collect_moonx(self.settings,self.policy,self.now,broker,symbols=['XAUUSD']))
        self.assertTrue(all(name=='get_candles' for name,args in broker.calls));self.assertEqual(len(broker.calls),2)
        self.assertEqual(result['markets']['XAUUSD'][0].volume,0)
        self.assertFalse(result['instruments']['XAUUSD']['specs_verified'])

    def test_moonx_identity_mismatch_rejected(self):
        broker=type('Broker',(),{})();broker.read=AsyncMock(return_value={'symbol':'WRONG','interval':'1h','market':'forex'})
        result=asyncio.run(collect_moonx(self.settings,self.policy,self.now,broker,symbols=['XAUUSD']))
        self.assertIn('XAUUSD',result['collection']['failures'])

    def test_hood_not_substituted_with_a_crypto(self):
        broker=type('Broker',(),{})();broker.read=AsyncMock()
        result=asyncio.run(collect_moonx(self.settings,self.policy,self.now,broker,symbols=['HOOD']))
        broker.read.assert_not_called();self.assertIn('HOOD',result['collection']['failures'])

    def test_secondary_context_does_not_overwrite_primary_crypto_feed(self):
        first=empty_bundle(self.now);second=empty_bundle(self.now,{'liquidity':{'BTC':{'source':'OLD_CONTEXT'}}})
        first['markets']['BTC']=[];first['liquidity']['BTC']={'source':'FRESH_PRIMARY'}
        second['markets']['XAUUSD']=[]
        self.assertEqual(merge_bundles(first,second)['liquidity']['BTC']['source'],'FRESH_PRIMARY')

    def test_external_file_requires_explicit_data_section(self):
        with self.assertRaises(TradingError):collect(self.settings,self.policy,self.store,'file',self.now,context={})
        result=collect(self.settings,self.policy,self.store,'file',self.now,context={'external_data':self.bundle})
        self.assertIn('XAUUSD',result['markets'])


class ReplayTests(PipelineFixture,unittest.TestCase):
    def test_multi_asset_replay_closes_all_simulated_trades(self):
        result=replay(synthetic_bundle(),self.settings,self.policy)
        self.assertEqual(len(result['trades']),2)
        self.assertTrue(all(p['status']=='CLOSED' for p in result['trades']))
        self.assertTrue(all(d['entry_model']=='NEXT_BAR_OPEN_PLUS_ADVERSE_COSTS' for d in result['decisions']))
        self.assertFalse(result['live_eligible'])

    def test_unknown_contract_specs_are_not_promoted(self):
        data=synthetic_bundle()
        for spec in data['instruments'].values():spec['specs_verified']=False
        self.assertEqual(replay(data,self.settings,self.policy)['metrics']['trades'],0)

    def test_current_cmc_list_does_not_enable_historical_top100(self):
        result=replay(synthetic_bundle(),replace(self.settings,universe='cmc_top100'),self.policy)
        self.assertEqual(result['metrics']['trades'],0)
        self.assertIn('HISTORICAL_UNIVERSE_MISSING_OR_ASSET_ABSENT',result['blocked'])

    def test_future_published_historical_universe_is_not_used(self):
        data=synthetic_bundle();data['historical_universe']=[{'asof':self.now,'available_at':self.now+timedelta(days=10),'symbols':['BTC','XAUUSD']}]
        self.assertEqual(replay(data,replace(self.settings,universe='cmc_top100'),self.policy)['metrics']['trades'],0)

    def test_future_prices_do_not_change_training_replay(self):
        data=synthetic_bundle();end=data['markets']['BTC'][63]['time']
        first=replay(data,self.settings,self.policy,end=end)
        for symbol,rows in data['markets'].items():
            for row in rows[64:]:
                for key in ('open','high','low','close'):row[key]*=10
        second=replay(data,self.settings,self.policy,end=end)
        self.assertEqual(first['metrics'],second['metrics'])

    def test_walk_forward_without_enough_trades_abstains(self):
        result=walk_forward(synthetic_bundle(),self.settings,[self.policy],train_sessions=60,test_sessions=3)
        self.assertTrue(result['folds']);self.assertTrue(all(f['status']=='INSUFFICIENT_TRAINING_EVIDENCE' for f in result['folds']))

    def test_walk_forward_rejects_incompatible_timeframes(self):
        with self.assertRaises(TradingError):walk_forward(synthetic_bundle(),self.settings,[self.policy,replace(self.policy,base_interval='5m')],train_sessions=60,test_sessions=3)

    def test_walk_forward_selects_on_training_and_evaluates_separate_test(self):
        data=synthetic_bundle()
        for symbol,rows in data['markets'].items():
            end=rows[-1]['time']
            for index in range(20):rows.append({'time':end+timedelta(hours=index+1),'open':117,'high':118,'low':116,'close':117,'volume':100})
        result=walk_forward(data,self.settings,[self.policy],train_sessions=69,test_sessions=5,minimum_train_trades=1)
        first=result['folds'][0]
        self.assertEqual(first['status'],'EVALUATED_OUT_OF_SAMPLE')
        self.assertLess(first['train_end'],first['test_start'])
        self.assertEqual(first['result']['window']['start'],first['test_start'])

    def test_walk_forward_trial_budget(self):
        with self.assertRaises(TradingError):walk_forward(synthetic_bundle(),self.settings,[self.policy]*11,train_sessions=60,test_sessions=3)


class RuntimeTests(PipelineFixture,unittest.TestCase):
    def test_old_entry_paths_obey_active_account_lease(self):
        with patch.dict(os.environ,{'TRADING_VALIDATION_HMAC_KEY':KEY}):
            engine=AutonomousPaperEngine(self.settings,self.policy,self.store)
            lease=RuntimeLease(self.store,self.settings.account);lease.acquire(now_utc())
            result=engine.scan(self.bundle,self.now)
            self.assertTrue(all('PAPER_ACCOUNT_OWNED_BY_ANOTHER_RUNTIME' in r['reasons'] for r in result['results']))

    def test_once_worker_releases_lease_and_creates_atomic_bundle(self):
        context=self.folder/'context.json';context.write_text('{}',encoding='utf8')
        output=self.folder/'bundle.json'
        with patch('agentic_trading.autonomy.runtime.collect',return_value=self.bundle),redirect_stdout(StringIO()):
            worker(self.settings,self.policy,self.store,source='file',context_path=context,bundle_path=output,once=True)
        self.assertTrue(output.exists())
        with self.store.transaction() as tx:self.assertIsNone(tx.execute('SELECT * FROM autonomy_leases').fetchone())

    def test_collection_failure_is_recorded_and_no_success_exit(self):
        with patch('agentic_trading.autonomy.runtime.collect',side_effect=TradingError('NO_FEED')):
            with self.assertRaisesRegex(TradingError,'ONCE_FAILED'):worker(self.settings,self.policy,self.store,once=True)
        report=self.store.report(self.settings.account)
        self.assertTrue(any(e['kind']=='AUTONOMY_INCIDENT' for e in report['events']));self.assertEqual(report['positions'],[])

    def test_preflight_does_not_make_positions_or_attestations(self):
        with patch.dict(os.environ,{'TRADING_VALIDATION_HMAC_KEY':KEY}):result=preflight(self.settings,self.policy,self.bundle,self.now,Costs())
        self.assertTrue(all(r['status']=='PAPER_INPUTS_QUALIFIED' for r in result['assets']))
        self.assertFalse(result['financial_qualification_created'])

    def test_preflight_rejects_future_metadata(self):
        self.bundle['market_metadata']['BTC']['fetched_at']=self.now+timedelta(days=1)
        result=preflight(self.settings,self.policy,self.bundle,self.now,Costs())
        self.assertIn('MARKET_TIMEFRAME_OR_AVAILABILITY_INVALID',result['assets'][0]['reasons'])

    def test_preflight_includes_dynamic_universe_members(self):
        self.bundle['collection']={'universe':{'requested':'cmc_top100','status':'CMC_TOP100_PLUS_PINNED','asof':self.now,
                                  'symbols':['BTC','XAUUSD','EXTRA'],'identities':{},'excluded':{}}}
        result=preflight(replace(self.settings,universe='cmc_top100'),self.policy,self.bundle,self.now,Costs())
        self.assertEqual(len(result['assets']),3);self.assertFalse(result['all_requested_inputs_qualified'])

    def test_readiness_can_fail_nonzero_without_starting_a_worker(self):
        config=self.folder/'settings.json';policy=self.folder/'policy.json';bundle=self.folder/'bundle.json'
        from dataclasses import asdict
        config.write_text(dumps(asdict(self.settings)),encoding='utf8');policy.write_text(dumps(asdict(self.policy)),encoding='utf8')
        bundle.write_text(dumps(self.bundle),encoding='utf8')
        with redirect_stdout(StringIO()):code=main(['--config',str(config),'--policy',str(policy),'--database',str(self.folder/'cli.sqlite'),
                            '--now',self.now.isoformat(),'check','--bundle',str(bundle),'--require-ready'])
        self.assertEqual(code,3)

    def test_stale_cmc_universe_is_not_used_for_entries(self):
        settings=replace(self.settings,universe='cmc_top100');engine=AutonomousPaperEngine(settings,self.policy,self.store)
        universe={'requested':'cmc_top100','asof':self.now-timedelta(days=1),'symbols':['BTC'],'identities':{},'excluded':{}}
        self.assertEqual(engine.scan(self.bundle,self.now,universe=universe)['results'][0]['reason'],'CURRENT_CMC_UNIVERSE_STALE_OR_MISMATCHED')

    def test_strategy_listing_does_not_load_secrets_or_initialize_database(self):
        with patch('agentic_trading.autonomy.cli.load_private_env',side_effect=AssertionError('No secrets needed')),\
             patch('agentic_trading.autonomy.cli.Store',side_effect=AssertionError('No database needed')),redirect_stdout(StringIO()):
            self.assertEqual(main(['strategies']),0)

    def test_demo_does_not_load_private_configuration_or_initialize_account_database(self):
        with patch('agentic_trading.autonomy.cli.load_private_env',side_effect=AssertionError('No secrets needed')),\
             patch('agentic_trading.autonomy.cli.Store',side_effect=AssertionError('No runtime database needed')),redirect_stdout(StringIO()):
            self.assertEqual(main(['demo']),0)

    def test_repeated_incident_is_not_queued_as_duplicate_notification(self):
        self.store.ensure_account(self.settings.account,self.settings.capital);health=HealthLog(self.store,self.settings.account)
        health.incident('FEED_DOWN',self.now);health.incident('FEED_DOWN',self.now+timedelta(minutes=1))
        state=self.store.report(self.settings.account)
        self.assertEqual(sum(e['kind']=='AUTONOMY_INCIDENT' for e in state['events']),1)
        self.assertEqual(len(state['notifications']),1)
        health.resolve('FEED_DOWN',self.now+timedelta(minutes=2));health.resolve('FEED_DOWN',self.now+timedelta(minutes=3))
        health.incident('FEED_DOWN',self.now+timedelta(minutes=4))
        state=self.store.report(self.settings.account)
        self.assertEqual(sum(e['kind']=='AUTONOMY_INCIDENT' for e in state['events']),2)
        self.assertEqual(sum(e['kind']=='AUTONOMY_RECOVERY' for e in state['events']),1)


if __name__=='__main__':unittest.main()
