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

    def test_no_key_falls_back_explicitly(self):
        with patch.dict(os.environ,{},clear=True):result=self.resolve()
        self.assertEqual(result['status'],'FALLBACK_PINNED_ONLY')
        self.assertEqual(result['symbols'],list(self.settings.watchlist))
        self.assertEqual(result['assets'],[])

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
