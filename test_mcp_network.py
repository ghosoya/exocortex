"""
test_mcp_network.py (v1.5.0)
Automated network/SSE integration tests for Exocortex MCP Daemon.
Tests tool discovery, temporal anchoring, graph querying, and node creation.
"""

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    print("[*] Connecting to Exocortex MCP Daemon via SSE...")
    async with sse_client("http://127.0.0.1:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 1. Tool-Discovery: Genau 11 saubere Tools registriert
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"\n[OK] Connected MCP Tools ({len(tool_names)}): {tool_names}")
            assert "exocortex_create_node" in tool_names
            assert "exocortex_query_graph" in tool_names
            assert "exocortex_mutate_node" in tool_names
            assert "exocortex_imprint_field" not in tool_names, "Legacy alias should be gone!"

            # 2. Zeit-Anker abrufen
            res_time = await session.call_tool("exocortex_temporal_anchor", arguments={"scope": "full"})
            print(f"\n[TOOL RESULT] exocortex_temporal_anchor:\n{res_time.content[0].text}")

            # 3. Kontext-Abfrage über das Netzwerk
            print("\n[*] Testing exocortex_query_graph...")
            res_query = await session.call_tool(
                "exocortex_query_graph", 
                arguments={"query": "Architecture Decoupling", "top_k": 2}
            )
            print(f"[TOOL RESULT] exocortex_query_graph:\n{res_query.content[0].text}")

            # 4. Knoten mit Link auf CST_001 anlegen
            print("\n[*] Testing exocortex_create_node...")
            res_create = await session.call_tool(
                "exocortex_create_node",
                arguments={
                    "node_type": "State",
                    "label": "Network_SSE_Validation_Trace",
                    "content_payload": "Automated verification of remote MCP tool dispatch and canvas sync.",
                    "links": ["CST_001"]
                }
            )
            create_text = res_create.content[0].text
            print(f"[TOOL RESULT] exocortex_create_node:\n{create_text}")
            assert "Node materialized" in create_text
            assert "Network_SSE_Validation_Trace" in create_text
            assert "CST_001" in create_text

            print("\n[SUCCESS] All remote MCP network integration checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
