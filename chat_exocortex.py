#!/usr/bin/env python3
"""
chat_exocortex.py (v1.4.4)
Universal terminal runner with dual-mode support:
  1. Embedded Mode (Local via direct class instances)
  2. Remote Mode   (Network via FastMCP / SSE client)
"""

import traceback
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

# Fallback for prompt_toolkit
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

import ollama

# Configuration & Cognition
from core.config import settings
from core.prompts import PromptManager
from core.session import SessionManager
from core.engine import ExecutionEngine
from core.guards import slice_for_embedding, prune_history_if_needed

# Local Substrates
from server.vault_io import VaultIO
from server.graph_store import GraphStore

# MCP Client Imports for Remote Mode
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# ANSI Color Codes
C_CYAN = "\033[1;36m"
C_YELLOW = "\033[1;33m"
C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_GRAY = "\033[90m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"


# ==============================================================================
# PROMPT COMMAND HANDLER (FOR BOTH MODES)
# ==============================================================================
def handle_prompt_command(user_input: str, prompt_manager: PromptManager):
    """Central handler for /prompt subcommands."""
    parts = user_input.split()
    sub = parts[1].lower() if len(parts) > 1 else "list"

    if sub == "list":
        profiles = prompt_manager.list_profiles()
        active = prompt_manager.active_profile
        print(f"\n{C_CYAN}[PROMPTS]{C_RESET} Cognitive Lenses / Profiles:")
        for p in profiles:
            mark = f" {C_GREEN}(active){C_RESET}" if p == active else ""
            print(f"  • {p}{mark}")
        print()
    elif sub == "set" and len(parts) > 2:
        target = parts[2]
        if prompt_manager.set_profile(target):
            print(f"{C_GREEN}[OK] Cognitive profile switched to: '{target}'{C_RESET}\n")
        else:
            print(f"{C_RED}[ERROR] Profile '{target}' not found.{C_RESET}\n")
    elif sub == "show":
        print(f"\n{C_CYAN}{'=' * 60}{C_RESET}")
        print(f"{C_BOLD}[ACTIVE BASE SYSTEM PROMPT ({prompt_manager.active_profile})]{C_RESET}")
        print(f"{C_CYAN}{'=' * 60}{C_RESET}")
        print(prompt_manager.get_base_prompt())
        print(f"{C_CYAN}{'=' * 60}{C_RESET}\n")
    elif sub == "reset":
        prompt_manager.reset()
        print(f"{C_GREEN}[OK] Prompt reset to default profile ('default').{C_RESET}\n")
    else:
        print(f"{C_YELLOW}[INFO] Usage: /prompt [list | set <profile> | show | reset]{C_RESET}\n")


def list_available_sessions(vault_io: VaultIO) -> List[str]:
    """Reads all persisted sessions from the vault's Sessions directory."""
    sessions_dir = vault_io.vault_path / "Sessions"
    if not sessions_dir.exists():
        return []
    # Collect JSON files without extension
    return sorted([f.stem for f in sessions_dir.glob("*.json")])


# ==============================================================================
# REMOTE MCP ADAPTER (FOR --remote)
# ==============================================================================
class RemoteMCPEngine:
    """Orchestrates cognition via a remote FastMCP daemon over SSE."""

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
        # 1. Gauge resonance via remote daemon
        safe_query = slice_for_embedding(user_input)
        try:
            gauge_res = await mcp_session.call_tool("exocortex_gauge_field", arguments={"query_vector": safe_query, "top_k": 4})
            field_xml = gauge_res.content[0].text if gauge_res.content else "<active_phase_space status='quiescent' />"
        except Exception:
            field_xml = "<active_phase_space status='quiescent' />"

        yield {"event": "field_context", "xml": field_xml}

        # 2. Dynamically retrieve system prompt from PromptManager
        base_prompt = self.prompt_manager.get_base_prompt()
        full_system_prompt = f"{base_prompt}\n\n### Active Phase Space (Remote):\n{field_xml}"

        # 3. Update session
        self.session.add_user_message(user_input)
        history = prune_history_if_needed(self.session.messages)
        messages_payload = [{"role": "system", "content": full_system_prompt}] + history

        turn_count = 0
        while turn_count < max_turns:
            turn_count += 1

            # Non-blocking chat call via thread
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

                    # Remote tool execution via FastMCP
                    try:
                        res = await mcp_session.call_tool(fn_name, arguments=fn_args)
                        tool_result = res.content[0].text if res.content else ""
                    except Exception as e:
                        tool_result = f"<error>Remote tool error: {e}</error>"

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
    print(f"{C_BOLD}[*] EXOCORTEX ONLINE v1.4.4 (Dual-Mode Runner){C_RESET}")
    print(f"[*] Mode: {C_GREEN}{mode.upper()}{C_RESET} | Target: {C_YELLOW}{target}{C_RESET} | Model: {C_CYAN}{model}{C_RESET}")
    print(f"[*] Send: [Enter] | Line break: [Alt+Enter] | Quit: 'exit'")
    print(f"[*] Commands: /save | /load | /prompt | /context | /clear | /help" + (" | /graph" if mode == "local" else " | /switch <Topology>"))
    print(f"{C_CYAN}{'=' * 70}{C_RESET}\n")


