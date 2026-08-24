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
    
    def get_boundary_constraints(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Extracts all active BoundaryConstraints regardless of vector similarity."""
        bcs = []
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == "BoundaryConstraint":
                bcs.append((str(node_id), attrs))
        bcs.sort(key=lambda x: x[0])  # Deterministische Sortierung (BC_001, BC_002, ...)
        return bcs
    
    def assemble_invariants_frame(self) -> str:
        """Assembles the immutable Boundary Invariants frame for the base system prompt."""
        bcs = self.get_boundary_constraints()
        if not bcs:
            return ""

        xml_parts = [f"<boundary_invariants topology='{self.active_graph_name}'>"]
        for node_id, attrs in bcs:
            label = attrs.get("label", node_id)
            payload = attrs.get("payload", "").strip()
            xml_parts.append(
                f"  <BoundaryConstraint id='{node_id}' label='{label}'>\n"
                f"    {payload}\n"
                f"  </BoundaryConstraint>"
            )
        xml_parts.append("</boundary_invariants>")
        return "\n".join(xml_parts)
    
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
            edge_weight = data.get("weight")
            
            edge_entry: Dict[str, Any] = {
                "id": f"edge_{u}_{v}",
                "fromNode": str(u),
                "fromSide": "right",
                "toNode": str(v),
                "toSide": "left",
            }
            
            # Kantenlabel mit Kosinus-Gewicht anreichern
            if relation:
                if edge_weight is not None and isinstance(edge_weight, (int, float)) and edge_weight != 1.0:
                    edge_entry["label"] = f"{relation} ({edge_weight:.2f})"
                else:
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

    def get_resonant_nodes(
        self, 
        query: str, 
        top_k: int = 4, 
        threshold: float = 0.50,
        exclude_types: Optional[List[str]] = None
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Retrieves top-k resonant nodes via cosine similarity, filtering excluded node types."""
        query_vec = self._get_embedding(query)
        if not query_vec:
            return []

        excluded = set(exclude_types or ["BoundaryConstraint"])
        scored = []
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("type") in excluded:
                continue
            node_vec = attrs.get("embedding", [])
            sim = cosine_similarity(query_vec, node_vec)
            if sim >= threshold:
                scored.append((str(node_id), attrs, sim))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]
        
    def get_resonant_subgraph(
        self,
        query: str,
        seed_top_k: int = 2,
        threshold: float = 0.50,
        max_hops: int = 1,
        max_total_nodes: int = 6,
    ) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extracts an induced resonant subgraph via undirected 1-hop spreading activation.
        - Seeds: Top-k vector matches (>= threshold, excluding BCs).
        - Neighbors: Activated purely via structural links (sorted by edge weight).
        - Links: Rendered preserving original edge direction and relation semantics.
        """
        seeds = self.get_resonant_nodes(
            query=query, 
            top_k=seed_top_k, 
            threshold=threshold, 
            exclude_types=["BoundaryConstraint"]
        )
        if not seeds:
            return {}, []

        selected_nodes: Dict[str, Dict[str, Any]] = {}
        for node_id, attrs, sim in seeds:
            node_data = dict(attrs)
            node_data["is_seed"] = True
            node_data["resonance"] = sim
            selected_nodes[node_id] = node_data

        # 1-Hop ungerichtete Nachbarschaft mit Kanten-Priorisierung
        candidate_neighbors: List[Tuple[str, float, str]] = []  # (neighbor_id, edge_weight, edge_relation)
        
        for seed_id in list(selected_nodes.keys()):
            # Ungerichtet: Alle ein- und ausgehenden Kanten sammeln
            in_edges = self.graph.in_edges(seed_id, data=True)
            out_edges = self.graph.out_edges(seed_id, data=True)
            
            for u, _, data in in_edges:
                if u not in selected_nodes and self.graph.nodes[u].get("type") != "BoundaryConstraint":
                    candidate_neighbors.append((u, float(data.get("weight", 1.0)), data.get("relation", "")))
                    
            for _, v, data in out_edges:
                if v not in selected_nodes and self.graph.nodes[v].get("type") != "BoundaryConstraint":
                    candidate_neighbors.append((v, float(data.get("weight", 1.0)), data.get("relation", "")))

        # Nach Kantengewicht absteigend sortieren
        candidate_neighbors.sort(key=lambda x: x[1], reverse=True)

        for neighbor_id, weight, rel in candidate_neighbors:
            if neighbor_id in selected_nodes:
                continue
            if len(selected_nodes) >= max_total_nodes:
                break
            
            n_attrs = dict(self.graph.nodes[neighbor_id])
            n_attrs["is_seed"] = False
            n_attrs["resonance"] = None
            selected_nodes[neighbor_id] = n_attrs

        # Induzierte Kanten zwischen allen selektierten Knoten sammeln
        subgraph_edges = []
        for u, v, data in self.graph.edges(data=True):
            if u in selected_nodes and v in selected_nodes:
                subgraph_edges.append({
                    "source": str(u),
                    "target": str(v),
                    "relation": data.get("relation", "connected_to"),
                    "weight": data.get("weight", 1.0)
                })

        return selected_nodes, subgraph_edges

    def assemble_field_context(self, query: str) -> str:
        """Assembles the dynamic resonant phase-space context including topological links."""
        nodes, edges = self.get_resonant_subgraph(
            query=query, 
            seed_top_k=2, 
            threshold=0.50, 
            max_hops=1, 
            max_total_nodes=6
        )
        if not nodes:
            return ""

        xml_parts = [f"<active_phase_space topology='{self.active_graph_name}'>"]
        
        # 1. Knoten rendern
        for node_id, attrs in nodes.items():
            n_type = attrs.get("type", "Node")
            label = attrs.get("label", node_id)
            payload = attrs.get("payload", "").strip()
            
            if attrs.get("is_seed"):
                sim_str = f" resonance='{attrs['resonance']:.2f}'"
            else:
                sim_str = " context='topological_neighbor'"

            xml_parts.append(
                f"  <{n_type} id='{node_id}' label='{label}'{sim_str}>\n"
                f"    {payload}\n"
                f"  </{n_type}>"
            )

        # 2. Topologische Kanten rendern
        if edges:
            xml_parts.append("  <topological_links>")
            for edge in edges:
                rel = edge["relation"]
                w = edge["weight"]
                w_attr = f" weight='{w:.2f}'" if isinstance(w, (int, float)) and w != 1.0 else ""
                xml_parts.append(
                    f"    <link from='{edge['source']}' to='{edge['target']}' relation='{rel}'{w_attr} />"
                )
            xml_parts.append("  </topological_links>")

        xml_parts.append("</active_phase_space>")
        return "\n".join(xml_parts)

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
        
    def imprint_node(
        self,
        node_type: str,
        label: str,
        content_payload: str,
        tensor_links: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically imprints a new node into the active NetworkX topology,
        calculates its bge-m3 embedding, establishes tensor links, and persists to vault.
        """
        tensor_links = tensor_links or []
        
        # 1. Deterministische ID generieren (z. B. TO_004 oder Hash/Prefix)
        prefix_map = {
            "BoundaryConstraint": "BC",
            "PotentialWell": "PW",
            "TrajectoryOperator": "TO",
            "PhaseSpaceTrace": "PST",
        }
        prefix = prefix_map.get(node_type, "NODE")
        existing_indices = [
            int(nid.split("_")[1]) for nid in self.graph.nodes
            if nid.startswith(f"{prefix}_") and nid.split("_")[1].isdigit()
        ]
        next_idx = max(existing_indices, default=0) + 1
        node_id = f"{prefix}_{next_idx:03d}"

        # 2. Embedding berechnen via internem Ollama-Client (bge-m3)
        embedding_text = f"{label}: {content_payload}"
        embedding = self._get_embedding(embedding_text)

        # 3. Node in NetworkX einhängen
        node_attrs = {
            "type": node_type,
            "label": label,
            "payload": content_payload,
            "weight": 1.0,
            "created_at": datetime.datetime.now().isoformat(),
        }
        if embedding:
            node_attrs["embedding"] = embedding

        self.graph.add_node(node_id, **node_attrs)

        # 4. Kanten (Tensor-Links) schlagen
        wired = []
        for target_id in tensor_links:
            target_id = target_id.strip()
            if self.graph.has_node(target_id):
                self.graph.add_edge(node_id, target_id, relation="tensor_link", weight=0.85)
                wired.append(target_id)

        # 5. Persistieren (JSON + Canvas-Sync)
        self.save_graph()

        return {
            "status": "success",
            "node_id": node_id,
            "label": label,
            "topology": self.active_graph_name,
            "wired_connections": wired,
        }
