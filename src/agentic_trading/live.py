"""Supervised MoonX futures execution. No strategy loop or implicit live activation."""
from dataclasses import replace
import json
import os
from .config import Settings, RiskLimits
from .models import D, Instrument, Mode, TradePlan, TradingError, dumps, fingerprint, utc
from .permissions import verify_evidence
from .risk import IndependentRiskEngine


def at(raw,path):
    for key in path:raw=raw[key]
    return raw


def rows(raw,path):
    result=at(raw,path)
    if not isinstance(result,list):raise TradingError("REMOTE_SCHEMA_UNQUALIFIED")
    return result


def fields(raw,mapping):
    return {key:at(raw,path) for key,path in mapping.items()}


def approval_id(config,packet):
    return fingerprint({"purpose":"LIVE_MOONX_ORDER","config":config,"packet":packet})


class LiveExecution:
    def __init__(self,config,store,transport):
        self.config,self.store,self.transport=config,store,transport
        self.settings=Settings(**dict(config['settings'],limits=RiskLimits(**config['settings'].get('limits',{}))))
        if self.settings.mode!=Mode.LIVE_EXECUTION:raise TradingError("LIVE_CONFIGURATION_REQUIRED")
        if not self.settings.account.startswith('live-'):raise TradingError("SEPARATE_LIVE_ACCOUNT_REQUIRED")
        self.risk=IndependentRiskEngine(self.settings.limits,timezone=self.settings.timezone)
        self.store.ensure_account(self.settings.account,self.settings.capital)
        with store.transaction() as tx:
            tx.execute("CREATE TABLE IF NOT EXISTS live_attempts (id TEXT PRIMARY KEY, account TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL)")

    async def inspect(self):
        """Read account, positions and pending orders. Field paths must be qualified per account."""
        schema=self.config['schema']
        account=await self.transport.call('get_account_overview',{})
        positions=rows(await self.transport.call('list_futures_positions',{}),schema['positions_path'])
        orders=rows(await self.transport.call('list_futures_orders',{}),schema['orders_path'])
        # Unrelated FX exposure is not silently ignored by this single-position executor.
        forex=rows(await self.transport.call('list_forex_positions',{}),schema['forex_positions_path'])
        fx_orders=rows(await self.transport.call('list_forex_orders',{}),schema['forex_orders_path'])
        if str(at(account,schema['account_id_path']))!=str(self.config['remote_account_id']):
            raise TradingError('REMOTE_ACCOUNT_MISMATCH')
        balance=D(at(account,schema['available_balance_path']))
        if balance<=0:raise TradingError('REMOTE_BALANCE_UNAVAILABLE')
        return {'balance':balance,'positions':positions,'orders':orders,'forex':forex,'fx_orders':fx_orders}

    def record(self,attempt,state,payload,now):
        with self.store.transaction(self.settings.account) as tx:
            tx.execute('UPDATE live_attempts SET state=?,payload=? WHERE id=? AND account=?',
                       (state,dumps(payload),attempt,self.settings.account))
            tx.event(self.settings.account,'LIVE_'+state,{'attempt':attempt},now,notify=True)

    async def submit(self,packet,approval,now):
        if self.config.get('enabled') is not True or os.environ.get('TRADING_LIVE_ENABLED')!='YES':
            raise TradingError('LIVE_NOT_ACTIVATED')
        if not approval or approval!=approval_id(self.config,packet):raise TradingError('EXACT_PLAN_APPROVAL_REQUIRED')
        if self.config.get('schema_qualified') is not True:raise TradingError('REMOTE_SCHEMA_UNQUALIFIED')
        tools=await self.transport.list_tools()
        opening=next((t for t in tools if t['name']=='open_futures_position'),None)
        required={'symbol','side','marginUsdt','leverage','marginMode','mode','stopLossPrice','takeProfitPrice'}
        if not opening or not required.issubset(opening.get('inputSchema',{}).get('properties',{})):
            raise TradingError('NATIVE_PROTECTED_ENTRY_UNAVAILABLE')
        plan=TradePlan.from_dict(packet['plan']);spec=Instrument(**packet['instrument'])
        if plan.symbol!=spec.symbol or plan.symbol not in self.settings.watchlist:raise TradingError('SYMBOL_NOT_ADMITTED')
        if len(plan.take_profits)!=1:raise TradingError('LIVE_REQUIRES_SINGLE_NATIVE_TARGET')
        if spec.point_value!=1:raise TradingError('MOONX_CRYPTO_UNITS_REQUIRED')
        context=packet['context']
        age=(utc(now)-utc(context['asof'])).total_seconds()
        if not 0<=age<=60 or context.get('blackout') is not False or context.get('liquidity_ok') is not True:
            raise TradingError('LIVE_CONTEXT_STALE_OR_BLOCKED')
        valid=verify_evidence(packet.get('evidence'),plan.symbol,plan.strategy,now)
        state=await self.inspect()
        if any(state[k] for k in ('positions','orders','forex','fx_orders')):raise TradingError('REMOTE_ACCOUNT_MUST_BE_FLAT')
        # Read current price immediately before sizing the margin; reject significant adverse drift.
        price=await self.transport.call('get_price',{'symbol':plan.symbol})
        current=D(at(price,self.config['schema']['price_path']))
        if abs(current/plan.entry-1)*10000>D(self.config.get('max_price_drift_bps','10')):
            raise TradingError('PRICE_MOVED_REAPPROVE_PLAN')
        checked=replace(plan,entry=current)
        from .brokers import MoonXBrokerAdapter
        prepared=MoonXBrokerAdapter(self.transport).prepare(checked,spec)
        attempt=approval_id(self.config,packet)
        payload={'plan':plan,'instrument':spec,'approval':attempt,'prepared':prepared,'created_at':now,
                 'remote_account_id':self.config['remote_account_id']}
        # Reserve before network I/O; account transaction serializes concurrent attempts.
        with self.store.transaction(self.settings.account) as tx:
            prior=tx.execute('SELECT id FROM live_attempts WHERE account=? AND state!=?',(self.settings.account,'CLOSED')).fetchone()
            if prior:raise TradingError('LIVE_RECONCILIATION_OR_CLOSE_REQUIRED')
            closed=[json.loads(r['payload']) for r in tx.execute('SELECT payload FROM live_attempts WHERE account=? AND state=?',(self.settings.account,'CLOSED'))]
            history=[{'status':'CLOSED','net_pnl':r['net_pnl'],'closed_at':r['closed_at']} for r in closed]
            account=tx.account(self.settings.account);account['balance']=state['balance']
            verdict=self.risk.evaluate(checked,spec,account,history,tx.events(self.settings.account),now,
                                       strategy_validated=valid,blackout=False,liquidity_ok=True)
            if verdict['status']!='PASS':raise TradingError('LIVE_RISK_BLOCK:'+','.join(verdict['reasons']))
            payload['risk']=verdict
            if tx.execute('SELECT id FROM live_attempts WHERE id=?',(attempt,)).fetchone():raise TradingError('DUPLICATE_LIVE_INTENT')
            tx.execute('INSERT INTO live_attempts(id,account,state,payload) VALUES(?,?,?,?)',(attempt,self.settings.account,'SENDING',dumps(payload)))
            # Reserve daily count/risk even if the broker response is lost.
            tx.event(self.settings.account,'OPEN',{'mode':'LIVE_EXECUTION','attempt':attempt,'fee':'0'},now)
        try:
            # The transport is explicitly write-enabled by the live CLI, never by PAPER tools.
            await self.transport.call(prepared['tool'],prepared['arguments'])
        except Exception:
            self.record(attempt,'RECONCILIATION_REQUIRED',payload,now)
            return {'status':'RECONCILIATION_REQUIRED','attempt':attempt,'retry_allowed':False}
        return await self.reconcile(attempt,now)

    async def reconcile(self,attempt,now):
        with self.store.transaction(self.settings.account) as tx:
            row=tx.execute('SELECT * FROM live_attempts WHERE id=? AND account=?',(attempt,self.settings.account)).fetchone()
        if row is None:raise TradingError('UNKNOWN_LIVE_ATTEMPT')
        if row['state']=='CLOSED':return {'status':'CLOSED','attempt':attempt}
        payload=json.loads(row['payload']);plan=TradePlan.from_dict(payload['plan']);spec=Instrument(**payload['instrument'])
        schema=self.config['schema']
        try:
            state=await self.inspect()
            positions=[fields(p,schema['position_fields']) for p in state['positions']]
            matches=[p for p in positions if p['symbol']==plan.symbol and p['side'].lower()==plan.side.lower()]
            if len(matches)==1:
                position=matches[0]
                if payload.get('position_id') not in (None,position['id']):raise TradingError('POSITION_ID_CHANGED')
                payload['position_id']=position['id']
                protections=[fields(p,schema['protection_fields']) for p in rows(
                    await self.transport.call('list_futures_tp_sl_orders',{'status':'active'}),schema['protections_path'])]
                attached=[p for p in protections if p['position_id']==position['id']]
                protected=any(p['type']==schema['stop_type'] and D(p['price'])==plan.stop_loss for p in attached)
                target=any(p['type']==schema['target_type'] and D(p['price'])==plan.take_profits[0].price for p in attached)
                actual=replace(plan,entry=D(position['entry']),quantity=D(position['quantity']))
                from .risk import economics
                within=actual.quantity<=plan.quantity and economics(actual,spec)['net_stop_risk']<=D(self.settings.limits.max_risk_per_trade)
                if protected and target and within:
                    self.record(attempt,'OPEN_PROTECTED',payload,now)
                    return {'status':'OPEN_PROTECTED','attempt':attempt,'position_id':position['id']}
            elif not positions and payload.get('position_id'):
                history=rows(await self.transport.call('get_futures_trade_history',{}),schema['history_path'])
                records=[fields(p,schema['history_fields']) for p in history]
                closed=[p for p in records if p['position_id']==payload['position_id'] and p['status']==schema['closed_status']]
                if len(closed)==1:
                    item=closed[0];pnl=D(item['net_pnl']);closed_at=utc(item['closed_at'])
                    if not utc(payload['created_at'])<=closed_at<=utc(now):raise TradingError('CLOSE_TIME_INVALID')
                    payload.update(net_pnl=pnl,closed_at=closed_at)
                    with self.store.transaction(self.settings.account) as tx:
                        latest=tx.execute('SELECT state FROM live_attempts WHERE id=?',(attempt,)).fetchone()
                        if latest['state']=='CLOSED':return {'status':'CLOSED','attempt':attempt}
                        tx.execute('UPDATE live_attempts SET state=?,payload=? WHERE id=?',('CLOSED',dumps(payload),attempt))
                        tx.event(self.settings.account,'EXIT',{'attempt':attempt,'pnl':pnl,'mode':'LIVE_EXECUTION'},closed_at,notify=True)
                    return {'status':'CLOSED','attempt':attempt,'net_pnl':pnl}
        except Exception:
            pass  # Never expose private provider responses or interpret uncertainty as success.
        self.record(attempt,'RECONCILIATION_REQUIRED',payload,now)
        return {'status':'RECONCILIATION_REQUIRED','attempt':attempt,'retry_allowed':False}

    async def close(self,attempt,approval,now):
        if self.config.get('enabled') is not True or os.environ.get('TRADING_LIVE_ENABLED')!='YES':raise TradingError('LIVE_NOT_ACTIVATED')
        if approval!=fingerprint({'purpose':'CLOSE_LIVE_POSITION','attempt':attempt}):raise TradingError('EXACT_CLOSE_APPROVAL_REQUIRED')
        await self.reconcile(attempt,now)
        with self.store.transaction(self.settings.account) as tx:
            row=tx.execute('SELECT * FROM live_attempts WHERE id=? AND account=?',(attempt,self.settings.account)).fetchone()
            payload=json.loads(row['payload'])
            if row['state'] not in ('OPEN_PROTECTED','RECONCILIATION_REQUIRED') or not payload.get('position_id'):
                raise TradingError('NO_IDENTIFIED_OPEN_POSITION')
            if payload.get('close_sent'):raise TradingError('CLOSE_ALREADY_SENT_RECONCILE')
            payload['close_sent']=True
            tx.execute('UPDATE live_attempts SET state=?,payload=? WHERE id=?',('CLOSING',dumps(payload),attempt))
        try:await self.transport.call('close_futures_position',{'positionId':payload['position_id'],'percentage':100})
        except Exception:
            self.record(attempt,'RECONCILIATION_REQUIRED',payload,now)
            return {'status':'RECONCILIATION_REQUIRED','attempt':attempt,'retry_allowed':False}
        return await self.reconcile(attempt,now)
