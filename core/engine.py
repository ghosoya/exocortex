"""
core/engine.py
ExecutionEngine: ReAct-Schleife, Tool-Dispatching und dynamische Kontext-Assemblierung.
"""

from typing import Any, Callable, Dict, Generator, List, Optional
from pathlib import Path
import json
import ollama

from server.graph_store import GraphStore
from server.vault_io import VaultIO
from .guards import prune_history_if_needed, slice_for_embedding
from .session import SessionManager
from core.prompts import PromptManager


class ExecutionEngine:
    def __init__(
        self,
        graph_store: GraphStore,
        session_manager: SessionManager,
        model_name: str = "gemma4:12b",
        num_ctx: int = 65536,
        ollama_host: str = "http://127.0.0.1:11434",
        config_dir: Optional[Path] = None,
    ):
        self.graph_store = graph_store
        self.session = session_manager
        self.model_name = model_name
        self.num_ctx = num_ctx
        self.client = ollama.Client(host=ollama_host)
        self.config_dir = config_dir or (Path(__file__).parent.parent / "config")
        self.prompt_manager = PromptManager()

        # Tool-Registry (Entkoppeltes Dispatching)
        self.tools_schema = self._build_tools_schema()
        self.tool_handlers: Dict[str, Callable[..., Any]] = {
            "read_vault_note": self._tool_read_vault_note,
            "append_scratchpad": self._tool_append_scratchpad,
            "exocortex_gauge_field": self._tool_gauge_field,
            "exocortex_imprint_field": self._tool_imprint_field,
            "exocortex_temporal_anchor": self._tool_temporal_anchor,
        }

    def _load_base_prompt(self) -> str:
        prompt_file = self.config_dir / "system_base.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return "Du bist der Exocortex. Antworte präzise und wende den Analytic Razor an."

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_vault_note",
                    "description": "Liest eine Markdown-Notiz aus dem Obsidian-Vault ein.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_name": {"type": "string", "description": "Relativer Pfad oder Name (z.B. 'Sessions/systemic.md')"}
                        },
                        "required": ["note_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "append_scratchpad",
                    "description": "Hängt Text an eine Scratchpad-Notiz im Vault an.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Textinhalt."},
                            "filename": {"type": "string", "description": "Dateiname (Default: Active_Scratchpad.md)"}
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_gauge_field",
                    "description": "Misst Resonanzknoten im Phasenraum für ein bestimmtes Thema.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_vector": {"type": "string", "description": "Semantischer Suchbegriff."},
                            "top_k": {"type": "integer", "description": "Maximale Anzahl Knoten (Default: 3)"}
                        },
                        "required": ["query_vector"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "exocortex_imprint_field",
                    "description": "Erzeugt einen neuen Knoten in der Topologie und verknüpft ihn.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_type": {
                                "type": "string",
                                "enum": ["BoundaryConstraint", "TrajectoryOperator", "PotentialWell", "PhaseSpaceTrace"],
                            },
                            "label": {"type": "string", "description": "Kompakter Bezeichner."},
                            "content_payload": {"type": "string", "description": "Axiom, Regel oder Synthese."},
                            "tensor_links": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Liste von Ziel-Knoten-IDs (z.B. ['BC_001', 'PW_002'])"
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
                    "description": "Gibt die aktuelle Systemzeit und Kalenderwoche zurück.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {"type": "string", "enum": ["full", "iso", "time_only"]}
                        },
                    },
                },
            },
        ]

    # --- Tool Implementierungen ---
    def _tool_read_vault_note(self, note_name: str) -> str:
        try:
            content = self.graph_store.vault_io.read_note(note_name)
            return f"<vault_note path='{note_name}'>\n{content}\n</vault_note>"
        except Exception as e:
            return f"<error>Fehler beim Lesen von '{note_name}': {e}</error>"

    def _tool_append_scratchpad(self, content: str, filename: str = "Active_Scratchpad.md") -> str:
        try:
            path = self.graph_store.vault_io.append_scratchpad(content, filename)
            return f"<scratchpad status='appended' path='{path}' />"
        except Exception as e:
            return f"<error>Fehler beim Schreiben ins Scratchpad: {e}</error>"

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
            conns = ", ".join(res["wired_connections"]) if res["wired_connections"] else "Keine"
            return (
                f"Field state materialized: Node {res['node_id']} ('{label}') wired into '{res['topology']}'. "
                f"| Verdrahtet mit: {conns}"
            )
        except Exception as e:
            return f"<error>Imprinting fehlgeschlagen: {e}</error>"

    def _tool_temporal_anchor(self, scope: str = "full") -> str:
        import datetime
        now = datetime.datetime.now()
        iso = now.isoformat()
        human = now.strftime("%d.%m.%Y, %H:%M:%S")
        kw = now.isocalendar()[1]
        return f"<temporal_anchor>\n  <human_readable>{human}</human_readable>\n  <iso8601>{iso}</iso8601>\n  <calendar_context>KW {kw}, Jahr {now.year}</calendar_context>\n</temporal_anchor>"

    # --- ReAct Execution Loop ---
    def execute_turn(self, user_input: str, max_turns: int = 5) -> Generator[Dict[str, Any], None, None]:
        """
        Führt einen vollen kognitiven Zug inklusive ReAct-Tool-Loop aus.
        Yielded Events:
          - {'event': 'field_context', 'xml': str}
          - {'event': 'tool_call', 'name': str, 'args': dict}
          - {'event': 'tool_result', 'result': str}
          - {'event': 'response_chunk', 'text': str}
          - {'event': 'completed', 'final_text': str}
        """
        # 1. Vektor-Resonanz via Embedding Guard berechnen
        safe_query = slice_for_embedding(user_input)
        field_xml = self.graph_store.assemble_field_context(safe_query)
        yield {"event": "field_context", "xml": field_xml}

        # 2. System-Prompt dynamisch zusammenbauen
        full_system_prompt = self.prompt_manager.build_system_prompt(field_xml)

        # 3. Session mit neuer Nutzereingabe aktualisieren
        self.session.add_user_message(user_input)
        self.session.active_graph = self.graph_store.active_graph_name

        # 4. Verlauf für Ollama vorbereiten
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

            # Tool Calls entdeckt?
            if tool_calls:
                # Assistant Zwischenschritt in History spiegeln
                messages_payload.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

                for call in tool_calls:
                    fn_name = call.get("function", {}).get("name", "")
                    fn_args = call.get("function", {}).get("arguments", {})

                    yield {"event": "tool_call", "name": fn_name, "args": fn_args}

                    handler = self.tool_handlers.get(fn_name)
                    if handler:
                        tool_result = str(handler(**fn_args))
                    else:
                        tool_result = f"<error>Unbekanntes Tool '{fn_name}'</error>"

                    yield {"event": "tool_result", "result": tool_result}

                    # Tool-Antwort in Payload einspeisen
                    messages_payload.append({"role": "tool", "content": tool_result})
            else:
                # Reines finales Text-Ergebnis
                final_response_text = content
                yield {"event": "completed", "final_text": final_response_text}
                self.session.add_assistant_message(final_response_text)
                break
