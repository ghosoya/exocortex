#!/usr/bin/env python3
"""
server/exocortex_mcp_server.py
MCP server interface (FastMCP).
Exposes vault I/O and the phase space as standardized MCP tools.
"""

from typing import List, Optional
import datetime
import argparse
from mcp.server.fastmcp import FastMCP

from core.config import settings
from server.vault_io import VaultIO
from server.graph_store import GraphStore
import json

# FastMCP server instance
mcp = FastMCP("Exocortex-Daemon")

# Substrate instances (transparently utilize settings.vault_path etc.)
vault_io = VaultIO()
graph_store = GraphStore(vault_io=vault_io)


@mcp.tool()
def read_vault_note(note_name: str) -> str:
    """Reads the content of a Markdown note from the Obsidian vault."""
    try:
        content = vault_io.read_note(note_name)
        return f"<vault_note path='{note_name}'>\n{content}\n</vault_note>"
    except Exception as e:
        return f"<error>Error reading '{note_name}': {e}</error>"


@mcp.tool()
def append_scratchpad(content: str, filename: str = "Active_Scratchpad.md") -> str:
    """Appends text or intermediate findings to a scratchpad note in the vault."""
    try:
        path = vault_io.append_scratchpad(content, filename)
        return f"<scratchpad status='appended' path='{path}' />"
    except Exception as e:
        return f"<error>Error writing to scratchpad: {e}</error>"


@mcp.tool()
def exocortex_gauge_field(query_vector: str, top_k: int = 3) -> str:
    """Gauges resonant nodes within the active phase space for a semantic topic."""
    try:
        resonant = graph_store.get_resonant_nodes(query_vector, top_k=top_k)
        if not resonant:
            return "<field_gauge status='quiescent' />"

        lines = [f"<field_gauge query='{query_vector}' topology='{graph_store.active_graph_name}'>"]
        for node_id, attrs, sim in resonant:
            lines.append(
                f"  <resonance id='{node_id}' label='{attrs.get('label')}' type='{attrs.get('type')}' score='{sim:.2f}'>\n"
                f"    {attrs.get('payload', '')}\n"
                f"  </resonance>"
            )
        lines.append("</field_gauge>")
        return "\n".join(lines)
    except Exception as e:
        return f"<error>Field Gauge error: {e}</error>"


@mcp.tool()
def exocortex_imprint_field(
    node_type: str,
    label: str,
    content_payload: str,
    tensor_links: Optional[List[str]] = None,
) -> str:
    """Deterministically imprints a new insight node into the active topology."""
    try:
        res = graph_store.imprint_node(node_type, label, content_payload, tensor_links)
        conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "None"
        return (
            f"Field state materialized: Node {res['node_id']} ('{label}') wired into '{res['topology']}'. "
            f"| Wired to: {conns}"
        )
    except Exception as e:
        return f"<error>Imprinting error: {e}</error>"


@mcp.tool()
def exocortex_temporal_anchor(scope: str = "full") -> str:
    """Returns current system date, time, and calendar week."""
    now = datetime.datetime.now()
    iso = now.isoformat()
    human = now.strftime("%Y-%m-%d %H:%M:%S")
    kw = now.isocalendar()[1]
    return (
        f"<temporal_anchor>\n"
        f"  <human_readable>{human}</human_readable>\n"
        f"  <iso8601>{iso}</iso8601>\n"
        f"  <calendar_context>Week {kw}, Year {now.year}</calendar_context>\n"
        f"</temporal_anchor>"
    )


@mcp.tool()
def exocortex_switch_topology(topology_name: str) -> str:
    """Switches the active graph topology at runtime."""
    try:
        stats = graph_store.load_graph(topology_name)
        return f"<topology_switched name='{stats['name']}' nodes='{stats['node_count']}' edges='{stats['edge_count']}' />"
    except Exception as e:
        return f"<error>Topology switch failed: {e}</error>"
        
@mcp.tool()
def exocortex_mutate_phase_space(
    target_node_id: str,
    action: str,
    payload_update: Optional[str] = None,
    delta: float = 0.2
) -> str:
    """Modulates, updates, decays, sets weight, or prunes an existing node in the active phase space (actions: STRENGTHEN, DECAY, SET_WEIGHT, PRUNE, UPDATE)."""
    res = graph_store.mutate_node(
        target_node_id=target_node_id,
        action=action,
        payload_update=payload_update,
        delta=delta
    )
    if res.get("status") == "error":
        return f"<phase_space_mutation status='error' message='{res.get('message')}' />"
    return f"<phase_space_mutation status='success' node_id='{target_node_id}' action='{action.upper()}' />"

@mcp.tool()
def exocortex_freeze_snapshot(tag: Optional[str] = None) -> str:
    """
    Freezes the active phase space topology into an immutable snapshot (JSON + Canvas).
    Returns snapshot metadata and created file paths.
    """
    try:
        res = graph_store.freeze_snapshot(tag)
        return json.dumps({
            "status": "success",    
            "snapshot_name": res["snapshot_name"],
            "json_path": res["json_path"],
            "canvas_path": res["canvas_path"]
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exocortex FastMCP Server Daemon")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (pipe)")
    parser.add_argument("--host", default=settings.mcp_host, help=f"Bind host (default: {settings.mcp_host})")
    parser.add_argument("--port", type=int, default=settings.mcp_port, help=f"Bind port (default: {settings.mcp_port})")
    args = parser.parse_args()

    if args.stdio:
        print("[*] Starting Exocortex MCP Daemon in stdio mode...")
        mcp.run(transport="stdio")
    else:
        print(f"[*] Starting Exocortex MCP Daemon via SSE on http://{args.host}:{args.port}/sse ...")
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
