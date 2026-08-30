#!/usr/bin/env python3
"""
server/exocortex_mcp_server.py
MCP server interface (FastMCP).
Exposes vault I/O and the knowledge graph as standardized MCP tools with fail-safe boundaries.
"""

from typing import List, Optional, Union
import argparse
import datetime
import json
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from core.config import settings
from server.vault_io import VaultIO
from server.graph_store import GraphStore, NodeType, cosine_similarity
from core.prompts import PromptManager
from core.guards import slice_for_embedding

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
def exocortex_query_graph(query: str, top_k: int = 3) -> str:
    """Queries relevant context nodes and 1-hop graph links within the active topology."""
    try:
        return graph_store.assemble_context_frame(query)
    except Exception as e:
        return f"<error>Graph query error: {e}</error>"
        

@mcp.tool()
def exocortex_get_topology_stats() -> str:
    """Returns active topology name, node count, and edge count."""
    try:
        stats = graph_store.get_graph_stats()
        return json.dumps(stats)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def exocortex_create_node(
    node_type: str = Field(
        ...,
        description="Allowed values: 'Constraint', 'Concept', 'Rule', 'State' (legacy formats are normalized automatically)",
    ),
    label: str = Field(
        ...,
        description="Compact snake_case or CamelCase identifier, e.g. 'Projective_Decoupling'",
    ),
    content_payload: str = Field(
        ...,
        description="Axiomatic principle, operational rule, constraint, or state payload",
    ),
    links: Optional[List[str]] = Field(
        default=None,
        description="Optional: List of existing target node IDs to link to (e.g. ['CNC_001', 'RUL_002']). Omit if no links exist.",
    ),
) -> str:
    """Deterministically creates a new node in the active knowledge graph."""
    try:
        target_links = links if isinstance(links, list) else []
        res = graph_store.imprint_node(
            node_type=node_type,
            label=label,
            content_payload=content_payload,
            links=target_links,
        )
        conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "None"
        return (
            f"Node materialized: {res['node_id']} ('{label}') [{node_type}] wired into '{res['topology']}'. "
            f"| Connected to: {conns}"
        )
    except Exception as e:
        return f"<error>Node creation error: {e}</error>"


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
def exocortex_mutate_node(
    target_node_id: str,
    action: str,
    payload_update: Optional[str] = None,
    delta: float = 0.2
) -> str:
    """Modulates weight, updates payload, or prunes an existing node in the active graph."""
    try:
        res = graph_store.mutate_node(
            target_node_id=target_node_id,
            action=action,
            payload_update=payload_update,
            delta=delta
        )
        if res.get("status") == "error":
            return f"<graph_mutation status='error' message='{res.get('message')}' />"
        return f"<graph_mutation status='success' node_id='{target_node_id}' action='{action.upper()}' />"
    except Exception as e:
        return f"<error>Graph mutation failed: {e}</error>"


@mcp.tool()
def exocortex_freeze_snapshot(tag: Optional[str] = None) -> str:
    """
    Freezes the active graph topology into an immutable snapshot (JSON + Canvas).
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
def exocortex_inspect_payload(query: str = "", profile: Optional[str] = None) -> str:
    """
    Assembles and returns the full compiled system prompt payload 
    (base stance + immutable constraints + optional dynamic context frame).
    """
    try:
        if profile and profile in prompt_manager.list_profiles():
            prompt_manager.set_profile(profile)
        constraints_xml = graph_store.assemble_constraints_frame()
        context_xml = graph_store.assemble_context_frame(query) if query else ""
        return prompt_manager.build_system_prompt(
            context_xml=context_xml, 
            constraints_xml=constraints_xml
        )
    except Exception as e:
        return f"<error>Failed to compile payload: {e}</error>"

@mcp.tool()
def exocortex_compute_telemetry(prompt: str, response: str) -> str:
    """Computes echo ratio and semantic alignment against the active graph."""
    try:
        if not prompt.strip() or not response.strip():
            return json.dumps({"echo": 0.0, "delta_e": None, "attractor": None})

        p_vec = graph_store._get_embedding(slice_for_embedding(prompt))
        r_vec = graph_store._get_embedding(slice_for_embedding(response))
        echo = round(cosine_similarity(p_vec, r_vec), 2)

        telemetry = {"echo": echo, "delta_e": None, "attractor": None}

        # Ähnlichste Knoten prüfen
        resonant = graph_store.get_resonant_nodes(slice_for_embedding(prompt), top_k=3)
        if resonant:
            best_nid, best_attrs, _ = resonant[0]
            w_vec = best_attrs.get("embedding", [])
            if w_vec:
                sim_p_w = cosine_similarity(p_vec, w_vec)
                sim_r_w = cosine_similarity(r_vec, w_vec)
                telemetry["delta_e"] = round(sim_r_w - sim_p_w, 2)
                telemetry["attractor"] = best_attrs.get("label", best_nid)

        return json.dumps(telemetry)
    except Exception as e:
        print(f"[!] Server telemetry error: {e}")
        return json.dumps({"echo": 0.0, "delta_e": None, "attractor": None, "error": str(e)})


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
