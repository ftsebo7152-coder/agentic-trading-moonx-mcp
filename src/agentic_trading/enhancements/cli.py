"""Optional research CLI. Existing scanner/risk/broker behavior is not replaced."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from ..config import Settings, load_private_env
from ..models import Candle, TradingError, dumps, now_utc, utc
from ..storage import Store
from .workspace import ResearchWorkspace


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write_json(path,value):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as handle:
            handle.write(dumps(value)+'\n');handle.flush();os.fsync(handle.fileno())
        os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)


def build_parser():
    parser=argparse.ArgumentParser(prog='agentic-research')
    parser.add_argument('--database',default=os.environ.get('TRADING_DATABASE_URL','state/trading.sqlite'))
    parser.add_argument('--output');parser.add_argument('--now')
    sub=parser.add_subparsers(dest='command',required=True)
    cv=sub.add_parser('validate');cv.add_argument('--input',required=True)
    cv.add_argument('--method',choices=['purged','walk-forward'],default='purged')
    cv.add_argument('--folds',type=int,default=5);cv.add_argument('--test-groups',type=int,default=1)
    cv.add_argument('--embargo-seconds',type=int,default=0)
    cv.add_argument('--train-sessions',type=int,default=60);cv.add_argument('--test-sessions',type=int,default=20)
    cv.add_argument('--expanding',action='store_true')
    for name in ('robustness','costs','book','twap','review','thesis','heat','portfolio'):
        item=sub.add_parser(name);item.add_argument('--input',required=True)
    smc=sub.add_parser('structure');smc.add_argument('--input',required=True)
    smc.add_argument('--opening-range',action='store_true');smc.add_argument('--timezone',default='America/New_York')
    smc.add_argument('--session-open',default='09:30');smc.add_argument('--minutes',type=int,default=30)
    smc.add_argument('--interval-seconds',type=int,default=60)
    collect=sub.add_parser('collect');collect.add_argument('--config',required=True)
    collect.add_argument('--symbols',nargs='+');collect.add_argument('--top100',action='store_true')
    collect.add_argument('--derivatives',action='store_true');collect.add_argument('--news',action='store_true')
    collect.add_argument('--calendar',action='store_true');collect.add_argument('--budget',type=int,default=200)
    cycle=sub.add_parser('cycle');cycle.add_argument('--config',required=True);cycle.add_argument('--bundle',required=True)
    history=sub.add_parser('historical-universe');history.add_argument('--max-age-seconds',type=int,default=86400)
    journal=sub.add_parser('journal');journal.add_argument('--input')
    journal.add_argument('--action',default='status',choices=['status','append','enqueue','claim','complete',
                        'holdout-register','holdout-consume','predict','settle'])
    return parser


def execute(args):
    from .validation import purged_splits,causal_walk_forward,robustness_report,historical_universe
    from .execution_quality import calibrate_costs,book_report,twap_schedule
    from .research import research_review,thesis_update,portfolio_heat
    from .structure import structure_events,opening_range
    now=utc(args.now) if args.now else now_utc()
    data=read_json(args.input) if getattr(args,'input',None) else {}
    data.pop('_label',None)  # Human-readable synthetic fixture label, never a permission.
    if args.command=='validate':
        if args.method=='purged':return purged_splits(data['samples'],args.folds,args.test_groups,args.embargo_seconds)
        return causal_walk_forward(data['samples'],args.train_sessions,args.test_sessions,
                                   embargo_seconds=args.embargo_seconds,expanding=args.expanding)
    if args.command=='robustness':return robustness_report(**data)
    if args.command=='costs':return calibrate_costs(**data)
    if args.command=='book':return book_report(data['book'],data['side'],data['quantity'],now=now)
    if args.command=='twap':return twap_schedule(**data)
    if args.command=='review':return research_review(data['symbol'],data['evidence'],now)
    if args.command=='heat':return portfolio_heat(**data)
    if args.command=='portfolio':
        from .portfolio import portfolio_diagnostics
        return portfolio_diagnostics(now=now,**data)
    if args.command=='structure':
        bars=[Candle.from_dict(row) for row in data['bars']]
        return opening_range(bars,args.session_open,args.minutes,args.timezone,args.interval_seconds) if args.opening_range else structure_events(bars)
    store=Store(args.database)
    if args.command=='collect':
        from .collector import collect_bundle
        from .feeds import FeedClient
        return collect_bundle(Settings.load(args.config),store,now,symbols=args.symbols,top100=args.top100,
                              derivatives=args.derivatives,news=args.news,calendar=args.calendar,client=FeedClient(store,args.budget))
    if args.command=='historical-universe':return historical_universe(store,now,args.max_age_seconds)
    workspace=ResearchWorkspace(store)
    if args.command=='thesis':return thesis_update(workspace,data['symbol'],data['thesis'],data['evidence'],now)
    if args.command=='cycle':
        from ..cli import load_bundle
        from ..orchestrator import AgenticTradingOrchestrator
        settings=Settings.load(args.config);bundle,markets,specs=load_bundle(args.bundle)
        # Original protection/entry gates run first and retain sole authority.
        run=AgenticTradingOrchestrator(settings,store).run(markets,specs,now,macro=bundle.get('macro',{}),
                liquidity=bundle.get('liquidity',{}),validation=bundle.get('validation',{}),asset_identities=bundle.get('asset_identities',{}))
        reviews={symbol:research_review(symbol,bundle.get('research_evidence',[]),now) for symbol in markets}
        artifact=workspace.append('CYCLE_REVIEW',{'run_id':run['run_id'],'reviews':reviews},now)
        return {'run':run,'reviews':reviews,'artifact_id':artifact['id'],'research_changes_entry_decision':False}
    if args.command=='journal':
        action=args.action
        if action=='status':return {'integrity':workspace.verify_chain(),'artifacts':workspace.artifacts()}
        if action=='append':return workspace.append(data['kind'],data['payload'],now)
        if action=='enqueue':return {'job_id':workspace.enqueue(data['kind'],data['payload'],data['due'])}
        if action=='claim':return {'job':workspace.claim(now,**data)}
        if action=='complete':workspace.complete(data['id'],data['lease_token'],now);return {'status':'DONE'}
        if action=='holdout-register':return workspace.register_holdout(**data)
        if action=='holdout-consume':return workspace.consume_holdout(**data)
        if action=='predict':return workspace.register_prediction(now=now,**data)
        if action=='settle':return workspace.settle_prediction(now=now,**data)
    raise TradingError('UNKNOWN_RESEARCH_COMMAND')


def main(argv=None):
    load_private_env();args=build_parser().parse_args(argv)
    try:
        result=execute(args)
        if args.output:write_json(args.output,result)
        print(dumps(result));return 0
    except (TradingError,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print(dumps({'status':'ERROR','error':str(exc)}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
