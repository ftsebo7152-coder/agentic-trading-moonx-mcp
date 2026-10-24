"""Chronological multi-asset research replay and bounded causal strategy selection."""
from dataclasses import asdict,replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from ..models import D,Instrument,TradingError,utc,fingerprint
from ..paper import PaperBroker
from ..risk import Costs,IndependentRiskEngine
from ..quantitative import performance
from ..storage import Store
from .engine import parse_markets,build_plan
from .strategies import StrategyRouter
from .timeframes import INTERVALS


def replay(bundle,settings,policy,*,costs=Costs(),start=None,end=None,scratch=None):
    markets=parse_markets(bundle['markets']);higher=parse_markets(bundle.get('higher_markets',{}))
    if not markets:raise TradingError('REPLAY_MARKETS_REQUIRED')
    for rows in [*markets.values(),*higher.values()]:
        if not rows or any(a.time>=b.time for a,b in zip(rows,rows[1:])):raise TradingError('INVALID_REPLAY_SERIES')
    times=sorted({b.time for rows in markets.values() for b in rows})
    first,last=utc(start) if start else times[0],utc(end) if end else times[-1]
    if first>last:raise TradingError('INVALID_REPLAY_WINDOW')
    specs={s:Instrument(symbol=s,**bundle['instruments'][s]) for s in markets}
    seconds=INTERVALS[policy.base_interval];router=StrategyRouter(policy);events={}
    for symbol,rows in markets.items():
        for index,bar in enumerate(rows):
            if first<=bar.time<=last:events.setdefault(bar.time,[]).append((symbol,index,bar))
    blocked={};decisions=[]
    with TemporaryDirectory(dir=scratch) as temp:
        store=Store(Path(temp)/'replay.sqlite')
        broker=PaperBroker(store,'multi-asset-research',settings.capital,IndependentRiskEngine(settings.limits,costs,settings.timezone))
        for when,items in sorted(events.items()):
            # All positions are marked through the just-closed interval before any next-open entries.
            for symbol,index,bar in sorted(items):broker.monitor(symbol,bar)
            for symbol,index,bar in sorted(items):
                rows=markets[symbol]
                if index+1>=len(rows) or rows[index+1].time>last or (rows[index+1].time-bar.time).total_seconds()!=seconds:continue
                if settings.universe=='cmc_top100':
                    snapshots=[r for r in bundle.get('historical_universe',[]) if utc(r['available_at'])<=when and 0<=(when-utc(r['asof'])).total_seconds()<=86400]
                    if not snapshots or symbol not in max(snapshots,key=lambda r:utc(r['asof']))['symbols']:
                        blocked['HISTORICAL_UNIVERSE_MISSING_OR_ASSET_ABSENT']=blocked.get('HISTORICAL_UNIVERSE_MISSING_OR_ASSET_ABSENT',0)+1;continue
                routed=router.evaluate(symbol,rows[:index+1],higher.get(symbol,[]),when)
                if not routed['candidates']:continue
                found=routed['candidates'][0]
                # Only next bar's opening price is consumed here. Its high/low/close are not inspected until it closes.
                try:
                    plan=build_plan(found,specs[symbol],settings,when,costs,90,entry=rows[index+1].open)
                    outcome=broker.open(plan,specs[symbol],when,strategy_validated=True,blackout=False,liquidity_ok=True)
                    decisions.append({'time':when,'symbol':symbol,'strategy':found['strategy'],'status':outcome['status'],
                                      'signal_id':found['signal_id'],'entry_model':'NEXT_BAR_OPEN_PLUS_ADVERSE_COSTS'})
                except TradingError as exc:blocked[str(exc)]=blocked.get(str(exc),0)+1
        with store.transaction('multi-asset-research') as tx:opened=tx.positions('multi-asset-research')
        for position in opened:
            eligible=[b for b in markets[position['symbol']] if b.time<=last]
            if eligible:broker.close(position['id'],eligible[-1].close,eligible[-1].time,'END_OF_RESEARCH_WINDOW')
        state=store.report('multi-asset-research');trades=state['positions']
    return {'scope':'RESEARCH_REPLAY_NOT_PAPER_VALIDATION','window':{'start':first,'end':last},'policy_hash':fingerprint(asdict(policy)),
            'dataset_hash':fingerprint(bundle),'metrics':performance([D(p['net_pnl']) for p in trades],settings.capital),
            'by_strategy':{s:performance([D(p['net_pnl']) for p in trades if p['plan']['strategy']==s],settings.capital) for s in policy.strategies},
            'trades':trades,'decisions':decisions,'blocked':blocked,'costs':costs,'live_eligible':False,
            'assumptions':['Next-open simulation with adverse costs; no queue/tick execution model.',
                'One shared PAPER risk account across symbols and strategies; stop-first intrabar ambiguity.',
                'Historical macro and executable liquidity are not reconstructed: research assumes those filters pass.',
                'No attestation is signed. Contracts must be independently supplied and verified; CMC replay needs dated compositions.']}


