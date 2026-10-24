"""Multi-strategy PAPER orchestration through the existing transactional risk engine."""
from dataclasses import asdict
from decimal import ROUND_CEILING,ROUND_FLOOR
from uuid import uuid4
from ..models import Candle,D,Instrument,Mode,TakeProfit,TradePlan,TradingError,dumps,fingerprint,utc
from ..paper import PaperBroker
from ..risk import IndependentRiskEngine,Costs,size_position
from ..permissions import verify_evidence
from ..fundamentals import context_at
from ..universe import resolve_universe,identity_error
from .strategies import StrategyRouter


def parse_markets(data):return {s:[b if isinstance(b,Candle) else Candle.from_dict(b) for b in rows] for s,rows in data.items()}


def liquidity_check(row,asset_class,now,maximum_age,costs):
    try:
        if not row.get('source') or not 0<=(utc(now)-utc(row['asof'])).total_seconds()<=min(maximum_age,120):return False
        bid,ask=D(row['bid']),D(row['ask'])
        if not 0<bid<=ask:return False
        spread=(ask-bid)/((ask+bid)/2)*10000
        if spread>costs.spread_bps:return False
        if row.get('quote_currency') not in ('USD','USDT'):return False
        if row['quote_currency']=='USDT' and row.get('usd_parity_verified') is not True:return False
        if asset_class=='crypto':return D(row['volume_24h'])>=1_000_000 and D(row['depth_usd'])>=100_000
        return row.get('executable_quote') is True
    except (KeyError,ValueError,TypeError,AttributeError):return False


def build_plan(found,spec,settings,now,costs,score,entry=None):
    entry=D(entry) if entry is not None else found['entry'];up=found['side']=='LONG'
    stop=(found['stop_loss']/spec.tick_size).to_integral_value(rounding=ROUND_FLOOR if up else ROUND_CEILING)*spec.tick_size
    distance=abs(entry-stop)
    quantity=size_position(settings.limits.max_risk_per_trade,entry,stop,spec,costs)
    targets=tuple(TakeProfit(((entry+(1 if up else -1)*distance*multiple)/spec.tick_size).to_integral_value(
                  rounding=ROUND_FLOOR if up else ROUND_CEILING)*spec.tick_size,D(fraction)) for multiple,fraction in [(2,'.25'),(3,'.35'),(4,'.40')])
    return TradePlan(spec.symbol,found['side'],entry,stop,quantity,D(1),targets,found['strategy'],D(score),
                     found['time'],found['signal_id'],found['reason'])


