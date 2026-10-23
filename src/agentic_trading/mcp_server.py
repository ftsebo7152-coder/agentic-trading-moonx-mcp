"""Local MCP tools. Modes and risk ceilings are not exposed as mutable tool inputs."""
from .storage import Store


def serve(database):
    import os
    from mcp.server.fastmcp import FastMCP
    server=FastMCP("agentic-trading-paper")
    store=Store(database)

    @server.tool()
    def trading_report(account:str="local-paper")->dict:
        """Read persistent simulated positions, trades and notification queue."""
        return store.report(account)

    @server.tool()
    def trading_halt(account:str="local-paper")->dict:
        """Stop new entries. Protective exits remain enabled."""
        store.halt(account);return {"status":"HALTED"}

    @server.tool()
    def trading_scan()->dict:
        """Run an isolated PAPER scan with preconfigured administrative risk limits."""
        from .config import Settings
        from .cli import load_bundle
        from .models import now_utc
        from .orchestrator import AgenticTradingOrchestrator
        settings=Settings.load(os.environ["TRADING_CONFIG_PATH"])
        data,markets,specs=load_bundle(os.environ["TRADING_BUNDLE_PATH"])
        return AgenticTradingOrchestrator(settings,store).run(markets,specs,now_utc(),macro=data.get("macro",{}),liquidity=data.get("liquidity",{}),validation=data.get("validation",{}))

    server.run(transport="stdio")
