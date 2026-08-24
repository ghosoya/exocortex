#!/usr/bin/env python3
"""
server/exocortex_mcp_server.py
MCP server interface (FastMCP).
Exposes vault I/O and the phase space as standardized MCP tools with fail-safe boundaries.
"""

from typing import List, Optional
import argparse
import datetime
import json
from mcp.server.fastmcp import FastMCP

from core.config import settings
from server.vault_io import VaultIO
from server.graph_store import GraphStore
from core.prompts import PromptManager
from pydantic import Field

# FastMCP server instance
mcp = FastMCP("Exocortex-Daemon")

# Substrate instances
vault_io = VaultIO()
graph_store = GraphStore(vault_io=vault_io)
prompt_manager = PromptManager()


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
    node_type: str = Field(
        ...,
        description="Allowed values: 'BoundaryConstraint', 'PotentialWell', 'TrajectoryOperator', 'PhaseSpaceTrace'",
    ),
    label: str = Field(
        ...,
        description="Compact snake_case or CamelCase identifier, e.g. 'Projective_Decoupling'",
    ),
    content_payload: str = Field(
        ...,
        description="Axiomatic content, synthesis mechanism, or invariant payload",
    ),
    tensor_links: List[str] = Field(
        default_factory=list,
        description="Optional: List of existing target node IDs to link to (e.g. ['PW_004', 'TO_003']). Leave empty or omit if no links exist. Do NOT use dicts or integers.",
    ),
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
    """Modulates, updates, decays, sets weight, or prunes an existing node in the active phase space."""
    try:
        res = graph_store.mutate_node(
            target_node_id=target_node_id,
            action=action,
            payload_update=payload_update,
            delta=delta
        )
        if res.get("status") == "error":
            return f"<phase_space_mutation status='error' message='{res.get('message')}' />"
        return f"<phase_space_mutation status='success' node_id='{target_node_id}' action='{action.upper()}' />"
    except Exception as e:
        return f"<error>Phase space mutation failed: {e}</error>"


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

@mcp.tool()
def exocortex_inspect_payload(query: str = "") -> str:
    """
    Assembles and returns the full compiled system prompt payload 
    (base stance + immutable boundary invariants + optional dynamic resonant field).
    """
    try:
        invariants_xml = graph_store.assemble_invariants_frame()
        field_xml = graph_store.assemble_field_context(query) if query else ""
        return prompt_manager.build_system_prompt(
            field_xml=field_xml, 
            invariants_xml=invariants_xml
        )
    except Exception as e:
        return f"<error>Failed to compile payload: {e}</error>"

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
