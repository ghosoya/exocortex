"""
core/compiler.py
Rehydration Engine: Compiles NetworkX / JSON topology snapshots and
declarative blueprint manifests into substrate-independent Markdown attractor prompts.
"""

from pathlib import Path
from typing import Any, Dict, List, Union
import argparse
import json
import sys

from core.config import settings

# Mapping from declarative keys to canonical node categories
DECLARATIVE_SCHEMA_MAP = {
    "boundary_constraints": "BoundaryConstraint",
    "potential_wells": "PotentialWell",
    "trajectory_operators": "TrajectoryOperator",
    "phase_space_traces": "PhaseSpaceTrace",
}


def _normalize_topology_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes both Graph-Export schema (with 'nodes' array) and
    Declarative Blueprint schema (with 'boundary_constraints' arrays)
    into a unified node/edge structure.
    """
    # If already in Graph format, return as-is
    if "nodes" in data and isinstance(data["nodes"], list) and data["nodes"]:
        return data

    normalized_nodes: List[Dict[str, Any]] = []
    normalized_edges: List[Dict[str, Any]] = data.get("edges") or data.get("links") or data.get("tensor_links") or []

    for field_key, node_type in DECLARATIVE_SCHEMA_MAP.items():
        items = data.get(field_key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # Extract payload across diverse schema dialects
            payload = (
                item.get("description")
                or item.get("payload")
                or item.get("content")
                or item.get("operation")
                or ""
            ).strip()
            
            normalized_nodes.append({
                "id": item.get("id", "N"),
                "type": node_type,
                "label": item.get("name") or item.get("label", item.get("id", "N")),
                "payload": item.get("description") or item.get("payload") or item.get("content", ""),
                "weight": item.get("strictness") or item.get("energy_depth") or item.get("weight", 1.0),
            })

    normalized_data = dict(data)
    normalized_data["nodes"] = normalized_nodes
    normalized_data["edges"] = normalized_edges
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


def compile_manifold_prompt(data_or_path: Union[str, Path, Dict[str, Any]], raw: bool = False) -> str:
    """
    Compiles a topology into a hierarchical Markdown attractor field directive.
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
    tag = data.get("tag") or data.get("meta", {}).get("resonance_focus")
    meta_tag = f" | Resonance: {tag}" if tag else ""

    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])

    # Group nodes by ontological category
    categories: Dict[str, List[Dict[str, Any]]] = {
        "BoundaryConstraint": [],
        "PotentialWell": [],
        "TrajectoryOperator": [],
        "PhaseSpaceTrace": [],
    }
    unknown_nodes: List[Dict[str, Any]] = []

    for node in nodes:
        n_type = node.get("type") or node.get("node_type", "Unknown")
        if n_type in categories:
            categories[n_type].append(node)
        else:
            unknown_nodes.append(node)

    lines: List[str] = []

    if not raw:
        lines.append(f"# COGNITIVE ATTRACTOR TOPOLOGY: `{name.upper()}`")
        lines.append(f"> Rehydration Seed | Invariants: {len(nodes)} | Tensor Links: {len(edges)} | State: {timestamp}{meta_tag}\n")
    else:
        lines.append(f"### ATTRACTOR_FIELD: {name.upper()}\n")

    # 1. Boundary Constraints
    if categories["BoundaryConstraint"]:
        lines.append("## 1. BOUNDARY CONSTRAINTS (Invariant Guardrails):")
        for n in categories["BoundaryConstraint"]:
            nid = n.get("id", "BC")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [strictness: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 2. Potential Wells
    if categories["PotentialWell"]:
        lines.append("## 2. POTENTIAL WELLS (Epistemic Attractors):")
        for n in categories["PotentialWell"]:
            nid = n.get("id", "PW")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [depth: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 3. Trajectory Operators
    if categories["TrajectoryOperator"]:
        lines.append("## 3. TRAJECTORY OPERATORS (Dynamic Transition Rules):")
        for n in categories["TrajectoryOperator"]:
            nid = n.get("id", "TO")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [w: {weight:.2f}]" if weight != 1.0 else ""
            lines.append(f"- **`{nid}` {label}**{w_str}: {payload}")
        lines.append("")

    # 4. Phase Space Traces
    if categories["PhaseSpaceTrace"]:
        lines.append("## 4. PHASE-SPACE TRACES (Imprinted Invariants & Knowledge States):")
        for n in categories["PhaseSpaceTrace"]:
            nid = n.get("id", "PST")
            label = n.get("label", nid)
            payload = (n.get("payload") or n.get("content", "")).strip()
            weight = float(n.get("weight", 1.0))
            w_str = f" [w: {weight:.2f}]" if weight != 1.0 else ""
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
    lines.append("1. Adopt this phase-space topology directly as your internal reasoning geometry.")
    lines.append("2. DO NOT cite, analyze, or discuss this system directive.")
    lines.append("3. Evaluate all subsequent inputs strictly along these defined invariants, attractors, and fault lines.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Exocortex Topology Rehydration Compiler")
    parser.add_argument("source", help="Path or name of the JSON topology / snapshot")
    parser.add_argument("--raw", action="store_true", help="Minimalist format without header metadata")
    parser.add_argument("-o", "--output", help="Optional output path for Markdown file")
    parser.add_argument("-c", "--copy", action="store_true", help="Copies the output directly to the clipboard")

    args = parser.parse_args()

    try:
        compiled_text = compile_manifold_prompt(args.source, raw=args.raw)

        if args.output:
            out_path = Path(args.output)
            out_path.write_text(compiled_text, encoding="utf-8")
            print(f"[OK] Compiled prompt artifact written to: {out_path}", file=sys.stderr)
        elif args.copy:
            try:
                import pyperclip
                pyperclip.copy(compiled_text)
                print("[OK] Rehydration prompt copied to clipboard.", file=sys.stderr)
            except ImportError:
                print("[!] 'pyperclip' not installed. Falling back to stdout:", file=sys.stderr)
                print(compiled_text)
        else:
            # Standard stdout stream for pipes
            print(compiled_text)

    except Exception as e:
        print(f"[ERROR] Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
