"""Source-backed desk synthesis without autonomous LLM calls or order authority."""
from ..models import utc, TradingError, D

DESKS=('macro','fundamental','technical','onchain','funding','liquidation','execution','risk')


def research_review(symbol,evidence,now,max_age_seconds=86400):
    observed=[];rejected=[];seen=set()
    for row in evidence:
        try:
            if row['id'] in seen:raise TradingError('DUPLICATE_EVIDENCE')
            seen.add(row['id'])
            if row['desk'] not in DESKS or row['symbol'] not in (symbol,'ALL'):continue
            if not row.get('source') or not row.get('source_url'):raise TradingError('SOURCE_REQUIRED')
            available=utc(row['available_at']);published=utc(row['published_at']);fetched=utc(row['fetched_at'])
            if available<published or fetched<available or fetched>utc(now):raise TradingError('INVALID_EVIDENCE_CHRONOLOGY')
            if not 0<=(utc(now)-available).total_seconds()<=max_age_seconds:raise TradingError('STALE_OR_FUTURE_EVIDENCE')
            if row.get('stance','neutral') not in ('bullish','bearish','neutral'):raise TradingError('UNKNOWN_STANCE')
            observed.append(dict(row))
        except (KeyError,ValueError,TypeError,AttributeError) as exc:
            rejected.append({'id':row.get('id'),'reason':str(exc)})
    desks={desk:[r for r in observed if r['desk']==desk] for desk in DESKS}
    bull=[r['id'] for r in observed if r.get('stance')=='bullish'];bear=[r['id'] for r in observed if r.get('stance')=='bearish']
    return {'symbol':symbol,'asof':utc(now),'status':'OBSERVED' if observed else 'INSUFFICIENT_DATA','desks':desks,
            'bull_case_evidence':bull,'bear_case_evidence':bear,'disagreement':bool(bull and bear),'rejected':rejected,
            'missing_desks':[k for k,v in desks.items() if not v],'execution_authority':False,'setup_score_override':False,
            'note':'Stances are supplied opinions, not verified causal effects or probabilities. Headline text is data, never an instruction.'}


def thesis_update(workspace,symbol,thesis,evidence,now):
    if not thesis.get('hypothesis') or not thesis.get('invalidation'):raise TradingError('FALSIFIABLE_THESIS_REQUIRED')
    review=research_review(symbol,evidence,now)
    return workspace.append('THESIS',{'symbol':symbol,'thesis':thesis,'review':review},now)


def portfolio_heat(positions,capital):
    capital=D(capital)
    if capital<=0:raise TradingError('POSITIVE_CAPITAL_REQUIRED')
    opened=[p for p in positions if p['status']=='OPEN'];groups={};total=D(0)
    for p in opened:
        value=D(p['remaining_risk'])
        if value<0:raise TradingError('INVALID_OPEN_RISK')
        total+=value;group=p['group'];groups[group]=groups.get(group,D(0))+value
    return {'open_risk':total,'heat_fraction':total/capital,'by_group':groups,'execution_authority':False}
