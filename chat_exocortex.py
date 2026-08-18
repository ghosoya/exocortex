#!/usr/bin/env python3
"""
chat_exocortex.py (v1.4.0)
Universeller Terminal-Runner mit Dual-Mode-Unterstützung:
  1. Embedded Mode (Lokal via direkte Klasseninstanzen)
  2. Remote Mode   (Netzwerk via FastMCP / SSE Client)
"""

import traceback
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

# Fallback für prompt_toolkit
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

import ollama

# Konfiguration & Kognition
from core.config import settings
from core.prompts import PromptManager
from core.session import SessionManager
from core.engine import ExecutionEngine
from core.guards import slice_for_embedding, prune_history_if_needed

# Lokale Substrate
from server.vault_io import VaultIO
from server.graph_store import GraphStore

# MCP Client Imports für den Remote-Modus
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# ANSI Farbcodes
C_CYAN = "\033[1;36m"
C_YELLOW = "\033[1;33m"
C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_GRAY = "\033[90m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"


# ==============================================================================
# PROMPT COMMAND HANDLER (FÜR BEIDE MODI)
# ==============================================================================
def handle_prompt_command(user_input: str, prompt_manager: PromptManager):
    """Zentraler Handler für /prompt Subkommandos."""
    parts = user_input.split()
    sub = parts[1].lower() if len(parts) > 1 else "list"

    if sub == "list":
        profiles = prompt_manager.list_profiles()
        active = prompt_manager.active_profile
        print(f"\n{C_CYAN}[PROMPTS]{C_RESET} Kognitive Linsen / Profile:")
        for p in profiles:
            mark = f" {C_GREEN}(aktiv){C_RESET}" if p == active else ""
            print(f"  • {p}{mark}")
        print()
    elif sub == "set" and len(parts) > 2:
        target = parts[2]
        if prompt_manager.set_profile(target):
            print(f"{C_GREEN}[OK] Kognitives Profil gewechselt auf: '{target}'{C_RESET}\n")
        else:
            print(f"{C_RED}[ERROR] Profil '{target}' nicht gefunden.{C_RESET}\n")
    elif sub == "show":
        print(f"\n{C_CYAN}{'=' * 60}{C_RESET}")
        print(f"{C_BOLD}[AKTIVER BASIS-SYSTEM-PROMPT ({prompt_manager.active_profile})]{C_RESET}")
        print(f"{C_CYAN}{'=' * 60}{C_RESET}")
        print(prompt_manager.get_base_prompt())
        print(f"{C_CYAN}{'=' * 60}{C_RESET}\n")
    elif sub == "reset":
        prompt_manager.reset()
        print(f"{C_GREEN}[OK] Prompt auf Standardprofil ('default') zurückgesetzt.{C_RESET}\n")
    else:
        print(f"{C_YELLOW}[INFO] Verwendung: /prompt [list | set <profil> | show | reset]{C_RESET}\n")


def list_available_sessions(vault_io: VaultIO) -> List[str]:
    """Liest alle gespeicherten Sessions aus dem Sessions-Ordner des Vaults."""
    sessions_dir = vault_io.vault_path / "Sessions"
    if not sessions_dir.exists():
        return []
    # JSON-Dateien ohne Endung sammeln
    return sorted([f.stem for f in sessions_dir.glob("*.json")])


