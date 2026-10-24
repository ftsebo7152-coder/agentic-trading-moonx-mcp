from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import importlib.util
import json
import unittest
from agentic_trading.config import Settings
from agentic_trading.models import dumps
from agentic_trading.storage import Store
from agentic_trading.demo import scenario
from agentic_trading.orchestrator import AgenticTradingOrchestrator
from agentic_trading.enhancements.cli import main

ROOT=Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)

    def test_cycle_preserves_protective_exit_during_halt(self):
        scene=scenario();db=self.folder/'paper.sqlite';store=Store(db)
        settings=Settings(account='synthetic-cycle',watchlist=('BTC',))
        engine=AgenticTradingOrchestrator(settings,store)
        engine.run({'BTC':scene['bars']},{'BTC':scene['spec']},scene['now'],macro=scene['macro'],
                   liquidity=scene['liquidity'],validation={},synthetic_demonstration=True)
        position=store.report(settings.account)['positions'][0]
        before=position['remaining_quantity'];store.halt(settings.account)
        config=self.folder/'config.json';config.write_text(dumps(asdict(settings)),encoding='utf8')
        spec=asdict(scene['spec']);spec.pop('symbol')
        bundle=self.folder/'bundle.json';bundle.write_text(dumps({'markets':{'BTC':[asdict(b) for b in scene['bars']+scene['exit_bars']]},
              'instruments':{'BTC':spec},'macro':scene['macro'],'liquidity':scene['liquidity'],'validation':{}}),encoding='utf8')
        out=StringIO()
        with redirect_stdout(out):code=main(['--database',str(db),'--now',scene['exit_bars'][-1].time.isoformat(),
                   'cycle','--config',str(config),'--bundle',str(bundle)])
        self.assertEqual(code,0)
        positions=store.report(settings.account)['positions']
        self.assertEqual(positions[0]['status'],'CLOSED');self.assertEqual(len(positions),1)
        self.assertFalse(json.loads(out.getvalue())['research_changes_entry_decision'])

    def test_cycle_refuses_live_mode(self):
        config=self.folder/'live.json';config.write_text('{"mode":"LIVE_EXECUTION","watchlist":["BTC"]}',encoding='utf8')
        bundle=self.folder/'bundle.json';bundle.write_text('{"markets":{},"instruments":{}}',encoding='utf8')
        with redirect_stderr(StringIO()):
            self.assertEqual(main(['--database',str(self.folder/'db.sqlite'),'cycle','--config',str(config),'--bundle',str(bundle)]),2)

    def installer(self):
        spec=importlib.util.spec_from_file_location('update_master_skill',ROOT/'scripts/update_master_skill.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_skill_installer_idempotent_and_preserves_custom_files(self):
        target=self.folder/'agentic-trading-master';target.mkdir();(target/'custom.txt').write_text('keep',encoding='utf8')
        module=self.installer();first=module.update(target);second=module.update(target)
        self.assertTrue(first['updated_files']);self.assertEqual(second['updated_files'],[])
        self.assertEqual((target/'custom.txt').read_text(encoding='utf8'),'keep')
        self.assertEqual((target/'SKILL.md').read_bytes(),(ROOT/'.agents/skills/agentic-trading-master/SKILL.md').read_bytes())

    def test_skill_installer_backs_up_prior_content(self):
        target=self.folder/'agentic-trading-master';target.mkdir();(target/'SKILL.md').write_text('old',encoding='utf8')
        result=self.installer().update(target)
        self.assertEqual(len(result['backups']),1);self.assertEqual(Path(result['backups'][0]).read_text(encoding='utf8'),'old')

    def test_skill_installer_rejects_unrelated_directory(self):
        with self.assertRaises(ValueError):self.installer().update(self.folder/'unrelated')


if __name__=='__main__':unittest.main()
