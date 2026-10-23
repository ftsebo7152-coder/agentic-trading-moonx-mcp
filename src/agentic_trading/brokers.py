"""Broker ports and honest capability-limited adapters. No live submission path."""
from dataclasses import dataclass
from typing import Protocol
from .models import D, Mode, TradingError, fingerprint


class MCPTransport(Protocol):
    async def call(self,name:str,arguments:dict): ...
    async def list_tools(self): ...


class BrokerAdapter(Protocol):
    name:str
    async def positions(self): ...
    def prepare(self,plan,spec): ...


class MoonXBrokerAdapter:
    name="moonx"
    READ_TOOLS={"get_account_overview","get_price","get_candles","get_technical_indicators","list_forex_positions","list_forex_orders","list_futures_positions","list_futures_orders","get_forex_trade_history","get_futures_trade_history","get_futures_summary","list_futures_tp_sl_orders"}

    def __init__(self,transport):self.transport=transport
    async def read(self,name,arguments):
        if name not in self.READ_TOOLS:raise TradingError("MCP_WRITE_TOOL_BLOCKED")
        return await self.transport.call(name,arguments)
    async def positions(self):
        return {"futures":await self.read("list_futures_positions",{}),"forex":await self.read("list_forex_positions",{})}
    async def capabilities(self):
        return await self.transport.list_tools()
    def prepare(self,plan,spec,*,market="futures"):
        if not spec.specs_verified:raise TradingError("contract specifications unverified")
        if market!="futures":raise TradingError("FX lot conversion requires verified broker lot specifications")
        margin=plan.entry*plan.quantity*spec.point_value/plan.leverage
        return {"status":"PREPARED_NOT_SENT","correlation_id":plan.id,"native_idempotency":False,
                "tool":"open_futures_position","arguments":{"symbol":plan.symbol,"side":plan.side.lower(),"mode":"futures",
                "marginMode":"isolated","marginUsdt":float(margin),"leverage":float(plan.leverage),
                "stopLossPrice":float(plan.stop_loss),"takeProfitPrice":float(plan.take_profits[-1].price)},
                "multiple_tp":"SOFTWARE_MANAGED_UNVALIDATED","warnings":["Numeric conversion occurs at the MCP boundary; tick/precision validation remains mandatory.",
                "Quantity is indirect through margin; actual fill and protection must be reconciled.","No native idempotency field: never retry an ambiguous submission."]}
    def submit(self,*args,**kwargs):
        raise TradingError("LIVE_EXECUTION_NOT_IMPLEMENTED_OR_ACTIVATED")


class OKXBrokerAdapter:
    name="okx"
    def prepare_demo(self,plan,spec,*,instrument_id,contracts_per_unit):
        if not spec.specs_verified:raise TradingError("contract specifications unverified")
        quantity=plan.quantity*D(contracts_per_unit)
        if quantity<=0:raise TradingError("invalid contract conversion")
        return {"status":"PREPARED_NOT_SENT","environment":"OKX_DEMO","method":"POST","path":"/api/v5/trade/order",
                "required_headers":{"x-simulated-trading":"1"},"correlation_id":plan.id,
                "body":{"instId":instrument_id,"tdMode":"isolated","side":"buy" if plan.side=="LONG" else "sell",
                        "ordType":"market","sz":str(quantity),"clOrdId":plan.id[:32],
                        "attachAlgoOrds":[{"slTriggerPx":str(plan.stop_loss),"slOrdPx":"-1","tpTriggerPx":str(plan.take_profits[-1].price),"tpOrdPx":"-1"}]},
                "limitation":"Demo request builder only; account, leverage, fills and protection reconciliation remain unqualified."}
    def prepare(self,plan,spec):raise TradingError("use prepare_demo with verified contract conversion")
    async def positions(self):raise TradingError("authenticated OKX demo transport not configured")
    def submit(self,*args,**kwargs):raise TradingError("EXCHANGE_DEMO_TRANSPORT_NOT_QUALIFIED")


class BybitBrokerAdapter:
    name="bybit"
    def prepare_demo(self,plan,spec,*,symbol):
        if not spec.specs_verified:raise TradingError("contract specifications unverified")
        return {"status":"PREPARED_NOT_SENT","environment":"BYBIT_DEMO","base_url":"https://api-demo.bybit.com",
                "method":"POST","path":"/v5/order/create","correlation_id":plan.id,
                "body":{"category":"linear","symbol":symbol,"side":"Buy" if plan.side=="LONG" else "Sell",
                        "orderType":"Market","qty":str(plan.quantity),"orderLinkId":plan.id[:36],"positionIdx":0,
                        "stopLoss":str(plan.stop_loss),"takeProfit":str(plan.take_profits[-1].price),"tpslMode":"Full"},
                "limitation":"Demo request builder only. Requires an actual demo key, account mode and fill reconciliation."}
    def prepare(self,plan,spec):raise TradingError("use prepare_demo with verified symbol")
    async def positions(self):raise TradingError("authenticated Bybit demo transport not configured")
    def submit(self,*args,**kwargs):raise TradingError("EXCHANGE_DEMO_TRANSPORT_NOT_QUALIFIED")
