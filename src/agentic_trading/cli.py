from dataclasses import asdict,replace
from pathlib import Path
import argparse
import asyncio
import json
import os
import sys
from .config import Settings,load_private_env
from .models import Candle, Instrument, TradingError, dumps, now_utc,utc
from .storage import Store


def load_bundle(path):
    data=json.loads(Path(path).read_text(encoding="utf8"))
    markets={s:[Candle.from_dict(row) for row in rows] for s,rows in data["markets"].items()}
    specs={s:Instrument(symbol=s,**v) for s,v in data["instruments"].items()}
    return data,markets,specs


def build_parser():
    parser=argparse.ArgumentParser(prog="agentic-trading")
    parser.add_argument("--database",default=os.environ.get("TRADING_DATABASE_URL","state/trading.sqlite"))
    sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo");demo.add_argument("--output");demo.add_argument("--account",default="synthetic-demo")
    scan=sub.add_parser("scan");scan.add_argument("--config",required=True);scan.add_argument("--bundle",required=True);scan.add_argument("--now")
    report=sub.add_parser("report");report.add_argument("--account",default="local-paper")
    perf=sub.add_parser("performance");perf.add_argument("--account",default="local-paper")
    perf.add_argument("--period",choices=["all","day","week","month"],default="all")
    perf.add_argument("--group-by",choices=["symbol","strategy","platform","regime","mode"],default="symbol")
    perf.add_argument("--capital",default="1250")
    halt=sub.add_parser("halt");halt.add_argument("--account",default="local-paper")
    resume=sub.add_parser("resume");resume.add_argument("--account",default="local-paper");resume.add_argument("--operator-confirm",action="store_true")
    mail=sub.add_parser("notify");mail.add_argument("--limit",type=int,default=50)
    bt=sub.add_parser("backtest");bt.add_argument("--bundle",required=True);bt.add_argument("--symbol",default="BTC");bt.add_argument("--output")
    sub.add_parser("top100")
    moon=sub.add_parser("moonx-read");moon.add_argument("--symbol",default="BTC");moon.add_argument("--output",required=True)
    sub.add_parser("mcp-server")
    worker=sub.add_parser("worker");worker.add_argument("--config",required=True);worker.add_argument("--bundle",required=True)
    worker.add_argument("--once",action="store_true");worker.add_argument("--send-email",action="store_true")
    return parser


def main(argv=None):
    load_private_env()
    args=build_parser().parse_args(argv)
    try:
        store=Store(args.database)
        if args.command=="demo":
            from .demo import scenario
            from .orchestrator import AgenticTradingOrchestrator
            from .quantitative import performance
            scene=scenario();settings=Settings(account=args.account,watchlist=("BTC",))
            engine=AgenticTradingOrchestrator(settings,store)
            run=engine.run({"BTC":scene["bars"]},{"BTC":scene["spec"]},scene["now"],macro=scene["macro"],liquidity=scene["liquidity"],validation={},synthetic_demonstration=True)
            exits=[]
            for bar in scene["exit_bars"]:exits.extend(engine.paper.monitor("BTC",bar))
            result={"label":"SYNTHETIC_DEMONSTRATION_NOT_MARKET_PERFORMANCE","run":run,"exits":exits,"state":store.report(args.account)}
            result["performance"]=performance([p["net_pnl"] for p in result["state"]["positions"] if p["status"]=="CLOSED"])
            if args.output:Path(args.output).write_text(dumps(result),encoding="utf8")
        elif args.command=="scan":
            from .orchestrator import AgenticTradingOrchestrator
            settings=Settings.load(args.config);data,markets,specs=load_bundle(args.bundle)
            result=AgenticTradingOrchestrator(settings,store).run(markets,specs,utc(args.now) if args.now else now_utc(),macro=data.get("macro",{}),liquidity=data.get("liquidity",{}),validation=data.get("validation",{}))
        elif args.command=="report":result=store.report(args.account)
        elif args.command=="performance":
            from .reporting import performance_report
            result=performance_report(store,args.account,now_utc(),period=args.period,group_by=args.group_by,reference_capital=args.capital)
        elif args.command=="halt":store.halt(args.account);result={"status":"HALTED","account":args.account}
        elif args.command=="resume":store.resume(args.account,administrative_confirmation=args.operator_confirm);result={"status":"RESUMED","account":args.account}
        elif args.command=="notify":
            from .notifications import NotificationWorker,SMTPEmailSender
            result=NotificationWorker(store,SMTPEmailSender()).flush(now_utc(),args.limit)
        elif args.command=="backtest":
            from .backtesting import backtest
            data,markets,specs=load_bundle(args.bundle)
            result=backtest(markets[args.symbol],specs[args.symbol],scratch=str(Path(args.database).parent))
            if args.output:Path(args.output).write_text(dumps(result),encoding="utf8")
        elif args.command=="top100":
            from .market_data import CoinMarketCapUniverse
            result=CoinMarketCapUniverse().top100(store,now_utc())
        elif args.command=="moonx-read":
            from .remote_mcp import moonx_session
            url=os.environ.get("MOONX_MCP_URL")
            if not url:raise TradingError("MOONX_MCP_URL_REQUIRED")
            async def read():
                async with moonx_session(url) as broker:
                    return await broker.read("get_candles",{"symbol":args.symbol,"interval":"1h","limit":500})
            result=asyncio.run(read());Path(args.output).write_text(dumps(result),encoding="utf8")
        elif args.command=="mcp-server":
            from .mcp_server import serve
            serve(args.database);return 0
        elif args.command=="worker":
            from .scheduler import worker
            worker(Settings.load(args.config),store,args.bundle,once=args.once,send_email=args.send_email);return 0
        print(dumps(result))
        return 0
    except (TradingError,OSError,ValueError,KeyError) as exc:
        # Only predictable application errors are exposed. Unknown network errors are sanitized at adapters.
        print(dumps({"status":"ERROR","error":str(exc)}),file=sys.stderr)
        return 2


if __name__=="__main__":raise SystemExit(main())