# ==============================================================================
# REMOTE MCP ADAPTER (FÜR --remote)
# ==============================================================================
class RemoteMCPEngine:
    """Orchestriert Kognition über einen entfernten FastMCP-Daemon via SSE."""

    def __init__(
        self,
        sse_url: str,
        session_manager: SessionManager,
        model_name: Optional[str] = None,
        num_ctx: Optional[int] = None,
        prompt_manager: Optional[PromptManager] = None,
    ):
        self.sse_url = sse_url
        self.session = session_manager
        self.model_name = model_name if model_name is not None else settings.chat_model
        self.num_ctx = num_ctx if num_ctx is not None else settings.context_window
        self.client = ollama.Client(host=settings.ollama_host)
        self.prompt_manager = prompt_manager or PromptManager()
        self.tools_schema: List[Dict[str, Any]] = []

    async def initialize(self, mcp_session: ClientSession):
        tools_list = await mcp_session.list_tools()
        self.tools_schema = []
        for t in tools_list.tools:
            self.tools_schema.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema or {"type": "object", "properties": {}},
                },
            })

    async def execute_turn(self, user_input: str, mcp_session: ClientSession, max_turns: int = 5):
        # 1. Resonanz über Remote Daemon messen
        safe_query = slice_for_embedding(user_input)
        try:
            gauge_res = await mcp_session.call_tool("exocortex_gauge_field", arguments={"query_vector": safe_query, "top_k": 4})
            field_xml = gauge_res.content[0].text if gauge_res.content else "<active_phase_space status='quiescent' />"
        except Exception:
            field_xml = "<active_phase_space status='quiescent' />"

        yield {"event": "field_context", "xml": field_xml}

        # 2. System-Prompt dynamisch aus PromptManager beziehen
        base_prompt = self.prompt_manager.get_base_prompt()
        full_system_prompt = f"{base_prompt}\n\n### Aktiver Phasenraum (Remote):\n{field_xml}"

        # 3. Session updaten
        self.session.add_user_message(user_input)
        history = prune_history_if_needed(self.session.messages)
        messages_payload = [{"role": "system", "content": full_system_prompt}] + history

        turn_count = 0
        while turn_count < max_turns:
            turn_count += 1

            # Non-blocking Chat-Aufruf via Thread
            response = await asyncio.to_thread(
                self.client.chat,
                model=self.model_name,
                messages=messages_payload,
                tools=self.tools_schema,
                options={"num_ctx": self.num_ctx},
            )

            msg = response.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                messages_payload.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

                for call in tool_calls:
                    fn_name = call.get("function", {}).get("name", "")
                    fn_args = call.get("function", {}).get("arguments", {})

                    yield {"event": "tool_call", "name": fn_name, "args": fn_args}

                    # Remote Tool Execution über FastMCP
                    try:
                        res = await mcp_session.call_tool(fn_name, arguments=fn_args)
                        tool_result = res.content[0].text if res.content else ""
                    except Exception as e:
                        tool_result = f"<error>Remote Tool Fehler: {e}</error>"

                    yield {"event": "tool_result", "result": tool_result}
                    messages_payload.append({"role": "tool", "content": tool_result})
            else:
                yield {"event": "completed", "final_text": content}
                self.session.add_assistant_message(content)
                break


# ==============================================================================
# UI & BANNER
# ==============================================================================
def print_banner(mode: str, target: str, model: str):
    print(f"{C_CYAN}{'=' * 70}{C_RESET}")
    print(f"{C_BOLD}[*] EXOCORTEX ONLINE v1.4.0 (Dual-Mode Runner){C_RESET}")
    print(f"[*] Modus: {C_GREEN}{mode.upper()}{C_RESET} | Ziel: {C_YELLOW}{target}{C_RESET} | Modell: {C_CYAN}{model}{C_RESET}")
    print(f"[*] Senden: [Enter] | Zeilenumbruch: [Alt+Enter] | Ende: 'exit'")
    print(f"[*] Befehle: /save | /load | /prompt | /context | /clear | /help" + (" | /graph" if mode == "local" else " | /switch <Topologie>"))
    print(f"{C_CYAN}{'=' * 70}{C_RESET}\n")


def print_help(mode: str):
    print(f"\n{C_BOLD}[INFO] Befehlsübersicht ({mode.upper()}-Modus):{C_RESET}")
    print("  /prompt [list|set|show|reset] - Kognitive Profile verwalten")
    if mode == "local":
        print("  /graph list                   - Zeigt alle Topologien im Vault")
        print("  /graph load <Name>            - Wechselt die aktive Topologie")
        print("  /graph info                   - Status und Knotenverteilung")
    else:
        print("  /switch <Name>                - Wechselt Topologie auf Remote-Daemon")
    print("  /save [Name]                  - Speichert Session (Markdown + JSON)")
    print("  /load [Name]                  - Lädt oder listet gespeicherte Sessions")
    print("  /context                      - Zeigt Token-Auslastung")
    print("  /clear                        - Leert den Verlauf")
    print("  exit                          - Beendet die Session\n")


