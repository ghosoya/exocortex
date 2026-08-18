#!/usr/bin/env python3
"""
server/exocortex_mcp_server.py
MCP-Server-Schnittstelle (FastMCP).
Exponiert Vault-I/O und den Phasenraum als standardisierte MCP-Tools.
"""

from typing import List, Optional
import datetime
from mcp.server.fastmcp import FastMCP

from server.vault_io import VaultIO
from server.graph_store import GraphStore

# FastMCP Server-Instanz
mcp = FastMCP("Exocortex-Daemon")

# Substrat-Instanzen (State in Objekten gekapselt)
vault_io = VaultIO()
graph_store = GraphStore(vault_io=vault_io)


@mcp.tool()
def read_vault_note(note_name: str) -> str:
    """Liest den Inhalt einer Markdown-Notiz aus dem Obsidian-Vault."""
    try:
        content = vault_io.read_note(note_name)
        return f"<vault_note path='{note_name}'>\n{content}\n</vault_note>"
    except Exception as e:
        return f"<error>Fehler beim Lesen von '{note_name}': {e}</error>"


@mcp.tool()
def append_scratchpad(content: str, filename: str = "Active_Scratchpad.md") -> str:
    """Hängt Text oder Zwischenergebnisse an eine Scratchpad-Notiz im Vault an."""
    try:
        path = vault_io.append_scratchpad(content, filename)
        return f"<scratchpad status='appended' path='{path}' />"
    except Exception as e:
        return f"<error>Fehler beim Schreiben ins Scratchpad: {e}</error>"


@mcp.tool()
def exocortex_gauge_field(query_vector: str, top_k: int = 3) -> str:
    """Misst Resonanzknoten im aktuellen Phasenraum für ein semantisches Thema."""
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
        return f"<error>Field Gauge Fehler: {e}</error>"


@mcp.tool()
def exocortex_imprint_field(
    node_type: str,
    label: str,
    content_payload: str,
    tensor_links: Optional[List[str]] = None,
) -> str:
    """Prägt einen neuen Erkenntnis-Knoten deterministisch in die aktive Topologie ein."""
    try:
        res = graph_store.imprint_node(node_type, label, content_payload, tensor_links)
        conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "Keine"
        return (
            f"Field state materialized: Node {res['node_id']} ('{label}') wired into '{res['topology']}'. "
            f"| Verdrahtet mit: {conns}"
        )
    except Exception as e:
        return f"<error>Imprinting Fehler: {e}</error>"


@mcp.tool()
def exocortex_temporal_anchor(scope: str = "full") -> str:
    """Gibt das aktuelle Systemdatum, Uhrzeit und Kalenderwoche zurück."""
    now = datetime.datetime.now()
    iso = now.isoformat()
    human = now.strftime("%d.%m.%Y, %H:%M:%S")
    kw = now.isocalendar()[1]
    return (
        f"<temporal_anchor>\n"
        f"  <human_readable>{human}</human_readable>\n"
        f"  <iso8601>{iso}</iso8601>\n"
        f"  <calendar_context>KW {kw}, Jahr {now.year}</calendar_context>\n"
        f"</temporal_anchor>"
    )


@mcp.tool()
def exocortex_switch_topology(topology_name: str) -> str:
    """Wechselt die aktive Graph-Topologie zur Laufzeit."""
    try:
        stats = graph_store.load_graph(topology_name)
        return f"<topology_switched name='{stats['name']}' nodes='{stats['node_count']}' edges='{stats['edge_count']}' />"
    except Exception as e:
        return f"<error>Topologie-Wechsel fehlgeschlagen: {e}</error>"


if __name__ == "__main__":
    import sys
    
    # Prüfen, ob als SSE (Netzwerk) oder Stdio (Pipe) gestartet werden soll
    if "--stdio" in sys.argv:
        print("[*] Starte Exocortex MCP Daemon im Stdio-Modus...")
        mcp.run(transport="stdio")
    else:
        print("[*] Starte Exocortex MCP Daemon via SSE auf http://127.0.0.1:8000/sse ...")
        mcp.run(transport="sse")
