"""Multi-timeframe public crypto and read-only MoonX candle collection."""
from dataclasses import asdict
from urllib.parse import urlencode
from ..models import Candle,D,Instrument,TradingError,utc,now_utc
from ..market_data import moonx_candles
from ..universe import resolve_universe,PINNED_SLUGS
from ..enhancements.feeds import FeedClient,milliseconds,crypto_book
from ..enhancements.cli import write_json
from .timeframes import INTERVALS

OKX_BARS={'1m':'1m','5m':'5m','15m':'15m','30m':'30m','1h':'1H','2h':'2H','4h':'4H','1d':'1Dutc'}
BYBIT_BARS={'1m':'1','5m':'5','15m':'15','30m':'30','1h':'60','2h':'120','4h':'240','1d':'D'}


def public_series(client,symbol,interval,now,*,provider=None,limit=300):
    if not symbol.isascii() or not symbol.isalnum() or interval not in INTERVALS or not 1<=limit<=300:raise TradingError('INVALID_SERIES_REQUEST')
    providers=(provider,) if provider else ('OKX_SPOT','BYBIT_SPOT')
    for source in providers:
        try:
            if source=='OKX_SPOT':
                raw=client.get('https://www.okx.com/api/v5/market/candles?'+urlencode({'instId':symbol+'-USDT','bar':OKX_BARS[interval],'limit':limit}),now,ttl=10 if interval=='1m' else 60)
                if str(raw.get('code'))!='0':raise TradingError('PUBLIC_SERIES_UNAVAILABLE')
                rows=[r for r in raw['data'] if str(r[8])=='1']
            elif source=='BYBIT_SPOT':
                raw=client.get('https://api.bybit.com/v5/market/kline?'+urlencode({'category':'spot','symbol':symbol+'USDT','interval':BYBIT_BARS[interval],'limit':limit}),now,ttl=10 if interval=='1m' else 60)
                if str(raw.get('retCode'))!='0':raise TradingError('PUBLIC_SERIES_UNAVAILABLE')
                rows=raw['result']['list']
            else:raise TradingError('UNKNOWN_PUBLIC_PROVIDER')
            from datetime import timedelta
            bars=[Candle(milliseconds(r[0])+timedelta(seconds=INTERVALS[interval]),*(D(r[k]) for k in (1,2,3,4,5))) for r in rows if milliseconds(r[0]).timestamp()+INTERVALS[interval]<=utc(now).timestamp()]
            bars.sort(key=lambda b:b.time)
            if not bars or any(a.time>=b.time for a,b in zip(bars,bars[1:])):raise TradingError('INVALID_PUBLIC_SERIES')
            return {'bars':bars,'source':source,'interval':interval,'fetched_at':getattr(client,'completed_at',None) or utc(now)}
        except (TradingError,KeyError,TypeError,ValueError,IndexError):continue
    raise TradingError('NO_VALID_PUBLIC_SERIES')


def empty_bundle(now,context=None):
    context=context or {}
    return {'markets':{},'higher_markets':{},'monitor_markets':{},'market_metadata':{},
            'instruments':dict(context.get('instruments',{})),'asset_identities':dict(context.get('asset_identities',{})),
            'macro':context.get('macro',{}),'validation':context.get('validation',{}),'liquidity':dict(context.get('liquidity',{})),
            'collection':{'started_at':utc(now),'failures':{},'mode':'READ_ONLY','contracts_qualified_by_collection':False}}


