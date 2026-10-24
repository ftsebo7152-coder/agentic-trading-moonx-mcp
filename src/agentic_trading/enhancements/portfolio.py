"""Aligned historical portfolio diagnostics; no order sizing or limit changes."""
from math import sqrt,isfinite
from statistics import mean
from ..models import D,TradingError,utc
from ..quantitative import quantile


def portfolio_diagnostics(exposures,returns,now,confidence=.95):
    if not exposures or not .5<confidence<1:raise TradingError('INVALID_PORTFOLIO_DIAGNOSTIC')
    notionals={symbol:float(D(value)) for symbol,value in exposures.items()}
    if not all(isfinite(value) for value in notionals.values()):raise TradingError('FINITE_PORTFOLIO_EXPOSURES_REQUIRED')
    panel={symbol:{} for symbol in notionals};rejected=[]
    for row in returns:
        symbol=row.get('symbol')
        if symbol not in panel:continue
        try:
            timestamp=utc(row['time']);available=utc(row['available_at'])
            if not row.get('source') or not timestamp<=available<=utc(now):raise TradingError('RETURN_PROVENANCE_OR_AVAILABILITY')
            if timestamp in panel[symbol]:raise TradingError('DUPLICATE_RETURN_TIMESTAMP')
            value=float(D(row['return']))
            if not isfinite(value) or value < -1:raise TradingError('INVALID_SIMPLE_RETURN')
            panel[symbol][timestamp]=value
        except (TradingError,KeyError,TypeError,AttributeError) as exc:
            rejected.append({'symbol':symbol,'reason':str(exc)})
    common=set.intersection(*(set(values) for values in panel.values()))
    timestamps=sorted(common)
    if len(timestamps)<3:
        return {'status':'INSUFFICIENT_DATA','aligned_observations':len(timestamps),'rejected':rejected,'execution_authority':False}
    aligned={symbol:[values[t] for t in timestamps] for symbol,values in panel.items()}
    correlations={}
    for first,a in aligned.items():
        correlations[first]={}
        for second,b in aligned.items():
            ma,mb=mean(a),mean(b);va=sum((x-ma)**2 for x in a);vb=sum((y-mb)**2 for y in b)
            correlations[first][second]=sum((x-ma)*(y-mb) for x,y in zip(a,b))/sqrt(va*vb) if va and vb else None
    losses=[-sum(notionals[symbol]*aligned[symbol][i] for symbol in notionals) for i in range(len(timestamps))]
    threshold=quantile(losses,confidence);tail=[v for v in losses if v>=threshold]
    return {'status':'OBSERVED','aligned_observations':len(timestamps),'start':timestamps[0],'end':timestamps[-1],
            'confidence':confidence,'historical_var_usd':max(0,threshold),'historical_expected_shortfall_usd':max(0,mean(tail)),
            'correlations':correlations,'observations_by_symbol':{s:len(v) for s,v in panel.items()},'rejected':rejected,
            'gross_exposure_usd':sum(abs(v) for v in notionals.values()),'execution_authority':False,
            'limitations':['Constant signed USD exposures; aligned supplied simple returns, one input period, no annualization.',
                           'Historical empirical tails exclude unseen shocks, execution costs and changing positions.',
                           'Missing dates are dropped, never forward-filled. This report does not alter portfolio risk caps.']}
