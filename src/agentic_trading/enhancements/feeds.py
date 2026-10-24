"""Bounded public feed collection, cache and provenance. No credentials or orders."""
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,build_opener
from urllib.error import HTTPError
import json
import xml.etree.ElementTree as ET
from ..market_data import NoRedirect
from ..models import Candle,D,TradingError,utc,validate_candles,fingerprint,dumps,now_utc
from .execution_quality import book_report

RSS={'federal_reserve':'https://www.federalreserve.gov/feeds/press_all.xml',
     'coindesk':'https://www.coindesk.com/arc/outboundfeeds/rss/',
     'cointelegraph':'https://cointelegraph.com/rss'}


class FeedClient:
    HOSTS={'www.okx.com','api.bybit.com','www.federalreserve.gov','www.coindesk.com','cointelegraph.com','api.fxmacrodata.com'}
    def __init__(self,store,budget=200,clock=now_utc):
        if not 1<=budget<=1000:raise TradingError('INVALID_FEED_BUDGET')
        self.store=store;self.budget=budget;self.requests=0;self.clock=clock;self.completed_at=None
        with store.transaction() as tx:
            tx.execute('CREATE TABLE IF NOT EXISTS research_feed_cache (id TEXT PRIMARY KEY, payload TEXT, fetched_at TEXT, retry_after TEXT)')

    def _fetch(self,url):
        with build_opener(NoRedirect).open(Request(url,headers={'Accept':'application/json, application/rss+xml','User-Agent':'AgenticTradingResearch/0.1'}),timeout=15) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise TradingError('FEED_RESPONSE_TOO_LARGE')
        return raw.decode('utf8')

    def get(self,url,now,ttl=60,xml=False):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in self.HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):raise TradingError('UNAPPROVED_RESEARCH_ORIGIN')
        key=fingerprint(url);now=utc(now)
        with self.store.transaction() as tx:
            row=tx.execute('SELECT * FROM research_feed_cache WHERE id=?',(key,)).fetchone()
        if row:
            if row['retry_after'] and now<utc(row['retry_after']):raise TradingError('FEED_RATE_LIMIT_COOLDOWN')
            if row['payload'] is not None and row['fetched_at'] and 0<=(now-utc(row['fetched_at'])).total_seconds()<=ttl:
                self.completed_at=utc(row['fetched_at'])
                return json.loads(row['payload'])
        if self.requests>=self.budget:raise TradingError('FEED_REQUEST_BUDGET_EXCEEDED')
        self.requests+=1
        try:
            raw=self._fetch(url);value=raw if xml else json.loads(raw)
            if not xml and not isinstance(value,dict):raise TradingError('FEED_OBJECT_REQUIRED')
        except HTTPError as exc:
            if exc.code==429:
                with self.store.transaction() as tx:
                    tx.execute('INSERT INTO research_feed_cache(id,retry_after) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET retry_after=excluded.retry_after',
                               (key,(now+timedelta(minutes=5)).isoformat()))
                raise TradingError('FEED_RATE_LIMITED') from None
            raise TradingError('FEED_HTTP_FAILED') from None
        except Exception:raise TradingError('FEED_READ_FAILED') from None
        self.completed_at=utc(self.clock())
        with self.store.transaction() as tx:
            tx.execute('INSERT INTO research_feed_cache(id,payload,fetched_at,retry_after) VALUES(?,?,?,NULL) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,fetched_at=excluded.fetched_at,retry_after=NULL',
                       (key,dumps(value),self.completed_at.isoformat()))
        return value


def timestamp(value,scale=1):
    try:return datetime.fromtimestamp(int(value)/scale,timezone.utc)
    except (ValueError,TypeError,OverflowError,OSError):raise TradingError('INVALID_PROVIDER_TIMESTAMP') from None


def milliseconds(value):return timestamp(value,1000)


def crypto_bars(client,symbol,now):
    if not symbol.isascii() or not symbol.isalnum():raise TradingError('INVALID_PROVIDER_SYMBOL')
    errors=[]
    for provider in ('OKX_SPOT','BYBIT_SPOT'):
        try:
            if provider=='OKX_SPOT':
                raw=client.get('https://www.okx.com/api/v5/market/candles?'+urlencode({'instId':symbol+'-USDT','bar':'1H','limit':100}),now)
                if str(raw.get('code'))!='0':raise TradingError('OKX_DATA_UNAVAILABLE')
                data=[r for r in raw['data'] if str(r[8])=='1']
            else:
                raw=client.get('https://api.bybit.com/v5/market/kline?'+urlencode({'category':'spot','symbol':symbol+'USDT','interval':60,'limit':100}),now)
                if str(raw.get('retCode'))!='0':raise TradingError('BYBIT_DATA_UNAVAILABLE')
                data=raw['result']['list']
            bars=[Candle(milliseconds(r[0])+timedelta(hours=1),*(D(r[k]) for k in (1,2,3,4,5))) for r in data if milliseconds(r[0])+timedelta(hours=1)<=utc(now)]
            bars.sort(key=lambda b:b.time);validate_candles(bars)
            return {'source':provider,'instrument':symbol+('/USDT' if provider=='BYBIT_SPOT' else '-USDT'),
                    'basis':'SPOT_USDT_NOT_MOONX_FUTURES','asof':utc(now),'fetched_at':getattr(client,'completed_at',None) or utc(now),
                    'bars':bars,'fallback_errors':errors}
        except (TradingError,KeyError,ValueError,TypeError,IndexError):errors.append(provider+'_UNAVAILABLE')
    raise TradingError('NO_VALID_CRYPTO_CANDLES')


