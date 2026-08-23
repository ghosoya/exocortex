"""
server/graph_store.py
Topological substrate: NetworkX state management, vector resonance, imprinting,
Copy-on-Write RAM lifecycle, snapshots, and automatic Obsidian Canvas projection.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import datetime
import json
import math
import os
import networkx as nx
import re
from typing import Optional, Dict

import ollama

from core.compiler import _normalize_topology_schema
from core.guards import slice_for_embedding
from .vault_io import VaultIO


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates bounded cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    val = dot / (norm1 * norm2)
    return max(-1.0, min(1.0, val))


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
        self.is_snapshot: bool = False
        self.mutations_count: int = 0
        self.graph: nx.DiGraph = nx.DiGraph()
        
        # Ensure base, snapshot, and canvas directories exist
        (self.vault_io.vault_path / "Topologies" / "base").mkdir(parents=True, exist_ok=True)
        (self.vault_io.vault_path / "Topologies" / "snapshots").mkdir(parents=True, exist_ok=True)
        (self.vault_io.vault_path / "Canvases" / "snapshots").mkdir(parents=True, exist_ok=True)

        self.load_graph("default")

    def _get_embedding(self, text: str) -> List[float]:
        safe_text = slice_for_embedding(text, max_chars=1500)
        if not safe_text:
            return []
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
            "PotentialWell": {"x": -320, "color": "5"},         # Cyan
            "TrajectoryOperator": {"x": 320, "color": "3"},     # Purple
            "PhaseSpaceTrace": {"x": 950, "color": "4"},        # Green
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

            embedding = attrs.get("embedding", [])
            has_embedding = bool(isinstance(embedding, list) and len(embedding) > 0)
            vec_badge = f"vec: ✓ ({len(embedding)}d)" if has_embedding else "vec: ✗"

            text_content = (
                f"### `{node_id}` {label}\n"
                f"`w: {weight:.2f}` · `{vec_badge}`\n"
                f"---\n"
                f"{payload}"
            )

            canvas_nodes.append({
                "id": str(node_id),
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
                "fromNode": str(u),
                "fromSide": "right",
                "toNode": str(v),
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
        canvas_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write
        tmp_path = canvas_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(canvas_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, canvas_path)

        return str(canvas_path)

    def load_graph(self, graph_name: str) -> Dict[str, Any]:
        """Loads a topology (checking base/, snapshots/, and vault root) with schema normalization."""
        clean_name = graph_name.replace(".json", "")
        
        base_path = self.vault_io.vault_path / "Topologies" / "base" / f"{clean_name}.json"
        snap_path = self.vault_io.vault_path / "Topologies" / "snapshots" / f"{clean_name}.json"
        
        if base_path.exists():
            raw_data = json.loads(base_path.read_text(encoding="utf-8"))
            self.is_snapshot = False
        elif snap_path.exists():
            raw_data = json.loads(snap_path.read_text(encoding="utf-8"))
            self.is_snapshot = True
        else:
            raw_data = self.vault_io.read_graph_json(clean_name)
            self.is_snapshot = False

        # Normalize schema (handles declarative blueprints and graph exports)
        data = _normalize_topology_schema(raw_data)
        if "links" in data and "edges" not in data:
            data["edges"] = data.pop("links")
            
        self.graph = nx.node_link_graph(data, directed=True, multigraph=False)
        self.active_graph_name = clean_name
        self.mutations_count = 0

        # Compute missing embeddings in-memory
        for node_id, attrs in self.graph.nodes(data=True):
            if "embedding" not in attrs or not attrs["embedding"]:
                payload = attrs.get("payload", "")
                label = attrs.get("label", node_id)
                attrs["embedding"] = self._get_embedding(f"{label}: {payload}")

        # Sync live canvas
        self.export_canvas("Exocortex_Interactive.canvas")
        return self.get_graph_stats()

    def save_graph(self, graph_name: Optional[str] = None) -> str:
        """
        Copy-on-Write semantics:
        Base topologies remain protected in RAM. Snapshots are synchronized to disk atomically.
        """
        target_name = graph_name or self.active_graph_name
        self.graph.graph["updated_at"] = datetime.datetime.now().isoformat()
        self.graph.graph["name"] = target_name
        self.graph.graph["embedding_model"] = self.embedding_model

        self.export_canvas("Exocortex_Interactive.canvas")

        if self.is_snapshot:
            data = nx.node_link_data(self.graph)
            snap_path = self.vault_io.vault_path / "Topologies" / "snapshots" / f"{target_name}.json"
            snap_path.parent.mkdir(parents=True, exist_ok=True)
            
            tmp_path = snap_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, snap_path)
            return str(snap_path)
        
        return "in-memory (base topology protected)"

    def freeze_snapshot(self, tag: Optional[str] = None) -> Dict[str, str]:
        """Freezes the current RAM state into an immutable snapshot (JSON + Canvas)."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{tag}" if tag else ""
    
        # Rekursive Timestamp-Kaskaden (YYYYMMDD_HHMMSS_) restlos entfernen
        clean_base_name = re.sub(r"^(\d{8}_\d{6}_)+", "", self.active_graph_name).strip("_")
        if not clean_base_name:
            clean_base_name = "default"

        snapshot_filename = f"{timestamp}_{clean_base_name}{suffix}"

        # 1. JSON snapshot
        data = nx.node_link_data(self.graph)
        snap_json_path = self.vault_io.vault_path / "Topologies" / "snapshots" / f"{snapshot_filename}.json"
        snap_json_path.parent.mkdir(parents=True, exist_ok=True)
    
        tmp_json = snap_json_path.with_suffix(".tmp")
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_json, snap_json_path)

        # 2. Canvas snapshot
        canvas_rel_path = f"Canvases/snapshots/{snapshot_filename}.canvas"
        snap_canvas_path = self.export_canvas(canvas_rel_path)

        return {
            "snapshot_name": snapshot_filename,
            "json_path": str(snap_json_path),
            "canvas_path": str(snap_canvas_path)
        }
    
    def get_graph_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for _, attrs in self.graph.nodes(data=True):
            t = attrs.get("type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "name": self.active_graph_name,
            "is_snapshot": self.is_snapshot,
            "mutations": self.mutations_count,
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "types": type_counts,
        }

    def switch_graph(self, graph_name: str) -> Dict[str, Any]:
        return self.load_graph(graph_name)

    def get_resonant_nodes(self, query: str, top_k: int = 4, threshold: float = 0.50) -> List[Tuple[str, Dict[str, Any], float]]:
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
            if str(n).startswith(f"{prefix}_"):
                parts = str(n).split("_")
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
        self.mutations_count += 1

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
            new_embedding = self._get_embedding(clean_payload)
            
            self.graph.nodes[target_node_id]["payload"] = clean_payload
            self.graph.nodes[target_node_id]["embedding"] = new_embedding
            result_payload["updated_payload"] = clean_payload
        
        elif action == "SET_WEIGHT":
            new_weight = max(0.05, min(3.0, round(float(delta), 2)))
            self.graph.nodes[target_node_id]["weight"] = new_weight
            result_payload["previous_weight"] = current_weight
            result_payload["new_weight"] = new_weight
        else:
            return {"status": "error", "message": f"Unknown mutation action: '{action}'."}

        self.mutations_count += 1
        self.save_graph() 
        return result_payload