def collect_public(settings,policy,store,now,*,context=None,symbols=None,monitor_symbols=(),client=None,universe=None):
    client=client or FeedClient(store,budget=600)
    universe=universe or resolve_universe(settings,store,now)
    bundle=empty_bundle(now,context);selected=list(dict.fromkeys([*monitor_symbols,*(symbols or universe['symbols'])]))
    for symbol in selected:
        if policy.asset_class(symbol)!='crypto' or (symbol in universe.get('excluded',{}) and symbol not in monitor_symbols):continue
        try:
            base=public_series(client,symbol,policy.base_interval,now)
            bundle['markets'][symbol]=base['bars']
            higher=public_series(client,symbol,policy.higher_interval,now,provider=base['source'])
            bundle['higher_markets'][symbol]=higher['bars']
            if symbol in monitor_symbols:bundle['monitor_markets'][symbol]=public_series(client,symbol,'1m',now,provider=base['source'])['bars']
            bundle['market_metadata'][symbol]={'base_interval':policy.base_interval,'higher_interval':policy.higher_interval,
                'monitor_interval':'1m','source':base['source'],'basis':base['source']+'_USDT','fetched_at':max(base['fetched_at'],higher['fetched_at'])}
            bundle['instruments'].setdefault(symbol,{'specs_verified':False})
            identity=universe.get('identities',{}).get(symbol) or ({'cmc_slug':PINNED_SLUGS[symbol]} if symbol in PINNED_SLUGS else None)
            if identity:bundle['asset_identities'][symbol]=identity
            try:
                book,quality=crypto_book(client,symbol,base['source'],now)
                row={'source':base['source'],'asof':book['asof'],'bid':max(D(r[0]) for r in book['bids']),
                     'ask':min(D(r[0]) for r in book['asks']),'depth_usd':min(quality['depth_bid_notional'],quality['depth_ask_notional']),
                     'quote_currency':'USDT','usd_parity_verified':bool((context or {}).get('liquidity',{}).get(symbol,{}).get('usd_parity_verified') is True)}
                if policy.base_interval=='1h' and len(base['bars'])>=24:
                    tail=base['bars'][-24:]
                    if all((b.time-a.time).total_seconds()==3600 for a,b in zip(tail,tail[1:])):
                        row.update(volume_24h=sum(b.volume*b.close for b in tail),volume_method='HOURLY_NOTIONAL_PROXY')
                bundle['liquidity'][symbol]=row
            except (TradingError,KeyError,TypeError,ValueError):bundle['collection']['failures'][symbol+':book']='BOOK_UNAVAILABLE'
        except (TradingError,KeyError,TypeError,ValueError):bundle['collection']['failures'][symbol]='PUBLIC_TIMEFRAMES_UNAVAILABLE'
    bundle['collection']['universe']=universe;bundle['collection']['requests']=client.requests
    return bundle


async def collect_moonx(settings,policy,now,broker,*,context=None,symbols=None,monitor_symbols=()):
    bundle=empty_bundle(now,context)
    for symbol in dict.fromkeys([*monitor_symbols,*(symbols or settings.watchlist)]):
        if policy.asset_class(symbol)=='equity':
            bundle['collection']['failures'][symbol]='EQUITY_FEED_MAPPING_REQUIRED';continue
        try:
            for interval,target in [(policy.base_interval,'markets'),(policy.higher_interval,'higher_markets')]+([('1m','monitor_markets')] if symbol in monitor_symbols else []):
                raw=await broker.read('get_candles',{'symbol':symbol,'interval':interval,'limit':300})
                expected='crypto' if policy.asset_class(symbol)=='crypto' else 'forex'
                # MoonX labels crypto instruments as futures in some versions.
                allowed=('crypto','futures') if expected=='crypto' else ('forex',)
                if raw.get('symbol')!=symbol or raw.get('interval')!=interval or raw.get('market') not in allowed:
                    raise TradingError('MOONX_MARKET_IDENTITY_OR_TIMEFRAME_MISMATCH')
                bundle[target][symbol]=moonx_candles(raw,INTERVALS[interval],now)
            bundle['market_metadata'][symbol]={'base_interval':policy.base_interval,'higher_interval':policy.higher_interval,
                'monitor_interval':'1m','source':'MOONX_MCP','basis':'MOONX_'+('CRYPTO' if expected=='crypto' else 'CFD'),
                'fetched_at':now_utc(),'volume_note':'Zero/unknown CFD volume is preserved; no synthetic market volume.'}
            bundle['instruments'].setdefault(symbol,{'specs_verified':False})
            if symbol in PINNED_SLUGS:bundle['asset_identities'].setdefault(symbol,{'cmc_slug':PINNED_SLUGS[symbol]})
        except (TradingError,KeyError,TypeError,ValueError):bundle['collection']['failures'][symbol]='MOONX_READ_ONLY_COLLECTION_FAILED'
    return bundle


def merge_bundles(primary,secondary):
    collected=set(secondary['markets'])
    for name in ('markets','higher_markets','monitor_markets','market_metadata','instruments','asset_identities','liquidity'):
        primary[name].update({s:v for s,v in secondary[name].items() if s in collected})
    primary['collection']['failures'].update(secondary['collection']['failures'])
    return primary
