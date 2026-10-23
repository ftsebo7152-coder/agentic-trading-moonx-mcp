"""Read-only Streamable HTTP MoonX session using the official MCP Python SDK."""
from contextlib import asynccontextmanager
import json
from urllib.parse import urlsplit
from .brokers import MoonXBrokerAdapter
from .models import TradingError


class SDKMCPTransport:
    def __init__(self,session):self.session=session
    async def list_tools(self):
        response=await self.session.list_tools()
        return [{"name":t.name,"inputSchema":t.inputSchema,"description":t.description} for t in response.tools]
    async def call(self,name,arguments):
        if name not in MoonXBrokerAdapter.READ_TOOLS:raise TradingError("MCP_WRITE_TOOL_BLOCKED")
        response=await self.session.call_tool(name,arguments)
        if response.isError:raise TradingError("MCP_TOOL_ERROR")
        texts=[item.text for item in response.content if item.type=="text"]
        if len(texts)!=1:raise TradingError("AMBIGUOUS_MCP_RESPONSE")
        try:return json.loads(texts[0])
        except (ValueError,TypeError):raise TradingError("INVALID_MCP_JSON") from None


@asynccontextmanager
async def moonx_session(url):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname!="api.moon-x.io" or parsed.username or parsed.password:
        raise TradingError("official MoonX HTTPS origin required")
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        async with streamablehttp_client(url) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                yield MoonXBrokerAdapter(SDKMCPTransport(session))
    except TradingError:raise
    except Exception:
        # Avoid leaking the personal MCP URL in an exception string.
        raise TradingError("MOONX_SESSION_FAILED") from None
