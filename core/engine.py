"""
core/engine.py
ExecutionEngine: ReAct loop, tool dispatching, and dynamic context assembly.
"""

from typing import Any, Callable, Dict, Generator, List, Optional
from pathlib import Path
import json
import datetime
import ollama

from core.config import settings
from core.prompts import PromptManager
from server.graph_store import GraphStore
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
        self.config_dir = config_dir or (Path(__file__).parent.parent / "config")
        self.prompt_manager = PromptManager()

        # Tool registry (decoupled dispatching)
        self.tools_schema = self._build_tools_schema()
        self.tool_handlers: Dict[str, Callable[..., Any]] = {
            "read_vault_note": self._tool_read_vault_note,
            "append_scratchpad": self._tool_append_scratchpad,
            "exocortex_gauge_field": self._tool_gauge_field,
            "exocortex_imprint_field": self._tool_imprint_field,
            "exocortex_temporal_anchor": self._tool_temporal_anchor,
            "exocortex_mutate_phase_space": self._handle_mutate_phase_space
        }

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
                                "description": "Relative path or filename (e.g., 'Sessions/systemic.md')",
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
                    "name": "exocortex_gauge_field",
                    "description": "Gauges resonant nodes within the active phase space for a given query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_vector": {"type": "string", "description": "Semantic query string."},
                            "top_k": {"type": "integer", "description": "Maximum number of nodes (default: 3)"},
                        },
                        "required": ["query_vector"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_imprint_field",
                    "description": "Creates and wires a new node into the active phase space topology.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_type": {
                                "type": "string",
                                "enum": ["BoundaryConstraint", "TrajectoryOperator", "PotentialWell", "PhaseSpaceTrace"],
                            },
                            "label": {"type": "string", "description": "Compact identifier or label."},
                            "content_payload": {"type": "string", "description": "Axiom, constraint, or synthesis."},
                            "tensor_links": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of target node IDs (e.g., ['BC_001', 'PW_002'])",
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
        "name": "exocortex_mutate_phase_space",
        "description": "Modulates, updates, decays, or prunes an existing node in the active phase-space topology.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_node_id": {
                    "type": "string",
                    "description": "Unique identifier of the target node (e.g. 'PW_001', 'BC_001')"
                },
                "action": {
                    "type": "string",
                    "enum": ["STRENGTHEN", "DECAY", "PRUNE", "UPDATE"],
                    "description": "Structural operation: STRENGTHEN (+weight), DECAY (-weight), PRUNE (remove node), UPDATE (modify payload)"
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

    def _tool_gauge_field(self, query_vector: str, top_k: int = 3) -> str:
        res = self.graph_store.get_resonant_nodes(query_vector, top_k=top_k)
        if not res:
            return "<field_gauge status='quiescent' />"
        lines = [f"<field_gauge query='{query_vector}'>"]
        for nid, attrs, sim in res:
            lines.append(f"  <resonance id='{nid}' label='{attrs.get('label')}' type='{attrs.get('type')}' score='{sim:.2f}' />")
        lines.append("</field_gauge>")
        return "\n".join(lines)

    def _tool_imprint_field(self, node_type: str, label: str, content_payload: str, tensor_links: Optional[List[str]] = None) -> str:
        try:
            res = self.graph_store.imprint_node(node_type, label, content_payload, tensor_links)
            conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "None"
            return (
                f"Field state materialized: Node {res['node_id']} ('{label}') wired into '{res['topology']}'. "
                f"| Wired to: {conns}"
            )
        except Exception as e:
            return f"<error>Imprinting failed: {e}</error>"

    def _tool_temporal_anchor(self, scope: str = "full") -> str:
        now = datetime.datetime.now()
        iso = now.isoformat()
        human = now.strftime("%d.%m.%Y, %H:%M:%S")
        kw = now.isocalendar()[1]
        return f"<temporal_anchor>\n  <human_readable>{human}</human_readable>\n  <iso8601>{iso}</iso8601>\n  <calendar_context>Week {kw}, Year {now.year}</calendar_context>\n</temporal_anchor>"
    
    def _handle_mutate_phase_space(
        self,
        target_node_id: str,
        action: str,
        payload_update: Optional[str] = None,
        delta: float = 0.2
    ) -> str:
        """Handler for exocortex_mutate_phase_space tool."""
        if not self.graph_store:
            return "<error>GraphStore is not initialized in engine.</error>"

        res = self.graph_store.mutate_node(
            target_node_id=target_node_id,
            action=action,
            payload_update=payload_update,
            delta=delta
        )

        if res.get("status") == "error":
            return f"<phase_space_mutation status='error' message='{res.get('message')}' />"

        delta_info = f" new_weight='{res.get('new_weight')}'" if "new_weight" in res else ""
        pruned_info = " pruned='true'" if action.upper() == "PRUNE" else ""

        return f"<phase_space_mutation status='success' node_id='{target_node_id}' action='{action.upper()}'{delta_info}{pruned_info} />"

    # --- ReAct Execution Loop ---
    def execute_turn(self, user_input: str, max_turns: int = 5) -> Generator[Dict[str, Any], None, None]:
        """
        Executes a full cognitive turn including the ReAct tool loop.
        Yielded Events:
          - {'event': 'field_context', 'xml': str}
          - {'event': 'tool_call', 'name': str, 'args': dict}
          - {'event': 'tool_result', 'result': str}
          - {'event': 'response_chunk', 'text': str}
          - {'event': 'completed', 'final_text': str}
        """
        # 1. Compute vector resonance via embedding guard
        safe_query = slice_for_embedding(user_input)
        field_xml = self.graph_store.assemble_field_context(safe_query)
        yield {"event": "field_context", "xml": field_xml}

        # 2. Dynamically assemble system prompt
        full_system_prompt = self.prompt_manager.build_system_prompt(field_xml)

        # 3. Update session with new user input
        self.session.add_user_message(user_input)
        self.session.active_graph = self.graph_store.active_graph_name

        # 4. Prepare message history for Ollama
        history = prune_history_if_needed(self.session.messages)
        messages_payload = [{"role": "system", "content": full_system_prompt}] + history

        turn_count = 0
        final_response_text = ""

        while turn_count < max_turns:
            turn_count += 1

            response = self.client.chat(
                model=self.model_name,
                messages=messages_payload,
                tools=self.tools_schema,
                options={"num_ctx": self.num_ctx},
            )

            msg = response.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            # Tool calls detected?
            if tool_calls:
                messages_payload.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

                for call in tool_calls:
                    fn_name = call.get("function", {}).get("name", "")
                    fn_args = call.get("function", {}).get("arguments", {})

                    yield {"event": "tool_call", "name": fn_name, "args": fn_args}

                    handler = self.tool_handlers.get(fn_name)
                    if handler:
                        tool_result = str(handler(**fn_args))
                    else:
                        tool_result = f"<error>Unknown tool '{fn_name}'</error>"

                    yield {"event": "tool_result", "result": tool_result}
                    messages_payload.append({"role": "tool", "content": tool_result})
            else:
                final_response_text = content
                yield {"event": "completed", "final_text": final_response_text}
                self.session.add_assistant_message(final_response_text)
                break