def print_help(mode: str = "local"):
    print(f"\n{C_BOLD}[INFO] Command Overview ({mode.upper()} Mode):{C_RESET}")
    print("  /prompt [list|set|show|reset] - Manage cognitive profiles")
    
    if mode.lower() == "local":
        print("  /graph                        - Display active topology status & node metrics")
        print("  /graph <Name>                 - Switch active topology (e.g. /graph code_architect)")
        print("  /freeze [Tag]                 - Freeze topology state (JSON snapshot + Canvas)")
    else:
        print("  /switch <Name>                - Switch topology on remote daemon (e.g. /switch code_architect)")
        print("  /freeze [Tag]                 - Freeze topology state on remote daemon")
        
    print("  /save [Name]                  - Save session transcript (Markdown + JSON)")
    print("  /load                         - List all saved sessions in vault")
    print("  /load <Name>                  - Load saved session transcript")
    print("  /context                      - Display active token usage")
    print("  /clear                        - Clear message history")
    print("  exit / quit                   - Terminate session\n")

# ==============================================================================
# RUNNER MODES
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
            user_input = p_session.prompt("\nOperator > ").strip() if p_session else input("\nOperator > ").strip()
            if not user_input:
                continue

            # 1. Command interception
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{C_GRAY}[*] Exocortex session terminated.{C_RESET}")
                break
            elif user_input == "/help":
                print_help("local")
                continue
            elif user_input.startswith("/prompt"):
                handle_prompt_command(user_input, engine.prompt_manager)
                continue
            elif user_input == "/clear":
                session.clear()
                print(f"{C_GREEN}[OK] Message history cleared.{C_RESET}\n")
                continue
            elif user_input == "/context":
                usage = session.get_token_usage()
                print(f"{C_CYAN}[CONTEXT]{C_RESET} {usage['estimated_tokens']} tokens across {usage['message_count']} messages.\n")
                continue
            elif user_input.startswith("/save"):
                name = user_input.split()[1] if len(user_input.split()) > 1 else None
                paths = session.save_session(name)
                print(f"{C_GREEN}[OK] Saved to vault:\n  ↳ {paths['markdown']}\n  ↳ {paths['json']}{C_RESET}\n")
                continue
            elif user_input.startswith("/load"):
                parts = user_input.split()
                if len(parts) > 1:
                    name = parts[1]
                    try:
                        session.load_session(name)
                        print(f"{C_GREEN}[OK] Session '{name}' loaded ({len(session.messages)} messages).{C_RESET}\n")
                    except Exception as e:
                        print(f"{C_RED}[ERROR] Failed to load session: {e}{C_RESET}\n")
                else:
                    saved = list_available_sessions(vault_io)
                    if saved:
                        print(f"{C_CYAN}[SESSIONS]{C_RESET} Available sessions: " + ", ".join(f"'{s}'" for s in saved) + "\n")
                    else:
                        print(f"{C_YELLOW}[INFO] No saved sessions found in vault.{C_RESET}\n")
                continue
            elif user_input.startswith("/graph") or user_input.startswith("/switch"):
                parts = user_input.strip().split(maxsplit=1)
                if len(parts) > 1:
                    target_graph = parts[1].strip()
                    try:
                        stats = engine.switch_graph(target_graph)
                        print(f"\n[*] Switched to graph '{stats['name']}' ({stats['node_count']} nodes, {stats['edge_count']} edges)")
                        print(f"[*] Canvas synced to 'Exocortex_Interactive.canvas'\n")
                    except Exception as e:
                        print(f"\n[!] Failed to switch graph: {e}\n")
                else:
                    stats = engine.get_graph_stats()
                    print(f"\n[GRAPH] '{stats['name']}' | {stats['node_count']} nodes | {stats['edge_count']} edges\n")
                continue
            elif user_input.startswith("/freeze"):
                parts = user_input.strip().split(maxsplit=1)
                tag = parts[1].strip() if len(parts) > 1 else None
                try:
                    res = graph_store.freeze_snapshot(tag)
                    print(f"\n{C_GREEN}[OK] Phase-space topology frozen:{C_RESET}")
                    print(f"  ↳ Snapshot: {res['snapshot_name']}")
                    print(f"  ↳ JSON:     {res['json_path']}")
                    print(f"  ↳ Canvas:   {res['canvas_path']}\n")
                except Exception as e:
                    print(f"\n{C_RED}[!] Failed to freeze snapshot: {e}{C_RESET}\n")
                continue

            # 2. Execute ReAct turn
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

    print(f"[*] Connecting to remote daemon at {sse_url}...")
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
                            user_input = (await p_session.prompt_async("\nOperator [Remote] > ")).strip()
                        else:
                            user_input = (await asyncio.to_thread(input, "\nOperator [Remote] > ")).strip()

                        if not user_input:
                            continue

                        # 1. Command interception
                        if user_input.lower() in ["exit", "quit"]:
                            print(f"\n{C_GRAY}[*] Remote connection closed. Exocortex terminated.{C_RESET}")
                            break
                        elif user_input == "/help":
                            print_help("remote")
                            continue
                        elif user_input.startswith("/prompt"):
                            handle_prompt_command(user_input, remote_engine.prompt_manager)
                            continue
                        elif user_input == "/clear":
                            session.clear()
                            print(f"{C_GREEN}[OK] Message history cleared.{C_RESET}\n")
                            continue
                        elif user_input == "/context":
                            usage = session.get_token_usage()
                            print(f"{C_CYAN}[CONTEXT]{C_RESET} {usage['estimated_tokens']} tokens across {usage['message_count']} messages.\n")
                            continue
                        elif user_input.startswith("/save"):
                            name = user_input.split()[1] if len(user_input.split()) > 1 else None
                            paths = session.save_session(name)
                            print(f"{C_GREEN}[OK] Saved to vault:\n  ↳ {paths['markdown']}\n  ↳ {paths['json']}{C_RESET}\n")
                            continue
                        elif user_input.startswith("/load"):
                            parts = user_input.split()
                            if len(parts) > 1:
                                name = parts[1]
                                try:
                                    session.load_session(name)
                                    print(f"{C_GREEN}[OK] Session '{name}' loaded ({len(session.messages)} messages).{C_RESET}\n")
                                except Exception as e:
                                    print(f"{C_RED}[ERROR] Failed to load session: {e}{C_RESET}\n")
                            else:
                                saved = list_available_sessions(vault_io)
                                if saved:
                                    print(f"{C_CYAN}[SESSIONS]{C_RESET} Available sessions: " + ", ".join(f"'{s}'" for s in saved) + "\n")
                                else:
                                    print(f"{C_YELLOW}[INFO] No saved sessions found in vault.{C_RESET}\n")
                            continue
                        elif user_input.startswith("/graph") or user_input.startswith("/switch"):
                            parts = user_input.strip().split(maxsplit=1)
                            if len(parts) > 1:
                                target_graph = parts[1].strip()
                                try:
                                    # Remote-Aufruf an das MCP-Tool auf dem Server
                                    res = await mcp_session.call_tool(
                                        "exocortex_switch_topology",
                                        arguments={"topology_name": target_graph}
                                    )
                                    raw_text = res.content[0].text if res.content else "{}"
                                    print(f"\n[*] Remote Topology: {raw_text}")
                                    print(f"[*] Server-Canvas synced to 'Exocortex_Interactive.canvas'\n")
                                except Exception as e:
                                    print(f"\n[!] Failed to switch graph on remote daemon: {e}\n")
                            else:
                                print(f"\n[!] Please specify a topology name: /switch <name>\n")
                            continue
                        elif user_input.startswith("/freeze"):
                            parts = user_input.strip().split(maxsplit=1)
                            tag = parts[1].strip() if len(parts) > 1 else None
                            try:
                                call_args = {"tag": tag} if tag else {}
                                result = await mcp_session.call_tool("exocortex_freeze_snapshot", arguments=call_args)
                                raw_payload = result.content[0].text if result.content else ""

                                # Robuster Parser: Prüfen, ob JSON oder XML/Text zurückkommt
                                try:
                                    payload = json.loads(raw_payload)
                                    if payload.get("status") == "success":
                                        print(f"\n{C_GREEN}[OK] Remote phase-space topology frozen:{C_RESET}")
                                        print(f"  ↳ Snapshot: {payload.get('snapshot_name')}")
                                        print(f"  ↳ JSON:     {payload.get('json_path')}")
                                        print(f"  ↳ Canvas:   {payload.get('canvas_path')}\n")
                                    else:
                                        print(f"\n{C_RED}[!] Remote freeze failed: {payload.get('message')}{C_RESET}\n")
                                except (json.JSONDecodeError, TypeError):
                                    # Direkte Ausgabe, falls der Server XML/Text liefert
                                    print(f"\n{C_GREEN}[OK] Remote phase-space response:{C_RESET}\n  ↳ {raw_payload}\n")
                            except Exception as e:
                                print(f"\n{C_RED}[!] Remote freeze RPC error: {e}{C_RESET}\n")
                            continue
                            
                        # 2. Execute remote turn
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
        print(f"{C_RED}[!] Error in remote turn:{C_RESET}")
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Exocortex Terminal Runner (v1.4.2)")
    parser.add_argument(
        "--remote",
        nargs="?",
        const=f"http://{settings.mcp_host}:{settings.mcp_port}/sse",
        default=None,
        help=f"Connect to remote MCP daemon (default: http://{settings.mcp_host}:{settings.mcp_port}/sse)",
    )
    args = parser.parse_args()

    if args.remote:
        asyncio.run(run_remote(args.remote))
    else:
        run_local()


if __name__ == "__main__":
    main()
