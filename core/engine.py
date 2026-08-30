"""
core/engine.py
ExecutionEngine: ReAct loop, decoupled tool dispatching, and dynamic context assembly.
"""

from typing import Any, Callable, Dict, Generator, List, Optional
from pathlib import Path
import datetime
import ollama

from core.config import settings
from core.prompts import PromptManager
from server.graph_store import GraphStore, cosine_similarity
from .guards import prune_history_if_needed, slice_for_embedding
from .session import SessionManager


class ExecutionEngine:
    def __init__(
        self,
        graph_store: GraphStore,
        session_manager: SessionManager,
        model_name: Optional[str] = None,
        num_ctx: Optional[int] = None,
        ollama_host: Optional[str] = None,
        config_dir: Optional[Path] = None,
    ):
        self.graph_store = graph_store
        self.session = session_manager
        self.model_name = model_name or settings.chat_model
        self.num_ctx = num_ctx or settings.context_window
        self.client = ollama.Client(host=ollama_host or settings.ollama_host)
        self.config_dir = config_dir or (settings.project_root / "config")
        self.prompt_manager = PromptManager(config_dir=self.config_dir)

        # Tool registry (decoupled dispatching)
        self.tools_schema = self._build_tools_schema()
        self.tool_handlers: Dict[str, Callable[..., Any]] = {
            "read_vault_note": self._tool_read_vault_note,
            "append_scratchpad": self._tool_append_scratchpad,
            "exocortex_query_graph": self._tool_query_graph,
            "exocortex_create_node": self._tool_create_node,
            "exocortex_mutate_node": self._handle_mutate_node,
            "exocortex_temporal_anchor": self._tool_temporal_anchor,
        }
        
    def freeze_snapshot(self, tag: Optional[str] = None) -> Dict[str, str]:
        """Exposes snapshot freezing from GraphStore."""
        return self.graph_store.freeze_snapshot(tag)

    def switch_graph(self, graph_name: str) -> Dict[str, Any]:
        """Switches the active knowledge graph topology."""
        return self.graph_store.switch_graph(graph_name)

    def get_graph_stats(self) -> Dict[str, Any]:
        """Returns stats of the currently active graph topology."""
        return self.graph_store.get_graph_stats()

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_vault_note",
                    "description": "Reads a Markdown note from the Obsidian vault.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_name": {
                                "type": "string",
                                "description": "Relative path or filename (e.g., 'Sessions/notes.md')",
                            }
                        },
                        "required": ["note_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "append_scratchpad",
                    "description": "Appends text content to a scratchpad note in the vault.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Text content to append."},
                            "filename": {
                                "type": "string",
                                "description": "Target filename (default: Active_Scratchpad.md)",
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_query_graph",
                    "description": "Queries relevant context nodes and graph connections within the active topology.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Semantic query string."},
                            "top_k": {"type": "integer", "description": "Maximum number of nodes (default: 3)"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_create_node",
                    "description": "Creates and links a new node in the active knowledge graph.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_type": {
                                "type": "string",
                                "enum": ["Constraint", "Concept", "Rule", "State"],
                                "description": "Constraint (guardrail), Concept (foundation), Rule (action), State (working context)",
                            },
                            "label": {"type": "string", "description": "Compact identifier or title."},
                            "content_payload": {"type": "string", "description": "Content, principle, or operational rule."},
                            "links": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of target node IDs to link to (e.g., ['CNC_001', 'RUL_002'])",
                            },
                        },
                        "required": ["node_type", "label", "content_payload"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_temporal_anchor",
                    "description": "Returns the current system timestamp, ISO 8601 string, and calendar week.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {"type": "string", "enum": ["full", "iso", "time_only"]}
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_mutate_node",
                    "description": "Modulates weight, updates payload, or prunes an existing node in the active graph.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_node_id": {
                                "type": "string",
                                "description": "Unique identifier of the target node (e.g. 'CNC_001', 'CST_001')"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["STRENGTHEN", "DECAY", "SET_WEIGHT", "PRUNE", "UPDATE"],
                                "description": "STRENGTHEN (+delta), DECAY (-delta), SET_WEIGHT (set weight via delta), PRUNE (remove node), UPDATE (modify payload)"
                            },
                            "payload_update": {
                                "type": "string",
                                "description": "New payload text (mandatory if action is UPDATE)"
                            },
                            "delta": {
                                "type": "number",
                                "description": "Weight modification delta for STRENGTHEN or DECAY (default: 0.2)"
                            }
                        },
                        "required": ["target_node_id", "action"]
                    }
                }
            }
        ]

    # --- Tool Implementations ---
    def _tool_read_vault_note(self, note_name: str) -> str:
        try:
            content = self.graph_store.vault_io.read_note(note_name)
            return f"<vault_note path='{note_name}'>\n{content}\n</vault_note>"
        except Exception as e:
            return f"<error>Error reading note '{note_name}': {e}</error>"

    def _tool_append_scratchpad(self, content: str, filename: str = "Active_Scratchpad.md") -> str:
        try:
            path = self.graph_store.vault_io.append_scratchpad(content, filename)
            return f"<scratchpad status='appended' path='{path}' />"
        except Exception as e:
            return f"<error>Error writing to scratchpad: {e}</error>"

    def _tool_query_graph(self, query: str, top_k: int = 3) -> str:
        try:
            res = self.graph_store.get_resonant_nodes(query, top_k=top_k)
            if not res:
                return "<graph_query status='empty' />"
            lines = [f"<graph_query query='{query}'>"]
            for nid, attrs, sim in res:
                lines.append(f"  <node id='{nid}' label='{attrs.get('label')}' type='{attrs.get('type')}' similarity='{sim:.2f}' />")
            lines.append("</graph_query>")
            return "\n".join(lines)
        except Exception as e:
            return f"<error>Graph query failed: {e}</error>"

    def _tool_create_node(
        self, 
        node_type: str, 
        label: str, 
        content_payload: str, 
        links: Optional[Any] = None,
    ) -> str:
        try:
            target_links = links if isinstance(links, list) else []
            if isinstance(links, str):
                target_links = [t.strip() for t in links.split(",") if t.strip()]

            res = self.graph_store.imprint_node(
                node_type=node_type,
                label=label,
                content_payload=content_payload,
                links=target_links
            )
            stats = self.graph_store.get_graph_stats()
            conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "None"

            return (
                f"<create_result status='materialized' node_id='{res['node_id']}' label='{label}'>\n"
                f"  <topology name='{stats['name']}' total_nodes='{stats['node_count']}' total_edges='{stats['edge_count']}' />\n"
                f"  <connected_to>{conns}</connected_to>\n"
                f"</create_result>"
            )
        except Exception as e:
            return f"<error>Node creation failed: {e}</error>"

    def _tool_temporal_anchor(self, scope: str = "full") -> str:
        now = datetime.datetime.now()
        iso = now.isoformat()
        human = now.strftime("%d.%m.%Y, %H:%M:%S")
        kw = now.isocalendar()[1]
        return (
            f"<temporal_anchor>\n"
            f"  <human_readable>{human}</human_readable>\n"
            f"  <iso8601>{iso}</iso8601>\n"
            f"  <calendar_context>Week {kw}, Year {now.year}</calendar_context>\n"
            f"</temporal_anchor>"
        )

    def _handle_mutate_node(
        self,
        target_node_id: str,
        action: str,
        payload_update: Optional[str] = None,
        delta: float = 0.2
    ) -> str:
        if not self.graph_store:
            return "<error>GraphStore is not initialized in engine.</error>"

        try:
            if isinstance(delta, str):
                try:
                    delta = float(delta)
                except ValueError:
                    delta = 0.2

            res = self.graph_store.mutate_node(
                target_node_id=target_node_id,
                action=action,
                payload_update=payload_update,
                delta=delta
            )

            if res.get("status") == "error":
                return f"<graph_mutation status='error' message='{res.get('message')}' />"

            stats = self.graph_store.get_graph_stats()
            delta_info = f" new_weight='{res.get('new_weight')}'" if "new_weight" in res else ""
            pruned_info = " pruned='true'" if action.upper() == "PRUNE" else ""

            return (
                f"<graph_mutation status='success' node_id='{target_node_id}' action='{action.upper()}'{delta_info}{pruned_info}>\n"
                f"  <topology name='{stats['name']}' total_nodes='{stats['node_count']}' total_edges='{stats['edge_count']}' />\n"
                f"</graph_mutation>"
            )
        except Exception as e:
            return f"<error>Graph mutation failed: {e}</error>"

    # --- ReAct Execution Loop (Streaming Enabled) ---
    def execute_turn(self, user_input: str, max_turns: int = 5) -> Generator[Dict[str, Any], None, None]:
        """
        Executes a full cognitive turn including the ReAct tool loop with live streaming.
        """
        try:
            # 1. Extract static Constraints (inviolable frame)
            constraints_xml = self.graph_store.assemble_constraints_frame()

            # 2. Extract dynamic context subgraph
            safe_query = slice_for_embedding(user_input)
            context_xml = self.graph_store.assemble_context_frame(safe_query)
            
            # Events für UI / CLI (neue und legacy Namen bereitstellen)
            yield {"event": "constraints_frame", "xml": constraints_xml}
            yield {"event": "context_frame", "xml": context_xml}

            # 3. Dynamically assemble system prompt
            full_system_prompt = self.prompt_manager.build_system_prompt(
                context_xml=context_xml,
                constraints_xml=constraints_xml
            )

            # 4. Update session with new user input
            self.session.add_user_message(user_input)
            self.session.active_graph = self.graph_store.active_graph_name

            # 5. Prepare message history for Ollama
            history = prune_history_if_needed(self.session.messages)
            messages_payload = [{"role": "system", "content": full_system_prompt}] + history

            turn_count = 0
            final_response_text = ""

            while turn_count < max_turns:
                turn_count += 1
                accumulated_content = ""
                accumulated_tool_calls = []

                try:
                    stream = self.client.chat(
                        model=self.model_name,
                        messages=messages_payload,
                        tools=self.tools_schema,
                        options={"num_ctx": self.num_ctx},
                        stream=True,
                    )

                    for chunk in stream:
                        msg = chunk.get("message", {}) if isinstance(chunk, dict) else getattr(chunk, "message", {})
                        content_delta = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""
                        chunk_tool_calls = (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", [])) or []

                        if chunk_tool_calls:
                            accumulated_tool_calls.extend(chunk_tool_calls)

                        if content_delta:
                            accumulated_content += content_delta
                            if not chunk_tool_calls:
                                yield {"event": "token", "delta": content_delta}

                except Exception as api_err:
                    err_msg = f"Inference engine failure: {api_err}"
                    yield {"event": "error", "message": err_msg}
                    self.session.add_assistant_message(f"### [System Error]\n{err_msg}")
                    return

                # Tool calls detected?
                if accumulated_tool_calls:
                    messages_payload.append({
                        "role": "assistant",
                        "content": accumulated_content,
                        "tool_calls": accumulated_tool_calls,
                    })
                    self.session.add_assistant_message(accumulated_content, tool_calls=accumulated_tool_calls)

                    for call in accumulated_tool_calls:
                        fn = call.get("function", {}) if isinstance(call, dict) else getattr(call, "function", {})
                        fn_name = fn.get("name", "") if isinstance(fn, dict) else getattr(fn, "name", "")
                        fn_args = fn.get("arguments", {}) if isinstance(fn, dict) else getattr(fn, "arguments", {})

                        if isinstance(fn_args, str):
                            try:
                                import json
                                fn_args = json.loads(fn_args)
                            except Exception:
                                pass

                        yield {"event": "tool_call", "name": fn_name, "args": fn_args}

                        handler = self.tool_handlers.get(fn_name)
                        if handler:
                            try:
                                tool_result = str(handler(**fn_args))
                            except Exception as exec_err:
                                tool_result = f"<error>Tool execution failed for '{fn_name}': {exec_err}</error>"
                        else:
                            tool_result = f"<error>Unknown tool '{fn_name}'</error>"

                        yield {"event": "tool_result", "result": tool_result}
                        messages_payload.append({"role": "tool", "content": tool_result})
                        self.session.add_tool_response(tool_result)

                else:
                    final_response_text = accumulated_content
                    
                    # Telemetrie
                    telemetry = {"echo": 0.0, "delta_e": None, "attractor": None}
                    try:
                        if final_response_text.strip():
                            p_vec = self.graph_store._get_embedding(safe_query)
                            r_vec = self.graph_store._get_embedding(slice_for_embedding(final_response_text))
                            telemetry["echo"] = round(cosine_similarity(p_vec, r_vec), 2)
                            
                            resonant = self.graph_store.get_resonant_nodes(safe_query, top_k=3)
                            if resonant:
                                best_nid, best_attrs, _ = resonant[0]
                                w_vec = best_attrs.get("embedding", [])
                                if w_vec:
                                    sim_p_w = cosine_similarity(p_vec, w_vec)
                                    sim_r_w = cosine_similarity(r_vec, w_vec)
                                    telemetry["delta_e"] = round(sim_r_w - sim_p_w, 2)
                                    telemetry["attractor"] = best_attrs.get("label", best_nid)
                    except Exception:
                        pass

                    yield {
                        "event": "completed", 
                        "final_text": final_response_text,
                        "telemetry": telemetry
                    }
                    self.session.add_assistant_message(final_response_text)
                    break

            if not final_response_text and turn_count >= max_turns:
                fallback_msg = "Budget exhausted: Maximum tool execution turns reached."
                yield {"event": "completed", "final_text": fallback_msg}
                self.session.add_assistant_message(fallback_msg)

        except Exception as general_err:
            fatal_msg = f"Fatal execution loop exception: {general_err}"
            yield {"event": "error", "message": fatal_msg}