# ==============================================================================
# RUNNER MODI
# ==============================================================================
def run_local():
    vault_io = VaultIO()
    graph_store = GraphStore(vault_io=vault_io)
    session = SessionManager(vault_io=vault_io)
    engine = ExecutionEngine(graph_store=graph_store, session_manager=session)

    stats = graph_store.get_graph_stats()
    print_banner("local", f"Vault: {vault_io.vault_path.name} ({stats['name']})", engine.model_name)

    p_session = None
    if HAS_PROMPT_TOOLKIT:
        kb = KeyBindings()
        @kb.add("enter")
        def _(event):
            event.current_buffer.validate_and_handle()
        p_session = PromptSession(key_bindings=kb, multiline=False)

    while True:
        try:
            user_input = p_session.prompt("\nGeorg > ").strip() if p_session else input("\nGeorg > ").strip()
            if not user_input:
                continue

            # 1. Befehle abfangen
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{C_GRAY}[*] Exocortex beendet.{C_RESET}")
                break
            elif user_input == "/help":
                print_help("local")
                continue
            elif user_input.startswith("/prompt"):
                handle_prompt_command(user_input, engine.prompt_manager)
                continue
            elif user_input == "/clear":
                session.clear()
                print(f"{C_GREEN}[OK] Verlauf geleert.{C_RESET}\n")
                continue
            elif user_input == "/context":
                usage = session.get_token_usage()
                print(f"{C_CYAN}[CONTEXT]{C_RESET} {usage['estimated_tokens']} Tokens über {usage['message_count']} Nachrichten.\n")
                continue
            elif user_input.startswith("/save"):
                name = user_input.split()[1] if len(user_input.split()) > 1 else None
                paths = session.save_session(name)
                print(f"{C_GREEN}[OK] Gespeichert in Vault:\n  ↳ {paths['markdown']}\n  ↳ {paths['json']}{C_RESET}\n")
                continue
            elif user_input.startswith("/load"):
                parts = user_input.split()
                if len(parts) > 1:
                    name = parts[1]
                    try:
                        session.load_session(name)
                        print(f"{C_GREEN}[OK] Session '{name}' geladen ({len(session.messages)} Nachrichten).{C_RESET}\n")
                    except Exception as e:
                        print(f"{C_RED}[ERROR] Fehler beim Laden der Session: {e}{C_RESET}\n")
                else:
                    saved = list_available_sessions(vault_io)
                    if saved:
                        print(f"{C_CYAN}[SESSIONS]{C_RESET} Verfügbare Sessions: " + ", ".join(f"'{s}'" for s in saved) + "\n")
                    else:
                        print(f"{C_YELLOW}[INFO] Keine gespeicherten Sessions im Vault gefunden.{C_RESET}\n")
                continue
            elif user_input.startswith("/graph"):
                parts = user_input.split()
                sub = parts[1].lower() if len(parts) > 1 else "info"
                if sub == "list":
                    print(f"{C_CYAN}[TOPOLOGIEN]{C_RESET} " + ", ".join(f"'{g}'" for g in vault_io.list_graphs()) + "\n")
                elif sub == "load" and len(parts) > 2:
                    st = graph_store.load_graph(parts[2])
                    session.active_graph = st["name"]
                    print(f"{C_GREEN}[OK] Topologie gewechselt: '{st['name']}' ({st['node_count']} Knoten){C_RESET}\n")
                elif sub == "info":
                    st = graph_store.get_graph_stats()
                    print(f"{C_CYAN}[GRAPH]{C_RESET} '{st['name']}' | {st['node_count']} Knoten | {st['edge_count']} Kanten\n")
                continue

            # 2. ReAct-Turn ausführen
            for event in engine.execute_turn(user_input):
                ev = event.get("event")
                if ev == "tool_call":
                    args = json.dumps(event.get("args", {}), ensure_ascii=False)
                    print(f"\n{C_YELLOW}⚡ [TOOL CALL]{C_RESET} {event['name']}({args})")
                elif ev == "tool_result":
                    print(f"{C_CYAN}↳ [RESULT]{C_RESET} {event['result']}")
                elif ev == "completed":
                    print(f"\n{C_BOLD}Exocortex >{C_RESET} {event['final_text']}\n")

        except KeyboardInterrupt:
            continue
        except EOFError:
            break