def crypto_book(client,symbol,provider,now):
    if provider=='OKX_SPOT':
        raw=client.get('https://www.okx.com/api/v5/market/books?'+urlencode({'instId':symbol+'-USDT','sz':50}),now,ttl=2)
        if str(raw.get('code'))!='0':raise TradingError('BOOK_UNAVAILABLE')
        data=raw['data'][0];bids=data['bids'];asks=data['asks'];stamp=data['ts']
    elif provider=='BYBIT_SPOT':
        raw=client.get('https://api.bybit.com/v5/market/orderbook?'+urlencode({'category':'spot','symbol':symbol+'USDT','limit':50}),now,ttl=2)
        if str(raw.get('retCode'))!='0':raise TradingError('BOOK_UNAVAILABLE')
        data=raw['result'];bids=data['b'];asks=data['a'];stamp=data['ts']
    else:raise TradingError('UNKNOWN_BOOK_PROVIDER')
    book={'source':provider,'asof':milliseconds(stamp),'bids':[(r[0],r[1]) for r in bids],'asks':[(r[0],r[1]) for r in asks]}
    diagnostic=book_report(book,'buy','0.001',now=getattr(client,'completed_at',None) or now,max_age_seconds=60)
    return book,diagnostic


def derivative_context(client,symbol,now):
    if not symbol.isascii() or not symbol.isalnum():raise TradingError('INVALID_PROVIDER_SYMBOL')
    instrument=symbol+'-USDT-SWAP';values={};errors=[];timestamps={}
    for key,path,args,field in [
        ('funding_rate','funding-rate',{'instId':instrument},'fundingRate'),
        ('open_interest_usd','open-interest',{'instType':'SWAP','instId':instrument},'oiUsd')]:
        try:
            raw=client.get('https://www.okx.com/api/v5/public/'+path+'?'+urlencode(args),now)
            if str(raw.get('code'))!='0' or len(raw.get('data',[]))!=1:raise TradingError('DERIVATIVE_DATA_UNAVAILABLE')
            values[key]=D(raw['data'][0][field])
            timestamps[key]=getattr(client,'completed_at',None) or utc(now)
        except (TradingError,KeyError,ValueError,TypeError,IndexError):errors.append(key)
    return {'source':'OKX_PUBLIC_SWAP','instrument':instrument,'fetched_at_by_field':timestamps,'values':values,'missing':errors,
            'status':'OBSERVED' if values else 'INSUFFICIENT_DATA','execution_authority':False}


def rss_news(client,now,max_age_seconds=86400):
    items=[];errors=[]
    for source,url in RSS.items():
        try:
            root=ET.fromstring(client.get(url,now,ttl=300,xml=True))
            fetched=getattr(client,'completed_at',None) or utc(now)
            for row in root.findall('.//item')[:100]:
                title=row.findtext('title');link=row.findtext('link');date=row.findtext('pubDate')
                if not all((title,link,date)):continue
                try:published=utc(parsedate_to_datetime(date))
                except (ValueError,TypeError):continue
                if not 0<=(utc(now)-published).total_seconds()<=max_age_seconds:continue
                if published>fetched:continue
                items.append({'id':fingerprint({'source':source,'url':link}),'headline':title[:1000],'source':source,'source_url':link,
                              'published_at':published,'available_at':fetched,'fetched_at':fetched,'trusted_as_instruction':False})
        except (TradingError,ValueError,ET.ParseError):errors.append(source)
    unique={r['id']:r for r in items}
    return {'status':'OBSERVED' if unique else 'INSUFFICIENT_DATA','items':list(unique.values()),'failed_sources':errors,
            'note':'RSS is not an exhaustive economic calendar. No headline is a trade instruction.'}


def macro_calendar(client,now):
    """Optional public USD event watch; completeness is deliberately not inferred."""
    payload=client.get('https://api.fxmacrodata.com/v1/calendar/usd?limit=100',now,ttl=300)
    fetched=getattr(client,'completed_at',None) or utc(now)
    quality=payload['data_quality']
    expected={'is_official':True,'is_proxy':False,'is_fallback':False,'is_stale':False,
              'has_announcement_datetime':True,'point_in_time_safe':True}
    if not isinstance(quality,dict) or payload.get('currency')!='USD' or quality.get('source_type')!='official' or any(quality.get(k) is not v for k,v in expected.items()):
        raise TradingError('CALENDAR_QUALITY_UNVERIFIED')
    events=[]
    for row in payload['data']:
        if type(row['announcement_datetime']) is not int or not row.get('release') or type(row.get('market_tier')) is not int or row['market_tier'] not in (1,2,3):
            raise TradingError('CALENDAR_EVENT_INVALID')
        events.append({'name':row['release'],'time':timestamp(row['announcement_datetime']),
                       'impact':'high' if row['market_tier']==1 else 'medium','available_at':fetched,'source':'FXMacroData'})
    return {'events':events,'calendar_asof':fetched,'coverage_until':None,'calendar_coverage_known':False,
            'note':'Observed event watch only. A truncated list does not establish an exhaustive calendar horizon.'}
