"""
server/graph_store.py
Topological substrate: NetworkX state management, vector resonance, imprinting,
and automatic Obsidian Canvas projection.
"""

from typing import Any, Dict, List, Optional, Tuple
import datetime
import json
import math
from pathlib import Path
import networkx as nx
import ollama
from core.guards import slice_for_embedding

from .vault_io import VaultIO


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0


class GraphStore:
    def __init__(
        self,
        vault_io: Optional[VaultIO] = None,
        embedding_model: str = "bge-m3",
        ollama_host: str = "http://127.0.0.1:11434",
    ):
        self.vault_io = vault_io or VaultIO()
        self.embedding_model = embedding_model
        self.client = ollama.Client(host=ollama_host)
        self.active_graph_name: str = "default"
        self.graph: nx.DiGraph = nx.DiGraph()
        self.load_graph("default")

    def _get_embedding(self, text: str) -> List[float]:
        safe_text = text[:1500]
        try:
            res = self.client.embeddings(model=self.embedding_model, prompt=safe_text)
            return res.get("embedding", [])
        except Exception as e:
            print(f"[!] GraphStore embedding error: {e}")
            return []

    def export_canvas(self, canvas_filename: str = "Exocortex_Interactive.canvas") -> str:
        """Projects the NetworkX graph into a structured Obsidian .canvas file with weights and vector telemetry."""
        type_config = {
            "BoundaryConstraint": {"x": -950, "color": "1"},   # Red
            "PotentialWell": {"x": -320, "color": "5"},        # Cyan
            "TrajectoryOperator": {"x": 320, "color": "3"},    # Purple
            "PhaseSpaceTrace": {"x": 950, "color": "4"},       # Green
        }

        y_counters: Dict[str, int] = {k: 0 for k in type_config}
        canvas_nodes = []
        canvas_edges = []

        card_width = 360
        card_height = 220
        y_gap = 50

        for node_id, attrs in self.graph.nodes(data=True):
            n_type = attrs.get("type", "PotentialWell")
            cfg = type_config.get(n_type, {"x": 0, "color": "0"})

            col_x = cfg["x"]
            idx = y_counters.get(n_type, 0)
            node_y = idx * (card_height + y_gap) - 400
            y_counters[n_type] = idx + 1

            label = attrs.get("label", node_id)
            payload = attrs.get("payload", "").strip()
            weight = float(attrs.get("weight", 1.0))

            # Vektor-Telemetrie prüfen
            embedding = attrs.get("embedding", [])
            has_embedding = bool(isinstance(embedding, list) and len(embedding) > 0)
            vec_badge = f"vec: ✓ ({len(embedding)}d)" if has_embedding else "vec: ✗"

            # Markdown-Karteninhalt mit Telemetrie-Zeile
            text_content = (
                f"### `{node_id}` {label}\n"
                f"`w: {weight:.2f}` · `{vec_badge}`\n"
                f"---\n"
                f"{payload}"
            )

            canvas_nodes.append({
                "id": node_id,
                "x": col_x,
                "y": node_y,
                "width": card_width,
                "height": card_height,
                "type": "text",
                "text": text_content,
                "color": cfg["color"]
            })

        for u, v, data in self.graph.edges(data=True):
            relation = data.get("relation", "")
            edge_entry: Dict[str, Any] = {
                "id": f"edge_{u}_{v}",
                "fromNode": u,
                "fromSide": "right",
                "toNode": v,
                "toSide": "left",
            }
            if relation:
                edge_entry["label"] = relation
            canvas_edges.append(edge_entry)

        canvas_data = {
            "nodes": canvas_nodes,
            "edges": canvas_edges
        }

        canvas_path = self.vault_io.vault_path / canvas_filename
        with open(canvas_path, "w", encoding="utf-8") as f:
            json.dump(canvas_data, f, indent=2, ensure_ascii=False)

        return str(canvas_path)

    def load_graph(self, graph_name: str) -> Dict[str, Any]:
        """Loads a topology from the vault and synchronizes the Canvas."""
        data = self.vault_io.read_graph_json(graph_name)
        
        # Backward compatibility: automatically normalize legacy 'links' to 'edges'
        if "links" in data and "edges" not in data:
            data["edges"] = data.pop("links")
            
        self.graph = nx.node_link_graph(data, directed=True, multigraph=False)
        self.active_graph_name = graph_name

        dirty = False
        for node_id, attrs in self.graph.nodes(data=True):
            if "embedding" not in attrs or not attrs["embedding"]:
                payload = attrs.get("payload", "")
                label = attrs.get("label", node_id)
                attrs["embedding"] = self._get_embedding(f"{label}: {payload}")
                dirty = True

        if dirty:
            self.save_graph(graph_name)
        else:
            # Synchronize canvas on load as well
            self.export_canvas()

        return self.get_graph_stats()

    def save_graph(self, graph_name: Optional[str] = None) -> str:
        """Serializes graph state into JSON schema and synchronizes the Canvas."""
        target_name = graph_name or self.active_graph_name
        self.graph.graph["updated_at"] = datetime.datetime.now().isoformat()
        self.graph.graph["name"] = target_name
        self.graph.graph["embedding_model"] = self.embedding_model

        data = nx.node_link_data(self.graph)
        path = self.vault_io.write_graph_json(target_name, data)
        self.active_graph_name = target_name

        # Automatic Canvas projection
        self.export_canvas()
        return path

    def get_graph_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for _, attrs in self.graph.nodes(data=True):
            t = attrs.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "name": self.active_graph_name,
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "types": type_counts,
        }
    
    def switch_graph(self, graph_name: str) -> Dict[str, Any]:
        """Loads a different graph by name, ensures embeddings exist, and updates canvas."""
        # Dateiendung handhaben falls mit übergeben
        clean_name = graph_name.replace(".json", "")
        self.load_graph(clean_name)
        
        # Fehlende Embeddings on-the-fly berechnen falls nötig
        updated = False
        for node_id, attrs in self.graph.nodes(data=True):
            emb = attrs.get("embedding", [])
            if not emb or len(emb) == 0:
                payload = attrs.get("payload", "")
                if payload:
                    attrs["embedding"] = self._get_embedding(payload)
                    updated = True
        
        if updated:
            self.save_graph(clean_name)
        else:
            self.export_canvas()
            
        return self.get_graph_stats()
        
    def get_resonant_nodes(self, query: str, top_k: int = 4, threshold: float = 0.45) -> List[Tuple[str, Dict[str, Any], float]]:
        query_vec = self._get_embedding(query)
        if not query_vec:
            return []

        scored = []
        for node_id, attrs in self.graph.nodes(data=True):
            node_vec = attrs.get("embedding", [])
            sim = cosine_similarity(query_vec, node_vec)
            if sim >= threshold:
                scored.append((node_id, attrs, sim))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def assemble_field_context(self, query: str) -> str:
        resonant = self.get_resonant_nodes(query, top_k=4)
        if not resonant:
            return "<active_phase_space status='quiescent' />"

        xml_parts = [f"<active_phase_space topology='{self.active_graph_name}'>"]
        for node_id, attrs, sim in resonant:
            n_type = attrs.get("type", "Node")
            label = attrs.get("label", node_id)
            payload = attrs.get("payload", "")
            xml_parts.append(
                f"  <{n_type} id='{node_id}' label='{label}' resonance='{sim:.2f}'>\n"
                f"    {payload}\n"
                f"  </{n_type}>"
            )
        xml_parts.append("</active_phase_space>")
        return "\n".join(xml_parts)

    def imprint_node(self, node_type: str, label: str, content_payload: str, tensor_links: Optional[List[str]] = None) -> Dict[str, Any]:
        prefix_map = {
            "BoundaryConstraint": "BC",
            "TrajectoryOperator": "TO",
            "PotentialWell": "PW",
            "PhaseSpaceTrace": "PST",
        }
        prefix = prefix_map.get(node_type, "NODE")

        existing_nums = []
        for n in self.graph.nodes():
            if n.startswith(f"{prefix}_"):
                parts = n.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    existing_nums.append(int(parts[1]))
        next_idx = max(existing_nums, default=0) + 1
        new_id = f"{prefix}_{next_idx:03d}"

        new_embedding = self._get_embedding(f"{label}: {content_payload}")

        self.graph.add_node(
            new_id,
            type=node_type,
            label=label,
            payload=content_payload,
            embedding=new_embedding,
            weight=1.0,
            created_at=datetime.datetime.now().isoformat(),
        )

        wired_connections = []

        if tensor_links:
            for target in tensor_links:
                if self.graph.has_node(target):
                    self.graph.add_edge(new_id, target, relation="tensor_link", weight=1.0)
                    wired_connections.append(f"{target} (explicit)")

        for existing_id, attrs in self.graph.nodes(data=True):
            if existing_id == new_id:
                continue
            sim = cosine_similarity(new_embedding, attrs.get("embedding", []))
            if sim >= 0.52:
                self.graph.add_edge(new_id, existing_id, relation="semantic_resonance", weight=round(sim, 2))
                wired_connections.append(f"{existing_id} (sim: {sim:.2f})")

        # Persists NetworkX JSON AND updates Obsidian Canvas
        self.save_graph(self.active_graph_name)

        return {
            "node_id": new_id,
            "label": label,
            "topology": self.active_graph_name,
            "wired_connections": wired_connections,
        }
        
 
    def mutate_node(
        self,
        target_node_id: str,
        action: str,
        payload_update: Optional[str] = None,
        delta: float = 0.2
    ) -> Dict[str, Any]:
        """
        Executes discrete structural mutations on active topology nodes:
        STRENGTHEN, DECAY, PRUNE, or UPDATE.
        """
        if not self.graph.has_node(target_node_id):
            return {
                "status": "error",
                "message": f"Node '{target_node_id}' does not exist in active topology '{self.active_graph_name}'."
            }

        node_data = self.graph.nodes[target_node_id]
        action = action.upper()
        current_weight = float(node_data.get("weight", 1.0))
        result_payload = {"status": "success", "node_id": target_node_id, "action": action}

        if action == "STRENGTHEN":
            new_weight = min(3.0, round(current_weight + abs(delta), 2))
            self.graph.nodes[target_node_id]["weight"] = new_weight
            result_payload["previous_weight"] = current_weight
            result_payload["new_weight"] = new_weight

        elif action == "DECAY":
            new_weight = max(0.05, round(current_weight - abs(delta), 2))
            self.graph.nodes[target_node_id]["weight"] = new_weight
            result_payload["previous_weight"] = current_weight
            result_payload["new_weight"] = new_weight

        elif action == "PRUNE":
            node_label = node_data.get("label", target_node_id)
            node_type = node_data.get("type", "Unknown")
            self.graph.remove_node(target_node_id)
            result_payload["pruned_node"] = {"id": target_node_id, "label": node_label, "type": node_type}

        elif action == "UPDATE":
            if not payload_update or not payload_update.strip():
                return {
                    "status": "error",
                    "message": "Action UPDATE requires a non-empty 'payload_update' string."
                }
            
            clean_payload = slice_for_embedding(payload_update.strip())
            # Embedding neu berechnen (das ist der synchrone Teil)
            new_embedding = self._get_embedding(clean_payload)
            
            self.graph.nodes[target_node_id]["payload"] = clean_payload
            self.graph.nodes[target_node_id]["embedding"] = new_embedding
            result_payload["updated_payload"] = clean_payload
        
        elif action == "SET_WEIGHT":
            # Setzt das Gewicht direkt auf den übergebenen delta-Wert (begrenzt auf [0.05, 3.0])
            new_weight = max(0.05, min(3.0, round(float(delta), 2)))
            self.graph.nodes[target_node_id]["weight"] = new_weight
            result_payload["previous_weight"] = current_weight
            result_payload["new_weight"] = new_weight
        else:
            return {"status": "error", "message": f"Unknown mutation action: '{action}'."}

        # --- FIX HIER ---
        # Statt self._persist_and_sync() nutzen wir die bestehende Methode:
        self.save_graph() 
        # ----------------

        return result_payload

        # Synchronize phase space state and persist changes
        self._persist_and_sync()
        return result_payload
