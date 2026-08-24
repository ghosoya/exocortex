"""
test_mcp_network.py (v1.4.1)
Automated network/SSE integration tests for Exocortex MCP Daemon.
Tests tool discovery, temporal anchoring, phase space gauging, and field imprinting.
"""

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    print("[*] Connecting to Exocortex MCP Daemon via SSE...")
    async with sse_client("http://127.0.0.1:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # 1. List available tools & verify registration
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"\n[OK] Connected MCP Tools ({len(tool_names)}): {tool_names}")
            assert "exocortex_imprint_field" in tool_names, "Tool 'exocortex_imprint_field' not exposed!"
            
            # 2. Retrieve temporal anchor
            res_time = await session.call_tool("exocortex_temporal_anchor", arguments={"scope": "full"})
            print(f"\n[TOOL RESULT] exocortex_temporal_anchor:\n{res_time.content[0].text}")
            
            # 3. Gauge phase space over the network
            res_gauge = await session.call_tool(
                "exocortex_gauge_field", 
                arguments={"query_vector": "Architecture Decoupling", "top_k": 2}
            )
            print(f"\n[TOOL RESULT] exocortex_gauge_field:\n{res_gauge.content[0].text}")

            # 4. Imprint field state with tensor links (E2E Schema & Persistence Test)
            print("\n[*] Testing exocortex_imprint_field (with tensor_links)...")
            res_imprint = await session.call_tool(
                "exocortex_imprint_field",
                arguments={
                    "node_type": "PhaseSpaceTrace",
                    "label": "Network_SSE_Validation_Trace",
                    "content_payload": "Automated verification of remote MCP tool dispatch and canvas sync.",
                    "tensor_links": ["BC_001"]
                }
            )
            imprint_text = res_imprint.content[0].text
            print(f"[TOOL RESULT] exocortex_imprint_field:\n{imprint_text}")
            assert "Field state materialized" in imprint_text
            assert "Network_SSE_Validation_Trace" in imprint_text
            assert "Wired to: BC_001" in imprint_text

            # 5. Imprint field state without tensor links (Optional Parameter Test)
            print("\n[*] Testing exocortex_imprint_field (optional tensor_links omitted)...")
            res_imprint_opt = await session.call_tool(
                "exocortex_imprint_field",
                arguments={
                    "node_type": "BoundaryConstraint",
                    "label": "Isolated_Constraint_Trace",
                    "content_payload": "Testing schema default handling for empty tensor link lists."
                }
            )
            opt_text = res_imprint_opt.content[0].text
            print(f"[TOOL RESULT] exocortex_imprint_field (omitted links):\n{opt_text}")
            assert "Field state materialized" in opt_text
            assert "Wired to: None" in opt_text

            print("\n[SUCCESS] All remote MCP network integration checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