def walk_forward(bundle,settings,policies,*,train_sessions,test_sessions,minimum_train_trades=5,embargo_sessions=1,scratch=None):
    if not policies or len(policies)>10 or min(train_sessions,test_sessions,minimum_train_trades)<1 or embargo_sessions<1:raise TradingError('INVALID_BOUNDED_WALK_FORWARD')
    if len({(p.base_interval,p.higher_interval) for p in policies})!=1:raise TradingError('WALK_FORWARD_TIMEFRAMES_MUST_MATCH')
    markets=parse_markets(bundle['markets']);times=sorted({b.time for rows in markets.values() for b in rows});folds=[]
    if max(0,(len(times)-train_sessions-embargo_sessions)//test_sessions)>50:raise TradingError('WALK_FORWARD_FOLD_BUDGET_EXCEEDED')
    for cursor in range(train_sessions+embargo_sessions,len(times)-test_sessions+1,test_sessions):
        train_start=times[cursor-embargo_sessions-train_sessions];train_end=times[cursor-embargo_sessions-1]
        test_start=times[cursor];test_end=times[cursor+test_sessions-1];ranked=[]
        for policy in policies:
            result=replay(bundle,settings,policy,start=train_start,end=train_end,scratch=scratch)
            metrics=result['metrics'];eligible=metrics['trades']>=minimum_train_trades and metrics['net_pnl']>0
            ranked.append({'policy':policy,'hash':result['policy_hash'],'eligible':eligible,'train_metrics':metrics})
        eligible=[r for r in ranked if r['eligible']]
        fold={'train_start':train_start,'train_end':train_end,'test_start':test_start,'test_end':test_end,
              'candidates':[{'policy_hash':r['hash'],'eligible':r['eligible'],'train_metrics':r['train_metrics']} for r in ranked]}
        if not eligible:fold.update(status='INSUFFICIENT_TRAINING_EVIDENCE',selected_policy=None)
        else:
            best=max(eligible,key=lambda r:(r['train_metrics']['net_pnl'],-r['train_metrics']['max_drawdown_fraction']))
            fold.update(status='EVALUATED_OUT_OF_SAMPLE',selected_policy=asdict(best['policy']),
                        result=replay(bundle,settings,best['policy'],start=test_start,end=test_end,scratch=scratch))
        folds.append(fold)
    return {'scope':'CAUSAL_POLICY_SELECTION_RESEARCH_ONLY','folds':folds,'dataset_hash':fingerprint(bundle),
            'embargo_sessions':embargo_sessions,'live_eligible':False,
            'limitations':['Candidates are selected on training results only; each test fold has independent initial capital.',
                           'Not a fitted ML pipeline or a financial qualification. Do not tune candidates after inspecting the holdout.']}