class AutonomousPaperEngine:
    def __init__(self,settings,policy,store,*,costs=Costs()):
        if settings.mode!=Mode.PAPER:raise TradingError('AUTONOMY_IS_PAPER_ONLY')
        self.settings,self.policy,self.store=settings,policy,store;self.costs=costs
        self.paper=PaperBroker(store,settings.account,settings.capital,IndependentRiskEngine(settings.limits,costs,settings.timezone))
        self.router=StrategyRouter(policy)
        if store.postgres:raise TradingError('AUTONOMY_SQLITE_ONLY_UNTIL_POSTGRES_QUALIFICATION')
        with store.transaction() as tx:
            tx.execute('CREATE TABLE IF NOT EXISTS autonomy_monitor_gaps (account TEXT NOT NULL,symbol TEXT NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(account,symbol))')

    def acknowledge_gap(self,symbol,reason,operator_confirm=False):
        if operator_confirm is not True or not reason or len(reason)<10:raise TradingError('EXPLICIT_PAPER_GAP_REVIEW_REQUIRED')
        with self.store.transaction(self.settings.account) as tx:
            row=tx.execute('SELECT * FROM autonomy_monitor_gaps WHERE account=? AND symbol=?',(self.settings.account,symbol)).fetchone()
            if not row:raise TradingError('UNKNOWN_PAPER_GAP')
            tx.execute('DELETE FROM autonomy_monitor_gaps WHERE account=? AND symbol=?',(self.settings.account,symbol))
            from ..models import now_utc
            tx.event(self.settings.account,'PAPER_GAP_OPERATOR_REVIEW',{'symbol':symbol,'reason':reason,'gap':dict(row)},now_utc())

    def protect(self,bundle,now):
        actions=[];issues=[]
        with self.store.transaction(self.settings.account) as tx:opened=tx.positions(self.settings.account)
        for position in opened:
            symbol=position['symbol']
            if position.get('mode')!='PAPER':
                issues.append({'symbol':symbol,'reason':'NON_PAPER_POSITION_IN_PAPER_ACCOUNT'});continue
            try:
                rows=bundle.get('monitor_markets',{}).get(symbol)
                if not rows:raise TradingError('MINUTE_MONITOR_DATA_MISSING')
                bars=parse_markets({symbol:rows})[symbol]
                if any(a.time>=b.time for a,b in zip(bars,bars[1:])):raise TradingError('MONITOR_ORDER_INVALID')
                available=[b for b in bars if utc(position['last_mark'])<b.time<=utc(now)]
                if self.policy.asset_class(symbol)=='crypto' and available:
                    if (available[0].time-utc(position['last_mark'])).total_seconds()>60 or any((b.time-a.time).total_seconds()!=60 for a,b in zip(available,available[1:])):
                        raise TradingError('MONITOR_HISTORY_GAP_REPLAY_REQUIRED')
                for bar in available:actions.extend(self.paper.monitor(symbol,bar))
                if not bars or not 0<=(utc(now)-bars[-1].time).total_seconds()<=120:raise TradingError('MINUTE_MONITOR_STALE')
            except (TradingError,KeyError,ValueError,TypeError) as exc:
                issues.append({'symbol':symbol,'reason':str(exc)})
                if str(exc)=='MONITOR_HISTORY_GAP_REPLAY_REQUIRED':
                    with self.store.transaction() as tx:tx.execute('INSERT INTO autonomy_monitor_gaps(account,symbol,reason,at) VALUES(?,?,?,?) ON CONFLICT(account,symbol) DO NOTHING',
                        (self.settings.account,symbol,str(exc),utc(now).isoformat()))
                # Available base bars can still trigger conservative protective exits.
                try:
                    for bar in parse_markets({symbol:bundle.get('markets',{}).get(symbol,[])})[symbol]:
                        if bar.time<=utc(now):actions.extend(self.paper.monitor(symbol,bar))
                except (TradingError,ValueError,KeyError,TypeError):pass
        with self.store.transaction() as tx:gaps=tx.execute('SELECT symbol,reason,at FROM autonomy_monitor_gaps WHERE account=?',(self.settings.account,)).fetchall()
        issues.extend({'symbol':g['symbol'],'reason':'UNREVIEWED_PAPER_HISTORY_GAP','at':g['at']} for g in gaps)
        return {'actions':actions,'issues':issues,'new_entries_allowed':not issues}

    def scan(self,bundle,now,*,universe=None,entries=True,protection=None):
        now=utc(now);protection=self.protect(bundle,now) if protection is None else protection
        universe=universe or resolve_universe(self.settings,self.store,now)
        universe_fresh=True
        if self.settings.universe=='cmc_top100':
            try:universe_fresh=universe.get('requested')=='cmc_top100' and 0<=(now-utc(universe['asof'])).total_seconds()<=3600
            except (KeyError,ValueError,TypeError,AttributeError):universe_fresh=False
        results=[];policy_hash=fingerprint(asdict(self.policy))
        for symbol in universe['symbols']:
            try:
                if not universe_fresh:raise TradingError('CURRENT_CMC_UNIVERSE_STALE_OR_MISMATCHED')
                blocked=universe.get('excluded',{}).get(symbol) or identity_error(symbol,universe,bundle.get('asset_identities',{}).get(symbol))
                if blocked:raise TradingError(blocked)
                base=parse_markets({symbol:bundle.get('markets',{}).get(symbol,[])})[symbol]
                higher=parse_markets({symbol:bundle.get('higher_markets',{}).get(symbol,[])})[symbol]
                metadata=bundle.get('market_metadata',{}).get(symbol,{})
                if metadata.get('base_interval')!=self.policy.base_interval or metadata.get('higher_interval')!=self.policy.higher_interval or not metadata.get('source') or not metadata.get('basis'):
                    raise TradingError('TIMEFRAME_PROVENANCE_REQUIRED')
                if utc(metadata['fetched_at'])>now:raise TradingError('MARKET_DATA_NOT_AVAILABLE_YET')
                routed=self.router.evaluate(symbol,base,higher,now)
                if not routed['candidates']:
                    results.append(routed);continue
                proofs=bundle.get('validation',{}).get(symbol,{}).get('strategies',{})
                valid=lambda c:verify_evidence(proofs.get(c['strategy'],{}),symbol,c['strategy'],now) and proofs[c['strategy']].get('policy_hash')==policy_hash and proofs[c['strategy']].get('basis')==metadata['basis']
                found=next((c for c in routed['candidates'] if valid(c)),routed['candidates'][0])
                spec=Instrument(symbol=symbol,**bundle.get('instruments',{})[symbol])
                liq=bundle.get('liquidity',{}).get(symbol,{})
                liquidity=liquidity_check(liq,self.policy.asset_class(symbol),now,self.settings.limits.max_data_age_seconds,self.costs)
                macro=bundle.get('macro',{})
                context=context_at(macro.get('observations',[]),macro.get('events',[]),now,calendar_asof=macro.get('calendar_asof'),coverage_until=macro.get('coverage_until'),symbol=symbol)
                from ..analysis import SetupScoringEngine
                score=SetupScoringEngine(minimum=self.settings.limits.minimum_setup_score).score({'structure':1,'multi_timeframe':1,
                    'liquidity':int(liquidity),'volume':int(found['volume_confirmed']),'macro':int(not context['blackout'] and context['status']=='OBSERVED'),
                    'regime':1,'costs':int(liquidity),'historical':int(valid(found))})
                reference=None
                if liquidity:
                    mid=(D(liq['bid'])+D(liq['ask']))/2
                    reference=(mid/spec.tick_size).to_integral_value(rounding=ROUND_CEILING if found['side']=='LONG' else ROUND_FLOOR)*spec.tick_size
                plan=build_plan(found,spec,self.settings,now,self.costs,score['score'],entry=reference)
                if not entries or not protection['new_entries_allowed']:
                    verdict={'status':'NO_TRADE','reasons':['MONITOR_ONLY' if not entries else 'POSITION_MONITOR_UNHEALTHY']}
                else:
                    verdict=self.paper.open(plan,spec,now,strategy_validated=valid(found),
                        blackout=context['blackout'] or context['status']!='OBSERVED',liquidity_ok=liquidity)
                results.append({'symbol':symbol,**verdict,'plan':plan,'score':score,'confirmation':found['confirmation'],
                    'strategy_diagnostics':routed['diagnostics'],'basis':metadata['basis'],
                    'fill_model':'OBSERVED_QUOTE_MID_PLUS_ADVERSE_COSTS' if liquidity else 'UNQUALIFIED_CLOSED_BAR_REFERENCE'})
            except (TradingError,KeyError,ValueError,TypeError,AttributeError) as exc:results.append({'symbol':symbol,'status':'NO_TRADE','reason':str(exc)})
        report={'run_id':str(uuid4()),'mode':'PAPER','engine':'MULTI_STRATEGY_V1','at':now,'policy_hash':policy_hash,
                'protection':protection,'universe':universe,'results':results,'real_orders_enabled':False,
                'collection_failures':bundle.get('collection',{}).get('failures',{})}
        with self.store.transaction(self.settings.account) as tx:
            tx.execute('INSERT INTO runs(id,account,at,payload) VALUES(?,?,?,?)',(report['run_id'],self.settings.account,now.isoformat(),dumps(report)))
            tx.event(self.settings.account,'AUTONOMOUS_PAPER_SCAN',report,now)
        return report
