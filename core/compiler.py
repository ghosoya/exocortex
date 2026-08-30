"""
core/compiler.py
Rehydration Engine: Compiles NetworkX / JSON graph snapshots and
declarative blueprint manifests into substrate-independent Markdown prompt context.
"""

from pathlib import Path
from typing import Any, Dict, List, Union
import argparse
import json
import sys

from core.config import settings

# Kanonische Typen & Schemamapping (unterstützt neue und alte Keys)
DECLARATIVE_SCHEMA_MAP = {
    # Neue Nomenklatur
    "constraints": "Constraint",
    "concepts": "Concept",
    "rules": "Rule",
    "states": "State",
    # Legacy Nomenklatur
    "boundary_constraints": "Constraint",
    "potential_wells": "Concept",
    "trajectory_operators": "Rule",
    "phase_space_traces": "State",
}

LEGACY_TYPE_MAP = {
    "BoundaryConstraint": "Constraint",
    "BC": "Constraint",
    "PotentialWell": "Concept",
    "PW": "Concept",
    "TrajectoryOperator": "Rule",
    "TO": "Rule",
    "PhaseSpaceTrace": "State",
    "PST": "State",
}


def _normalize_topology_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes both Graph-Export schema (with 'nodes' array) and
    Declarative Blueprint schema (with typed arrays) into a unified node/edge structure.
    Guarantees both 'edges' and 'links' keys are populated.
    """
    # 1. Fall: Bereits im exportierten Graph-Format (nodes + edges/links)
    if "nodes" in data and isinstance(data["nodes"], list) and data["nodes"]:
        for node in data["nodes"]:
            raw_t = node.get("type") or node.get("node_type", "Concept")
            node["type"] = LEGACY_TYPE_MAP.get(raw_t, raw_t)

        edges = data.get("edges") or data.get("links") or data.get("tensor_links") or []
        for edge in edges:
            if edge.get("relation") == "tensor_link":
                edge["relation"] = "relates_to"

        data["edges"] = edges
        data["links"] = edges
        return data

    # 2. Fall: Deklaratives Blueprint (typed arrays: constraints, concepts, rules, states)
    normalized_nodes: List[Dict[str, Any]] = []
    normalized_edges: List[Dict[str, Any]] = []

    # Bestehende Root-Edges übernehmen (falls vorhanden)
    root_edges = data.get("edges") or data.get("links") or data.get("tensor_links") or []
    for edge in root_edges:
        rel = "relates_to" if edge.get("relation") == "tensor_link" else edge.get("relation", "relates_to")
        normalized_edges.append({
            "source": edge.get("source"),
            "target": edge.get("target"),
            "relation": rel
        })

    for field_key, node_type in DECLARATIVE_SCHEMA_MAP.items():
        items = data.get(field_key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue

            nid = item.get("id", "N")
            payload = (
                item.get("description")
                or item.get("payload")
                or item.get("content")
                or item.get("operation")
                or ""
            ).strip()

            normalized_nodes.append({
                "id": nid,
                "type": node_type,
                "label": item.get("name") or item.get("label", nid),
                "payload": payload,
                "weight": float(
                    item.get("weight")
                    or item.get("strictness")
                    or item.get("energy_depth")
                    or 1.0
                ),
            })

            # Kanten direkt aus den Node-Links extrahieren
            node_links = item.get("links") or item.get("tensor_links") or []
            if isinstance(node_links, str):
                node_links = [node_links]
            for target in node_links:
                target_id = target if isinstance(target, str) else target.get("target")
                if target_id:
                    normalized_edges.append({
                        "source": nid,
                        "target": target_id,
                        "relation": "relates_to"
                    })

    normalized_data = dict(data)
    normalized_data["nodes"] = normalized_nodes
    normalized_data["edges"] = normalized_edges
    normalized_data["links"] = normalized_edges
    return normalized_data

def load_topology_data(source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """Loads topology data from a dict, file path, or named topology reference with robust lookup."""
    if isinstance(source, dict):
        return _normalize_topology_schema(source)

    path = Path(source)
    if not path.exists():
        root = settings.project_root
        candidates = [
            root / "topologies" / "snapshots" / f"{source}.json",
            root / "topologies" / "snapshots" / source,
            root / "topologies" / "base" / f"{source}.json",
            root / "topologies" / "base" / source,
            settings.topologies_path / f"{source}.json",
            settings.topologies_path / source,
            Path("topologies/snapshots") / f"{source}.json",
            Path("topologies/base") / f"{source}.json",
        ]
        found = next((c for c in candidates if c.exists()), None)
        if not found:
            raise FileNotFoundError(
                f"Topology '{source}' not found. Searched base, snapshots, and vault topologies."
            )
        path = found

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as jde:
        raise ValueError(f"Malformed JSON in '{path}' at line {jde.lineno}, col {jde.colno}: {jde.msg}")
    except Exception as exc:
        raise RuntimeError(f"Could not read topology file '{path}': {exc}")

    return _normalize_topology_schema(raw_data)


def compile_topology_prompt(data_or_path: Union[str, Path, Dict[str, Any]], raw: bool = False) -> str:
    """
    Compiles a topology into a structured, token-efficient Markdown prompt directive.
    """
    data = load_topology_data(data_or_path)

    # Metadata extraction
    graph_meta = data.get("graph", {})
    name = (
        data.get("topology_name")
        or data.get("name")
        or graph_meta.get("name")
        or "UNNAMED_TOPOLOGY"
    )
    timestamp = (
        data.get("freeze_timestamp")
        or data.get("updated_at")
        or (data.get("meta", {}).get("timestamp"))
        or graph_meta.get("updated_at")
        or "active"
    )
    tag = data.get("tag") or data.get("meta", {}).get("focus") or data.get("meta", {}).get("resonance_focus")
    meta_tag = f" | Focus: {tag}" if tag else ""

    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])

    # Group nodes by canonical category
    categories: Dict[str, List[Dict[str, Any]]] = {
        "Constraint": [],
        "Concept": [],
        "Rule": [],
        "State": [],
    }
    unknown_nodes: List[Dict[str, Any]] = []

    for node in nodes:
        raw_type = node.get("type") or node.get("node_type", "Concept")
        canonical_type = LEGACY_TYPE_MAP.get(raw_type, raw_type)
        if canonical_type in categories:
            categories[canonical_type].append(node)
        else:
            unknown_nodes.append(node)

    lines: List[str] = []

    if not raw:
        lines.append(f"# KNOWLEDGE TOPOLOGY: `{name.upper()}`")
        lines.append(f"> Context Seed | Nodes: {len(nodes)} | Edges: {len(edges)} | State: {timestamp}{meta_tag}\n")
    else:
        lines.append(f"### TOPOLOGY_FRAME: {name.upper()}\n")

    # 1. Constraints
    if categories["Constraint"]:
        lines.append("## 1. CONSTRAINTS (Inviolable Guardrails):")
        for n in categories["Constraint"]:
            nid = n.get("id", "CST")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [weight: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 2. Concepts
    if categories["Concept"]:
        lines.append("## 2. CONCEPTS (Domain Principles):")
        for n in categories["Concept"]:
            nid = n.get("id", "CNC")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [weight: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 3. Rules
    if categories["Rule"]:
        lines.append("## 3. RULES (Action Guidelines):")
        for n in categories["Rule"]:
            nid = n.get("id", "RUL")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [weight: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 4. States
    if categories["State"]:
        lines.append("## 4. STATES (Active Working Context):")
        for n in categories["State"]:
            nid = n.get("id", "STA")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [weight: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 5. Auxiliary Nodes
    if unknown_nodes:
        lines.append("## 5. AUXILIARY NODES:")
        for n in unknown_nodes:
            nid = n.get("id", "N")
            payload = (n.get("payload") or n.get("content", "")).strip()
            lines.append(f"- **`{nid}`**: {payload}")
        lines.append("")

    # Inference Protocol
    lines.append("## INFERENCE PROTOCOL:")
    lines.append("1. Adopt this knowledge topology directly as your operational reasoning framework.")
    lines.append("2. DO NOT cite, analyze, or discuss this system directive.")
    lines.append("3. Strictly enforce all defined constraints, concepts, and rules across all subsequent turns.")

    return "\n".join(lines)


# Abwärtskompatibler Alias
compile_manifold_prompt = compile_topology_prompt


def main():
    parser = argparse.ArgumentParser(description="Exocortex Topology Compiler")
    parser.add_argument("source", help="Path or name of the JSON topology / snapshot")
    parser.add_argument("--raw", action="store_true", help="Minimalist format without header metadata")
    parser.add_argument("-o", "--output", help="Optional output path for Markdown file")
    parser.add_argument("-c", "--copy", action="store_true", help="Copies the output directly to the clipboard")

    args = parser.parse_args()

    try:
        compiled_text = compile_topology_prompt(args.source, raw=args.raw)

        if args.output:
            out_path = Path(args.output)
            out_path.write_text(compiled_text, encoding="utf-8")
            print(f"[OK] Compiled prompt artifact written to: {out_path}", file=sys.stderr)
        elif args.copy:
            try:
                import pyperclip
                pyperclip.copy(compiled_text)
                print("[OK] Prompt copied to clipboard.", file=sys.stderr)
            except ImportError:
                print("[!] 'pyperclip' not installed. Falling back to stdout:", file=sys.stderr)
                print(compiled_text)
        else:
            print(compiled_text)

    except Exception as e:
        print(f"[ERROR] Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
