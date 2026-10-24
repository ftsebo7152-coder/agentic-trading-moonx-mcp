"""Independent temporal validation utilities with explicit information intervals."""
from itertools import combinations
from datetime import timedelta
from math import comb, isfinite
from random import Random
import json
from ..models import TradingError, utc
from ..quantitative import performance, monte_carlo, bootstrap_mean_ci


def audit_samples(samples):
    if not samples:raise TradingError('SAMPLES_REQUIRED')
    ids=set();normalized=[]
    for sample in samples:
        row=dict(sample)
        if not row.get('id') or row['id'] in ids:raise TradingError('UNIQUE_SAMPLE_IDS_REQUIRED')
        ids.add(row['id'])
        for key in ('decision_time','information_start','information_end','feature_available_at','label_available_at'):
            row[key]=utc(row[key])
        if not row['information_start']<=row['decision_time']<=row['information_end']<=row['label_available_at']:
            raise TradingError('INVALID_INFORMATION_INTERVAL')
        if row['feature_available_at']>row['decision_time']:raise TradingError('FEATURE_LOOKAHEAD')
        if not row.get('symbol') or not row.get('source'):raise TradingError('SAMPLE_PROVENANCE_REQUIRED')
        normalized.append(row)
    return sorted(normalized,key=lambda r:(r['decision_time'],r['id']))


def purged_splits(samples,n_splits=5,test_groups=1,embargo_seconds=0):
    data=audit_samples(samples)
    sessions=sorted({r['decision_time'] for r in data})
    if not 2<=n_splits<=len(sessions) or not 1<=test_groups<n_splits or embargo_seconds<0:
        raise TradingError('INVALID_CV_DESIGN')
    if comb(n_splits,test_groups)>1000:raise TradingError('CPCV_BUDGET_EXCEEDED')
    groups=[sessions[i*len(sessions)//n_splits:(i+1)*len(sessions)//n_splits] for i in range(n_splits)]
    results=[]
    for selected in combinations(range(n_splits),test_groups):
        test_times={t for i in selected for t in groups[i]}
        test=[r for r in data if r['decision_time'] in test_times]
        train=[];purged=[];embargoed=[]
        for row in data:
            if row['decision_time'] in test_times:continue
            if any(row['information_start']<=t['information_end'] and t['information_start']<=row['information_end'] for t in test):
                purged.append(row['id'])
            elif embargo_seconds and any(t['information_end']<row['decision_time']<=t['information_end']+timedelta(seconds=embargo_seconds) for t in test):
                embargoed.append(row['id'])
            else:train.append(row['id'])
        results.append({'test_groups':selected,'train':train,'test':[r['id'] for r in test],
                        'purged':purged,'embargoed':embargoed,'valid':bool(train)})
    return {'method':'PURGED_CPCV' if test_groups>1 else 'PURGED_K_FOLD','causal':False,'folds':results,
            'note':'Session groups keep simultaneous assets together. CV is not forward evidence; preprocessing must be fit only on each training fold.'}


def causal_walk_forward(samples,train_sessions,test_sessions,step_sessions=None,embargo_seconds=0,expanding=False):
    data=audit_samples(samples);times=sorted({r['decision_time'] for r in data})
    step_sessions=test_sessions if step_sessions is None else step_sessions
    if min(train_sessions,test_sessions,step_sessions)<1 or embargo_seconds<0:raise TradingError('INVALID_WALK_FORWARD')
    folds=[]
    for start in range(train_sessions,len(times)-test_sessions+1,step_sessions):
        cutoff=times[start]-timedelta(seconds=embargo_seconds)
        train_times=set(times[0 if expanding else start-train_sessions:start])
        test_times=set(times[start:start+test_sessions])
        candidates=[r for r in data if r['decision_time'] in train_times]
        eligible=[r for r in candidates if r['information_end']<cutoff and r['label_available_at']<cutoff]
        folds.append({'train':[r['id'] for r in eligible],'test':[r['id'] for r in data if r['decision_time'] in test_times],
                      'purged':[r['id'] for r in candidates if r not in eligible],'valid':bool(eligible)})
    return {'method':'CAUSAL_WALK_FORWARD','folds':folds,'causal':True,'expanding':expanding,
            'note':'Splits only; no model is fitted or certified by this function.'}


def historical_universe(store,asof,max_age_seconds=86400):
    now=utc(asof)
    with store.transaction() as tx:
        records=tx.execute("SELECT at,payload FROM snapshots WHERE kind='CMC_TOP100'").fetchall()
    eligible=[]
    for record in records:
        payload=json.loads(record['payload']);age=(now-utc(payload['asof'])).total_seconds()
        if utc(record['at'])<=now and 0<=age<=max_age_seconds:eligible.append(payload)
    if not eligible:return {'status':'INSUFFICIENT_DATA','assets':[],'reason':'HISTORICAL_CMC_SNAPSHOT_REQUIRED'}
    result=max(eligible,key=lambda r:utc(r['asof']))
    return {'status':'OBSERVED','asof':result['asof'],'assets':result['assets'],'source':result['source']}


def robustness_report(pnls,notionals,capital=1250,seed=19,runs=1000):
    values=[float(v) for v in pnls];notionals=[float(v) for v in notionals]
    capital=float(capital)
    if not values or len(values)!=len(notionals) or not all(isfinite(x) for x in values+notionals+[capital]) or min(notionals)<0 or capital<=0 or not 1<=runs<=100000:
        raise TradingError('ALIGNED_FINITE_TRADES_REQUIRED')
    rng=Random(seed)
    adverse=[v-rng.uniform(0,0.0025)*n for v,n in zip(values,notionals)]
    base=performance(values,capital)
    return {'scope':'RESEARCH_DIAGNOSTICS_NOT_ADMISSION','seed':seed,'baseline':base,
            'cost_stress':{str(bps):performance([v-n*bps/10000 for v,n in zip(values,notionals)],capital) for bps in (5,10,25,50)},'adverse_noise':performance(adverse,capital),
            'without_best_trade':performance([v for i,v in enumerate(values) if i!=values.index(max(values))],capital),
            'bootstrap_mean_ci95':bootstrap_mean_ci(values,runs=runs,seed=seed),
            'block_bootstrap':monte_carlo(values,initial_capital=capital,runs=runs,seed=seed),
            'live_eligible':False,'limitations':['No claim of out-of-sample performance without dated folds.',
            'No PBO/DSR certification or actual model refitting is performed.']}
