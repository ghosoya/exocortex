"""
scripts/migrate_v1_5.py
Deterministic migration script for Exocortex v1.5.0:
- Node Types: BoundaryConstraint -> Constraint, PotentialWell -> Concept, etc.
- Node ID Prefixes: BC_ -> CST_, PW_ -> CNC_, TO_ -> RUL_, PST_ -> STA_
- Edge Relations: tensor_link -> relates_to
"""

from pathlib import Path
import json
import re
import sys

# Typ- und Präfix-Mappings
TYPE_MAP = {
    "BoundaryConstraint": "Constraint",
    "PotentialWell": "Concept",
    "TrajectoryOperator": "Rule",
    "PhaseSpaceTrace": "State",
}

PREFIX_MAP = {
    "BC_": "CST_",
    "PW_": "CNC_",
    "TO_": "RUL_",
    "PST_": "STA_",
}


def remap_id(node_id: str) -> str:
    for old_pre, new_pre in PREFIX_MAP.items():
        if node_id.startswith(old_pre):
            return f"{new_pre}{node_id[len(old_pre):]}"
    return node_id


def migrate_topology_dict(data: dict) -> tuple[dict, int]:
    mutations = 0

    # 1. Deklarative Keys umbenennen, falls vorhanden
    key_renames = {
        "boundary_constraints": "constraints",
        "potential_wells": "concepts",
        "trajectory_operators": "rules",
        "phase_space_traces": "states",
    }
    for old_k, new_k in key_renames.items():
        if old_k in data:
            data[new_k] = data.pop(old_k)
            mutations += 1

    # 2. Graph Export Format ('nodes' und 'edges' / 'links')
    id_translation: dict[str, str] = {}

    nodes = data.get("nodes", [])
    if isinstance(nodes, list):
        for node in nodes:
            old_id = str(node.get("id", ""))
            new_id = remap_id(old_id)
            if old_id != new_id:
                node["id"] = new_id
                id_translation[old_id] = new_id
                mutations += 1

            old_type = node.get("type", "")
            if old_type in TYPE_MAP:
                node["type"] = TYPE_MAP[old_type]
                mutations += 1

    # Kanten aktualisieren (source/target IDs und Relations)
    edges = data.get("edges") or data.get("links") or []
    if isinstance(edges, list):
        for edge in edges:
            src = str(edge.get("source", ""))
            tgt = str(edge.get("target", ""))

            if src in id_translation:
                edge["source"] = id_translation[src]
                mutations += 1
            if tgt in id_translation:
                edge["target"] = id_translation[tgt]
                mutations += 1

            if edge.get("relation") == "tensor_link":
                edge["relation"] = "relates_to"
                mutations += 1

    return data, mutations


def migrate_directory(target_dir: Path, dry_run: bool = False):
    if not target_dir.exists():
        print(f"[!] Directory not found: {target_dir}")
        return

    json_files = list(target_dir.glob("*.json"))
    if not json_files:
        print(f"[-] No JSON files in {target_dir}")
        return

    print(f"\nScanning: {target_dir} ({len(json_files)} files)")

    for path in sorted(json_files):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            migrated_data, count = migrate_topology_dict(data)

            if count > 0:
                print(f"  [MIGRATE] {path.name}: {count} changes")
                if not dry_run:
                    tmp_path = path.with_suffix(".tmp")
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(migrated_data, f, indent=2, ensure_ascii=False)
                    tmp_path.replace(path)
            else:
                print(f"  [OK]      {path.name}: already compliant")

        except Exception as e:
            print(f"  [ERROR]   {path.name}: {e}")


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN MODE: No files will be overwritten ===")

    project_root = Path(__file__).resolve().parent.parent
    base_dir = project_root / "topologies" / "base"
    snapshots_dir = project_root / "topologies" / "snapshots"

    migrate_directory(base_dir, dry_run=dry_run)
    migrate_directory(snapshots_dir, dry_run=dry_run)
    print("\nMigration pass completed.")


if __name__ == "__main__":
    main()
