"""Local simulator. It has no reference to a network or broker transport."""
from dataclasses import replace
from decimal import ROUND_CEILING, ROUND_FLOOR
from .models import D, TradePlan, Instrument, TradingError, dumps, floor_step, fingerprint, now_utc
from .risk import Costs, IndependentRiskEngine, economics


class PaperBroker:
    def __init__(self, store, account, capital="1250", risk=None):
        self.store, self.account = store, account
        self.risk = risk or IndependentRiskEngine()
        self.costs = self.risk.costs
        store.ensure_account(account, capital)

    @staticmethod
    def fill_price(price, sign, entering, spec, costs):
        direction = sign if entering else -sign
        raw = D(price)*(1+direction*costs.adverse_bps/10000)
        rounding = ROUND_CEILING if direction>0 else ROUND_FLOOR
        return (raw/spec.tick_size).to_integral_value(rounding=rounding)*spec.tick_size

    def open(self, plan: TradePlan, spec: Instrument, now, **context):
        with self.store.transaction(self.account) as tx:
            existing = tx.execute("SELECT id FROM positions WHERE account=? AND signal=?", (self.account,plan.signal_id)).fetchone()
            if existing:
                return {"status":"DUPLICATE", "position_id":existing["id"]}
            fill = self.fill_price(plan.entry,plan.sign,True,spec,self.costs)
            try:
                filled_plan = replace(plan,entry=fill)
            except TradingError:
                return {"status":"BLOCK","reasons":["ADVERSE_FILL_INVALIDATES_PLAN"]}
            verdict = self.risk.evaluate(filled_plan,spec,tx.account(self.account),tx.positions(self.account,False),tx.events(self.account),now,**context)
            # Requested and executed prices are both retained; evaluate adverse fill before commitment.
            if verdict["status"]!="PASS":
                tx.event(self.account,"REJECT",{"mode":"PAPER","plan":plan,"risk":verdict},now)
                return verdict
            eco=verdict["economics"]
            fee=fill*plan.quantity*spec.point_value*self.costs.fee_bps/10000
            position_id=fingerprint([self.account,plan.id])
            position={"id":position_id,"account":self.account,"signal":plan.signal_id,"symbol":plan.symbol,
                      "mode":"PAPER","platform":"LOCAL_SIMULATOR","status":"OPEN","plan":filled_plan,
                      "requested_entry":plan.entry,"entry":fill,"quantity":plan.quantity,"remaining_quantity":plan.quantity,
                      "remaining_risk":eco["net_stop_risk"],"remaining_notional":eco["notional"],"remaining_margin":eco["margin"],
                      "spec":spec,"group":spec.correlation_group,"stop_loss":plan.stop_loss,"target_index":0,
                      "net_pnl":-fee,"fees":fee,"opened_at":now.isoformat(),"last_mark":now.isoformat(),"mark_price":fill,"exits":[]}
            tx.execute("INSERT INTO positions(id,account,signal,status,payload) VALUES(?,?,?,?,?)",(position_id,self.account,plan.signal_id,"OPEN",dumps(position)))
            balance=D(tx.account(self.account)["balance"])-fee
            tx.execute("UPDATE accounts SET balance=? WHERE id=?",(str(balance),self.account))
            event=tx.event(self.account,"OPEN",{"mode":"PAPER","platform":"LOCAL_SIMULATOR","position":position,
                          "economics":eco,"risk":verdict,"fee":fee,"status":"SIMULATED_FILLED"},now,notify=True)
            return {"status":"SIMULATED_FILLED","position_id":position_id,"event_id":event["event_id"],"risk":verdict}

    def _exit(self,tx,p,quantity,reference,reason,now):
        spec=Instrument(**p["spec"])
        plan=TradePlan.from_dict(p["plan"])
        quantity=D(quantity)
        if not 0<quantity<=D(p["remaining_quantity"]):
            raise TradingError("invalid reducing quantity")
        price=self.fill_price(reference,plan.sign,False,spec,self.costs)
        fee=price*quantity*spec.point_value*self.costs.fee_bps/10000
        pnl=plan.sign*(price-D(p["entry"]))*quantity*spec.point_value-fee
        remaining=D(p["remaining_quantity"])-quantity
        ratio=remaining/D(p["remaining_quantity"])
        p.update(remaining_quantity=remaining,net_pnl=D(p["net_pnl"])+pnl,fees=D(p["fees"])+fee)
        for key in ("remaining_risk","remaining_margin","remaining_notional"):
            p[key]=D(p[key])*ratio
        if remaining==0:
            p.update(status="CLOSED",closed_at=now.isoformat())
        record={"reason":reason,"price":price,"quantity":quantity,"pnl":pnl,"fee":fee,"time":now.isoformat()}
        p["exits"].append(record)
        balance=D(tx.account(self.account)["balance"])+pnl
        tx.execute("UPDATE accounts SET balance=? WHERE id=?",(str(balance),self.account))
        tx.save_position(p)
        tx.event(self.account,"EXIT",{"mode":"PAPER","platform":"LOCAL_SIMULATOR","position_id":p["id"],
                 "symbol":p["symbol"],"side":plan.side,"entry":p["entry"],"stop_loss":p["stop_loss"],
                 "take_profits":plan.take_profits,"leverage":plan.leverage,"score":plan.score,"strategy":plan.strategy,
                 "decision_reason":plan.reason,"remaining_notional":p["remaining_notional"],"remaining_margin":p["remaining_margin"],
                 **record,"position_status":p["status"],"net_position_pnl":p["net_pnl"]},now,notify=True)
        return record

    def monitor(self,symbol,bar):
        from .models import utc
        actions=[]
        with self.store.transaction(self.account) as tx:
            for p in tx.positions(self.account):
                if p["symbol"]!=symbol or bar.time<=utc(p["last_mark"]):
                    continue
                plan=TradePlan.from_dict(p["plan"])
                spec=Instrument(**p["spec"])
                hours=D((bar.time-utc(p["last_mark"])).total_seconds())/3600
                financing=D(p["remaining_notional"])*(self.costs.funding_bps_per_8h*hours/8+self.costs.swap_bps_per_day*hours/24)/10000
                if financing:
                    p["net_pnl"]=D(p["net_pnl"])-financing
                    balance=D(tx.account(self.account)["balance"])-financing
                    tx.execute("UPDATE accounts SET balance=? WHERE id=?",(str(balance),self.account))
                    tx.event(self.account,"FINANCING",{"mode":"PAPER","position_id":p["id"],"pnl":-financing},bar.time)
                p["last_mark"]=bar.time.isoformat()
                p["mark_price"]=bar.close
                stop=D(p["stop_loss"])
                stop_hit=bar.low<=stop if plan.side=="LONG" else bar.high>=stop
                # OHLC cannot determine intrabar order: always stop first when ambiguous.
                if stop_hit:
                    reference=min(stop,bar.open) if plan.side=="LONG" else max(stop,bar.open)
                    actions.append(self._exit(tx,p,D(p["remaining_quantity"]),reference,"STOP",bar.time))
                    continue
                while p["target_index"]<len(plan.take_profits) and p["status"]=="OPEN":
                    idx=p["target_index"]
                    target=plan.take_profits[idx]
                    hit=bar.high>=target.price if plan.side=="LONG" else bar.low<=target.price
                    if not hit: break
                    prior=sum(t.fraction for t in plan.take_profits[:idx])
                    through=prior+target.fraction
                    quantity=(D(p["remaining_quantity"]) if idx==len(plan.take_profits)-1 else
                              floor_step(D(p["quantity"])*through,spec.quantity_step)-floor_step(D(p["quantity"])*prior,spec.quantity_step))
                    p["target_index"]+=1
                    if quantity>0:
                        actions.append(self._exit(tx,p,quantity,target.price,f"TP{idx+1}",bar.time))
                tx.save_position(p)
        return actions

    def close(self,position_id,reference,now,reason="OPERATOR_CLOSE"):
        with self.store.transaction(self.account) as tx:
            positions=[p for p in tx.positions(self.account) if p["id"]==position_id]
            if not positions:
                raise TradingError("unknown or closed position")
            return self._exit(tx,positions[0],D(positions[0]["remaining_quantity"]),reference,reason,now)

    def tighten_stop(self,position_id,new_stop):
        with self.store.transaction(self.account) as tx:
            matches=[p for p in tx.positions(self.account) if p["id"]==position_id]
            if not matches: raise TradingError("unknown position")
            p=matches[0];plan=TradePlan.from_dict(p["plan"]);spec=Instrument(**p["spec"])
            new_stop=D(new_stop)
            if new_stop<=0 or new_stop%spec.tick_size or plan.sign*(new_stop-D(p["stop_loss"]))<0:
                raise TradingError("stop cannot widen risk or violate tick size")
            if plan.sign*(D(p["mark_price"])-new_stop)<=0:
                raise TradingError("stop crosses the last observed market price")
            old_stop=p["stop_loss"]
            p["stop_loss"]=new_stop
            tx.save_position(p)
            tx.event(self.account,"STOP_MODIFIED",{"mode":"PAPER","position_id":p["id"],"previous_stop":old_stop,"stop_loss":new_stop},now_utc())
