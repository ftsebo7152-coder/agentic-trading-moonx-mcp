"""Command-line entry point for the isolated multi-strategy PAPER system."""
from dataclasses import replace
from pathlib import Path
import argparse,json,os,sys
from ..models import TradingError,utc,now_utc,dumps
from ..config import Settings,load_private_env
from ..storage import Store
from ..risk import Costs
from ..enhancements.cli import write_json
from .policy import StrategyPolicy,STRATEGIES


def parser():
    p=argparse.ArgumentParser(prog='autonomous-paper')
    p.add_argument('--config',default='configs/multi-asset-paper.json');p.add_argument('--policy',default='configs/strategy-policy.json')
    p.add_argument('--database')
    p.add_argument('--output');p.add_argument('--now');p.add_argument('--costs')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('strategies');sub.add_parser('status');sub.add_parser('demo')
    for name in ('scan','check','replay'):
        item=sub.add_parser(name);item.add_argument('--bundle',required=True)
        if name=='check':item.add_argument('--require-ready',action='store_true')
    wf=sub.add_parser('walk-forward');wf.add_argument('--bundle',required=True)
    wf.add_argument('--candidates',required=True);wf.add_argument('--train-sessions',type=int,required=True)
    wf.add_argument('--test-sessions',type=int,required=True);wf.add_argument('--minimum-train-trades',type=int,default=5)
    for name in ('collect','worker'):
        item=sub.add_parser(name);item.add_argument('--source',choices=['public','moonx','hybrid','file'],default='public');item.add_argument('--context')
        if name=='worker':
            item.add_argument('--once',action='store_true');item.add_argument('--bundle-path',default='state/autonomous-latest.json')
            item.add_argument('--monitor-seconds',type=int,default=15);item.add_argument('--refresh-seconds',type=int,default=60)
    gap=sub.add_parser('review-paper-gap');gap.add_argument('--symbol',required=True);gap.add_argument('--reason',required=True)
    gap.add_argument('--operator-confirm',action='store_true')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    if args.command in ('check','scan','collect','worker','status','review-paper-gap'):load_private_env()
    args.database=args.database or os.environ.get('TRADING_DATABASE_URL','state/trading.sqlite')
    try:
        now=utc(args.now) if args.now else now_utc();settings=Settings.load(args.config);policy=StrategyPolicy.load(args.policy)
        if settings.mode.value!='PAPER':raise TradingError('AUTONOMY_IS_PAPER_ONLY')
        costs=Costs(**json.loads(Path(args.costs).read_text(encoding='utf8'))) if args.costs else Costs()
        data=json.loads(Path(args.bundle).read_text(encoding='utf8')) if hasattr(args,'bundle') else None
        store=Store(args.database) if args.command in ('scan','collect','worker','status','review-paper-gap') else None
        if args.command=='strategies':result={'implemented':STRATEGIES,'enabled':policy.strategies,'policy':policy,'financially_validated':False}
        elif args.command=='check':
            from .preflight import preflight
            result=preflight(settings,policy,data,now,costs)
        elif args.command in ('replay','demo'):
            from .replay import replay
            if args.command=='demo':
                from .demo import synthetic_bundle
                data=synthetic_bundle();settings=replace(settings,universe='static',watchlist=('BTC','XAUUSD'))
            result=replay(data,settings,policy,costs=costs)
        elif args.command=='walk-forward':
            from .replay import walk_forward
            candidates=[StrategyPolicy(**v) for v in json.loads(Path(args.candidates).read_text(encoding='utf8'))]
            result=walk_forward(data,settings,candidates,train_sessions=args.train_sessions,test_sessions=args.test_sessions,minimum_train_trades=args.minimum_train_trades)
        elif args.command=='collect':
            from .runtime import collect,load_context
            result=collect(settings,policy,store,args.source,now,context=load_context(args.context))
        elif args.command=='worker':
            from .runtime import worker
            if args.now:raise TradingError('WORKER_USES_CURRENT_CLOCK_ONLY')
            worker(settings,policy,store,source=args.source,context_path=args.context,bundle_path=args.bundle_path,
                   once=args.once,monitor_seconds=args.monitor_seconds,refresh_seconds=args.refresh_seconds,costs=costs)
            return 0
        elif args.command=='status':
            from .runtime import runtime_status
            store.ensure_account(settings.account,settings.capital);result=runtime_status(store,settings.account,now)
        else:
            from .engine import AutonomousPaperEngine
            engine=AutonomousPaperEngine(settings,policy,store,costs=costs)
            if args.command=='review-paper-gap':
                engine.acknowledge_gap(args.symbol,args.reason,args.operator_confirm);result={'status':'PAPER_GAP_REVIEW_RECORDED','symbol':args.symbol}
            else:
                from .runtime import RuntimeLease,run_cycle
                lease=RuntimeLease(store,settings.account);lease.acquire(now_utc())
                try:result=run_cycle(engine,data,now,lease=lease)
                finally:lease.release()
        if args.output:write_json(args.output,result)
        print(dumps(result))
        return 3 if args.command=='check' and args.require_ready and not result['all_requested_inputs_qualified'] else 0
    except (TradingError,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print(dumps({'status':'ERROR','error':str(exc)}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
