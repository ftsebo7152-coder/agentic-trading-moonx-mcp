from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from agentic_trading.config import Settings
from agentic_trading.market_data import CoinMarketCapUniverse
from agentic_trading.models import Mode, TradingError
from agentic_trading.orchestrator import AgenticTradingOrchestrator
from agentic_trading.storage import Store
from agentic_trading.universe import resolve_universe, identity_error
from tests.test_engine import NOW, SPEC, plan, bar


class Client:
    def __init__(self):
        self.rows=[dict(id=i,symbol=f"C{i}",name=f"Coin {i}",slug=f"coin-{i}",
                        cmc_rank=i,tags=[],quote={"USD":{"price":1}}) for i in range(1,101)]

    def get(self,url,headers):
        return {"status":{"error_code":0},"data":self.rows}


class UniverseTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'test.sqlite')
        self.settings=Settings(watchlist=("BTC","PUMP","HOOD"),universe="cmc_top100")
        self.client=Client()
        self.key=patch.dict(os.environ,{"CMC_API_KEY":"TEST_ONLY"});self.key.start();self.addCleanup(self.key.stop)

    def resolve(self):
        return resolve_universe(self.settings,self.store,NOW,CoinMarketCapUniverse(self.client))

    def test_union_keeps_pinned_outside_top100(self):
        result=self.resolve()
        self.assertEqual(result['status'],'CMC_TOP100_PLUS_PINNED')
        self.assertEqual(len(result['assets']),100)
        self.assertEqual(len(result['symbols']),103)
        self.assertIn('PUMP',result['symbols'])

    def test_no_key_uses_public_api(self):
        with patch.dict(os.environ,{},clear=True):result=self.resolve()
        self.assertEqual(result['status'],'CMC_TOP100_PLUS_PINNED')
        self.assertEqual(result['access'],'public')
        self.assertEqual(len(result['assets']),100)

    def test_public_v3_normalized_without_sending_existing_key(self):
        for row in self.client.rows:
            row['quote']=[{'symbol':'EUR','price':2},{'symbol':'USD','price':1}]
        raw={'status':{'error_code':'0','timestamp':'2026-10-23T12:00:00Z'},'data':self.client.rows}
        with patch.object(self.client,'get',return_value=raw) as request:
            result=self.resolve()
        url,headers=request.call_args.args
        self.assertIn('/public-api/v3/cryptocurrency/listings/latest?',url)
        self.assertIn('limit=100',url)
        self.assertEqual(headers,{})
        self.assertEqual(result['assets'][0]['quote']['symbol'],'USD')
        self.assertEqual(result['provider_timestamp'],raw['status']['timestamp'])

    def test_authenticated_mode_is_explicit_and_preserved(self):
        with patch.object(self.client,'get',wraps=self.client.get) as request:
            result=CoinMarketCapUniverse(self.client,access='authenticated').top100(self.store,NOW)
        url,headers=request.call_args.args
        self.assertNotIn('/public-api/',url)
        self.assertEqual(headers,{'X-CMC_PRO_API_KEY':'TEST_ONLY'})
        self.assertEqual(result['access'],'authenticated')
        with patch.dict(os.environ,{},clear=True),self.assertRaises(TradingError):
            CoinMarketCapUniverse(self.client,access='authenticated').top100(self.store,NOW)

    def test_invalid_public_status_and_partial_results_rejected(self):
        for raw in [
            {'status':{'error_code':'1008'},'data':self.client.rows},
            {'status':{'error_code':'0'},'data':self.client.rows[:99]},
            {'data':self.client.rows},
            {'status':{'error_code':'0'},'data':{}},
        ]:
            with self.subTest(raw_type=type(raw)),patch.object(self.client,'get',return_value=raw):
                self.assertEqual(self.resolve()['status'],'FALLBACK_PINNED_ONLY')

    def test_invalid_public_quotes_rejected(self):
        for quote in [[],[{'symbol':'EUR','price':1}],
                      [{'symbol':'USD','price':1},{'symbol':'USD','price':2}],
                      [{'symbol':'USD','price':None}]]:
            self.client.rows[0]['quote']=quote
            self.assertEqual(self.resolve()['status'],'FALLBACK_PINNED_ONLY')

    def test_network_failure_does_not_use_stale_snapshot(self):
        self.resolve()
        with patch.object(self.client,'get',side_effect=TradingError('network')):
            result=self.resolve()
        self.assertEqual(result['status'],'FALLBACK_PINNED_ONLY')
        self.assertEqual(result['assets'],[])

    def test_duplicates_and_stablecoins_are_research_only(self):
        self.client.rows[0]['symbol']='DUP';self.client.rows[1]['symbol']='DUP'
        self.client.rows[2]['tags']=['stablecoin']
        result=self.resolve()
        self.assertEqual(result['excluded']['DUP'],'AMBIGUOUS_CMC_IDENTITY')
        self.assertEqual(result['excluded']['C3'],'STABLECOIN_RESEARCH_ONLY')
        self.assertEqual(len(result['assets']),100)

    def test_pump_homonym_and_hood_crypto_cannot_override_pins(self):
        self.client.rows[0]['symbol']='PUMP'
        self.client.rows[1]['symbol']='HOOD'
        result=self.resolve()
        self.assertEqual(set(result['excluded']),{'PUMP','HOOD'})

    def test_identity_must_match_id_or_canonical_pin(self):
        result=self.resolve()
        self.assertEqual(identity_error('C1',result,{'cmc_id':99}),'CMC_IDENTITY_UNVERIFIED')
        self.assertIsNone(identity_error('C1',result,{'cmc_id':1}))
        self.assertIsNone(identity_error('PUMP',result,{'cmc_slug':'pump-fun'}))
        self.assertEqual(identity_error('PUMP',result,{'cmc_slug':'other'}),'PINNED_IDENTITY_UNVERIFIED')
        self.assertIsNone(identity_error('HOOD',result,{'asset_class':'equity','exchange':'NASDAQ','symbol':'HOOD'}))
        self.assertEqual(identity_error('HOOD',result,{'asset_class':'crypto'}),'HOOD_EQUITY_IDENTITY_UNVERIFIED')

    def test_bad_ranking_rejected(self):
        self.client.rows[-1]['cmc_rank']=101
        self.assertEqual(self.resolve()['status'],'FALLBACK_PINNED_ONLY')

    def test_history_does_not_fetch_current_ranking(self):
        with patch.object(self.client,'get',side_effect=AssertionError('must not call')):
            result=resolve_universe(replace(self.settings,mode=Mode.BACKTEST),self.store,NOW,CoinMarketCapUniverse(self.client))
        self.assertEqual(result['status'],'HISTORICAL_UNIVERSE_REQUIRED')

    def test_scan_actually_uses_resolved_universe_and_reports_missing_data(self):
        engine=AgenticTradingOrchestrator(self.settings,self.store)
        with patch('agentic_trading.universe.CoinMarketCapUniverse',return_value=CoinMarketCapUniverse(self.client)):
            result=engine.run({}, {}, NOW,macro={},liquidity={},validation={})
        self.assertEqual(len(result['results']),103)
        self.assertTrue(all(r['status']=='NO_TRADE' for r in result['results']))
        self.assertIn('C100',{r['symbol'] for r in result['results']})

    def test_removed_position_still_gets_stop_protection(self):
        engine=AgenticTradingOrchestrator(Settings(watchlist=('BTC',)),self.store)
        opened=engine.paper.open(plan(),SPEC,NOW,strategy_validated=True,blackout=False,liquidity_ok=True)
        self.assertEqual(opened['status'],'SIMULATED_FILLED')
        engine=AgenticTradingOrchestrator(Settings(watchlist=('ETH',)),self.store)
        engine.run({'BTC':[bar(low=97,high=101,close=99)]},{'BTC':SPEC},NOW+timedelta(hours=1),macro={},liquidity={},validation={})
        positions=self.store.report('local-paper')['positions']
        self.assertEqual(positions[0]['status'],'CLOSED')

    def test_default_paper_includes_every_requested_asset(self):
        root=Path(__file__).resolve().parents[1]
        settings=Settings.load(root/'configs/paper.json')
        self.assertEqual(settings.universe,'cmc_top100')
        self.assertTrue({'BTC','ETH','SOL','INJ','TRX','PUMP','XRP','BNB','HYPE','UNI','AVAX','AAVE','POL','ALGO','HOOD'}<=set(settings.watchlist))


if __name__=='__main__':unittest.main()
