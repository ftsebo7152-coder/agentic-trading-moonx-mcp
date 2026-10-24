"""Build bundles consumable by the existing scanner, preserving contract uncertainty."""
from dataclasses import asdict
from ..models import Instrument,TradingError,utc,fingerprint
from ..universe import resolve_universe,PINNED_SLUGS
from .feeds import FeedClient,crypto_bars,crypto_book,derivative_context,rss_news,macro_calendar
from .structure import structure_events


def evidence(symbol,desk,source,url,published,fetched,value):
    return {'id':fingerprint({'symbol':symbol,'desk':desk,'source':source,'fetched':fetched,'value':value}),
            'symbol':symbol,'desk':desk,'source':source,'source_url':url,'published_at':published,
            'available_at':fetched,'fetched_at':fetched,'stance':'neutral','observation':value,'trusted_as_instruction':False}


def collect_bundle(settings,store,now,*,symbols=None,top100=False,derivatives=False,news=False,calendar=False,client=None,universe=None):
    client=client or FeedClient(store);universe=universe or resolve_universe(settings,store,now)
    selected=list(dict.fromkeys(symbols or universe['symbols']))
    if top100 and universe['status']!='CMC_TOP100_PLUS_PINNED':raise TradingError('CURRENT_TOP100_REQUIRED_FOR_FULL_COLLECTION')
    if top100:selected=list(dict.fromkeys([r['symbol'] for r in universe['assets']]+selected))
    bundle={'markets':{},'instruments':{},'asset_identities':{},'macro':{'observations':[],'events':[]},'liquidity':{},'validation':{},
            'collection':{'asof':utc(now),'universe_status':universe['status'],'assets':{},'failures':{},'execution_enabled':False},
            'research_evidence':[],'derivatives':{}}
    for symbol in selected:
        if symbol in ('HOOD','XAUUSD','XAGUSD','NAS100') or symbol in universe['excluded']:
            bundle['collection']['failures'][symbol]='NON_CRYPTO_OR_EXCLUDED';continue
        identity=universe['identities'].get(symbol)
        if not identity and symbol in PINNED_SLUGS:identity={'cmc_slug':PINNED_SLUGS[symbol]}
        if not identity:
            bundle['collection']['failures'][symbol]='IDENTITY_UNVERIFIED';continue
        try:
            collected=dict(crypto_bars(client,symbol,now));bars=collected.pop('bars')
            bundle['markets'][symbol]=[asdict(b) for b in bars]
            spec=asdict(Instrument(symbol));spec.pop('symbol')
            # Research spot data never qualifies a real MoonX futures contract.
            bundle['instruments'][symbol]=spec;bundle['asset_identities'][symbol]=identity
            bundle['collection']['assets'][symbol]={**collected,'broker_mapping_verified':False,'completed_bars':len(bars)}
            url='https://www.okx.com/api/v5/market/candles' if collected['source']=='OKX_SPOT' else 'https://api.bybit.com/v5/market/kline'
            bundle['research_evidence'].append(evidence(symbol,'technical',collected['source'],url,bars[-1].time,collected['fetched_at'],
                     {'instrument':collected['instrument'],'basis':collected['basis'],'structure':structure_events(bars)}))
            try:
                book,quality=crypto_book(client,symbol,collected['source'],now)
                liq={'source':collected['source'],'asof':book['asof'],'depth_usd':min(quality['depth_bid_notional'],quality['depth_ask_notional']),
                     'spread_bps':quality['spread_bps'],'quote_currency':'USDT','usd_parity_verified':False}
                recent=bars[-24:]
                if len(recent)==24 and all((b.time-a.time).total_seconds()==3600 for a,b in zip(recent,recent[1:])):
                    liq['volume_24h']=sum(b.volume*b.close for b in recent)
                    liq['volume_method']='CLOSED_HOURLY_CLOSE_TIMES_VOLUME_PROXY'
                bundle['liquidity'][symbol]=liq
            except (TradingError,KeyError,ValueError,TypeError,IndexError):bundle['collection']['failures'][symbol+':book']='BOOK_UNAVAILABLE'
            if derivatives:
                context=derivative_context(client,symbol,now);bundle['derivatives'][symbol]=context
                for key,value in context['values'].items():
                    fetched=context['fetched_at_by_field'][key]
                    bundle['research_evidence'].append(evidence(symbol,'funding',context['source'],
                         'https://www.okx.com/api/v5/public/'+('funding-rate' if key=='funding_rate' else 'open-interest'),
                         fetched,fetched,{'instrument':context['instrument'],'field':key,'value':value}))
        except (TradingError,KeyError,ValueError,TypeError,IndexError):bundle['collection']['failures'][symbol]='MARKET_DATA_UNAVAILABLE'
    if news:
        bundle['news']=rss_news(client,now)
        for item in bundle['news']['items']:
            bundle['research_evidence'].append({**item,'symbol':'ALL','desk':'macro' if item['source']=='federal_reserve' else 'fundamental','stance':'neutral'})
    if calendar:
        try:bundle['macro'].update(macro_calendar(client,now))
        except (TradingError,KeyError,ValueError,TypeError):bundle['collection']['failures']['calendar']='CALENDAR_UNAVAILABLE'
    bundle['collection']['note']='Read-only research bundle. Missing calendar, evidence or verified contract specs continues to block entries in the existing engine.'
    return bundle
