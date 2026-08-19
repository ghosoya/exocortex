"""
test_mcp_network.py (v1.4.0)
Automated unit and integration tests for Exocortex.
Tests VaultIO, Guards, SessionManager, GraphStore, and ExecutionEngine in isolation.
"""

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    print("[*] Connecting to Exocortex MCP Daemon via SSE...")
    async with sse_client("http://127.0.0.1:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # 1. List available tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"\n[OK] Connected MCP Tools ({len(tool_names)}): {tool_names}")
            
            # 2. Retrieve temporal anchor
            res_time = await session.call_tool("exocortex_temporal_anchor", arguments={"scope": "full"})
            print(f"\n[TOOL RESULT] exocortex_temporal_anchor:\n{res_time.content[0].text}")
            
            # 3. Gauge phase space over the network
            res_gauge = await session.call_tool("exocortex_gauge_field", arguments={"query_vector": "Architecture Decoupling", "top_k": 2})
            print(f"\n[TOOL RESULT] exocortex_gauge_field:\n{res_gauge.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
    
