"""Observed execution costs and order-book research. Never submits an order."""
from datetime import timedelta
from statistics import mean
from ..models import D, TradingError, floor_step, utc
from ..quantitative import quantile


def calibrate_costs(fills,quotes,max_quote_age_seconds=5):
    if max_quote_age_seconds<0:raise TradingError('INVALID_QUOTE_AGE')
    ordered=sorted(quotes,key=lambda q:utc(q['time']));rows=[]
    for fill in fills:
        when=utc(fill['time']);side=fill['side'].lower();price=D(fill['price']);quantity=D(fill['quantity'])
        if side not in ('buy','sell') or min(price,quantity)<=0:raise TradingError('INVALID_FILL')
        candidates=[q for q in ordered if q['symbol']==fill['symbol'] and 0<=(when-utc(q['time'])).total_seconds()<=max_quote_age_seconds]
        if not candidates:
            rows.append({'symbol':fill['symbol'],'time':when,'status':'NO_PRIOR_QUOTE'});continue
        quote=candidates[-1];bid=D(quote['bid']);ask=D(quote['ask'])
        if bid<=0 or ask<bid:raise TradingError('INVALID_QUOTE')
        mid=(ask+bid)/2;sign=D(1 if side=='buy' else -1)
        slippage=sign*(price-mid)/mid*10000
        fee=D(fill['fee_amount'])/(price*quantity)*10000 if fill.get('fee_amount') is not None and fill.get('fee_currency') in ('USD','USDT') else None
        if fee is not None and fee<0:raise TradingError('NEGATIVE_FEE_REQUIRES_SEPARATE_REBATE_MODEL')
        rows.append({'symbol':fill['symbol'],'time':when,'quote_time':utc(quote['time']),'status':'OBSERVED',
                     'notional':price*quantity,'slippage_from_mid_bps':slippage,'full_spread_bps':(ask-bid)/mid*10000,
                     'fee_bps':fee,'total_bps':slippage+fee if fee is not None else None})
    observed=[r for r in rows if r['status']=='OBSERVED'];totals=[float(r['total_bps']) for r in observed if r['total_bps'] is not None]
    return {'status':'OBSERVED' if observed else 'INSUFFICIENT_DATA','fills':len(rows),'quote_coverage':len(observed)/len(rows) if rows else 0,
            'fee_coverage':len(totals)/len(rows) if rows else 0,'rows':rows,
            'total_bps_mean':mean(totals) if totals else None,'total_bps_p95':quantile(totals,.95) if totals else None,
            'applied_to_risk_limits':False,
            'note':'Mid-price slippage already includes the spread; spread is not added a second time. USDT fees assume quote-currency parity; rebates and other currencies need explicit conversion.'}


def book_report(book,side,quantity,*,now=None,max_age_seconds=5,band_bps=100):
    side=side.lower();quantity=D(quantity)
    if side not in ('buy','sell') or quantity<=0 or D(band_bps)<=0:raise TradingError('INVALID_BOOK_REQUEST')
    bids=sorted([(D(p),D(q)) for p,q in book['bids']],reverse=True)
    asks=sorted([(D(p),D(q)) for p,q in book['asks']])
    if not bids or not asks or any(min(p,q)<=0 for p,q in bids+asks) or bids[0][0]>asks[0][0]:raise TradingError('INVALID_ORDER_BOOK')
    if len({p for p,q in bids})!=len(bids) or len({p for p,q in asks})!=len(asks):raise TradingError('DUPLICATE_BOOK_LEVEL')
    if now is not None and not 0<=(utc(now)-utc(book['asof'])).total_seconds()<=max_age_seconds:raise TradingError('STALE_ORDER_BOOK')
    if not book.get('source'):raise TradingError('BOOK_SOURCE_REQUIRED')
    mid=(bids[0][0]+asks[0][0])/2;remaining=quantity;spent=D(0);filled=D(0)
    for price,available in asks if side=='buy' else bids:
        take=min(remaining,available);spent+=take*price;filled+=take;remaining-=take
        if remaining==0:break
    vwap=spent/filled if filled else None;sign=D(1 if side=='buy' else -1)
    depth_buy=sum(p*q for p,q in asks if (p/mid-1)*10000<=D(band_bps))
    depth_sell=sum(p*q for p,q in bids if (1-p/mid)*10000<=D(band_bps))
    return {'status':'FULL_SNAPSHOT_FILL' if remaining==0 else 'PARTIAL_SNAPSHOT_FILL','source':book['source'],'asof':book.get('asof'),
            'mid':mid,'spread_bps':(asks[0][0]-bids[0][0])/mid*10000,'filled_quantity':filled,'unfilled_quantity':remaining,
            'vwap':vwap,'adverse_bps':sign*(vwap/mid-1)*10000 if vwap else None,
            'depth_bid_notional':depth_sell,'depth_ask_notional':depth_buy,'band_bps':band_bps,'execution_enabled':False,
            'limitations':['Snapshot consumption only; no queue priority, latency, hidden liquidity or future book movement.']}


def twap_schedule(quantity,step,slices,start,interval_seconds):
    quantity,step=D(quantity),D(step)
    if slices<1 or interval_seconds<1 or quantity<=0 or floor_step(quantity,step)!=quantity:raise TradingError('INVALID_TWAP')
    base=floor_step(quantity/D(slices),step)
    if base<=0:raise TradingError('TOO_MANY_SLICES_FOR_QUANTITY_STEP')
    schedule=[{'at':utc(start)+timedelta(seconds=i*interval_seconds),'quantity':base} for i in range(slices)]
    schedule[-1]['quantity']+=quantity-base*D(slices)
    return {'execution_enabled':False,'schedule':schedule,'quantity':quantity,'note':'Research schedule only, not a broker order or approval.'}