async def run_remote(sse_url: str):
    vault_io = VaultIO()
    session = SessionManager(vault_io=vault_io)
    prompt_mgr = PromptManager()
    remote_engine = RemoteMCPEngine(sse_url, session, prompt_manager=prompt_mgr)

    print(f"[*] Verbinde mit Remote Daemon auf {sse_url}...")
    try:
        async with sse_client(sse_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()
                await remote_engine.initialize(mcp_session)

                print_banner("remote", sse_url, remote_engine.model_name)

                p_session = None
                if HAS_PROMPT_TOOLKIT:
                    kb = KeyBindings()
                    @kb.add("enter")
                    def _(event):
                        event.current_buffer.validate_and_handle()
                    p_session = PromptSession(key_bindings=kb, multiline=False)

                while True:
                    try:
                        if p_session:
                            user_input = (await p_session.prompt_async("\nGeorg [Remote] > ")).strip()
                        else:
                            user_input = (await asyncio.to_thread(input, "\nGeorg [Remote] > ")).strip()

                        if not user_input:
                            continue

                        # 1. Befehle abfangen
                        if user_input.lower() in ["exit", "quit"]:
                            print(f"\n{C_GRAY}[*] Remote-Verbindung getrennt. Exocortex beendet.{C_RESET}")
                            break
                        elif user_input == "/help":
                            print_help("remote")
                            continue
                        elif user_input.startswith("/prompt"):
                            handle_prompt_command(user_input, remote_engine.prompt_manager)
                            continue
                        elif user_input == "/clear":
                            session.clear()
                            print(f"{C_GREEN}[OK] Verlauf geleert.{C_RESET}\n")
                            continue
                        elif user_input == "/context":
                            usage = session.get_token_usage()
                            print(f"{C_CYAN}[CONTEXT]{C_RESET} {usage['estimated_tokens']} Tokens über {usage['message_count']} Nachrichten.\n")
                            continue
                        elif user_input.startswith("/save"):
                            name = user_input.split()[1] if len(user_input.split()) > 1 else None
                            paths = session.save_session(name)
                            print(f"{C_GREEN}[OK] Gespeichert in Vault:\n  ↳ {paths['markdown']}\n  ↳ {paths['json']}{C_RESET}\n")
                            continue
                        elif user_input.startswith("/load"):
                            parts = user_input.split()
                            if len(parts) > 1:
                                name = parts[1]
                                try:
                                    session.load_session(name)
                                    print(f"{C_GREEN}[OK] Session '{name}' geladen ({len(session.messages)} Nachrichten).{C_RESET}\n")
                                except Exception as e:
                                    print(f"{C_RED}[ERROR] Fehler beim Laden der Session: {e}{C_RESET}\n")
                            else:
                                saved = list_available_sessions(vault_io)
                                if saved:
                                    print(f"{C_CYAN}[SESSIONS]{C_RESET} Verfügbare Sessions: " + ", ".join(f"'{s}'" for s in saved) + "\n")
                                else:
                                    print(f"{C_YELLOW}[INFO] Keine gespeicherten Sessions im Vault gefunden.{C_RESET}\n")
                            continue
                        elif user_input.startswith(("/switch", "/graph")) and len(user_input.split()) > 1:
                            parts = user_input.split()
                            topo = parts[2] if parts[0] == "/graph" and len(parts) > 2 else parts[1]
                            try:
                                res = await mcp_session.call_tool("exocortex_switch_topology", arguments={"topology_name": topo})
                                print(f"{C_GREEN}[OK] {res.content[0].text}{C_RESET}\n")
                            except Exception as e:
                                print(f"{C_RED}[ERROR] Topologie-Wechsel fehlgeschlagen: {e}{C_RESET}\n")
                            continue

                        # 2. Remote Turn über asynchronen Generator
                        async for event in remote_engine.execute_turn(user_input, mcp_session):
                            ev = event.get("event")
                            if ev == "tool_call":
                                args = json.dumps(event.get("args", {}), ensure_ascii=False)
                                print(f"\n{C_YELLOW}⚡ [REMOTE TOOL]{C_RESET} {event['name']}({args})")
                            elif ev == "tool_result":
                                print(f"{C_CYAN}↳ [RESULT]{C_RESET} {event['result']}")
                            elif ev == "completed":
                                print(f"\n{C_BOLD}Exocortex >{C_RESET} {event['final_text']}\n")

                    except (KeyboardInterrupt, asyncio.CancelledError):
                        continue
                    except EOFError:
                        break
    except Exception as e:
        print(f"{C_RED}[!] Fehler im Remote-Turn:{C_RESET}")
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Exocortex Terminal Runner (v1.4.0)")
    parser.add_argument(
        "--remote",
        nargs="?",
        const=f"http://{settings.mcp_host}:{settings.mcp_port}/sse",
        default=None,
        help=f"Verbindet mit Remote-MCP-Daemon (Standard: http://{settings.mcp_host}:{settings.mcp_port}/sse)",
    )
    args = parser.parse_args()

    if args.remote:
        asyncio.run(run_remote(args.remote))
    else:
        run_local()


if __name__ == "__main__":
    main()
