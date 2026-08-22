"""
server/vault_io.py
Isolated, sandboxed I/O layer for interacting with the Obsidian vault.
Enforces strict path containment, safe fallbacks, and atomic write operations.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import datetime
import json
import os

from core.config import settings


class VaultIO:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = Path(vault_path or settings.vault_path).resolve()
        
        # Topology directory resolution (with legacy fallback to 'graphs')
        topo_name = settings.topologies_dir_name
        if not (self.vault_path / topo_name).exists() and (self.vault_path / "graphs").exists():
            self.graphs_dir = (self.vault_path / "graphs").resolve()
        else:
            self.graphs_dir = (self.vault_path / topo_name).resolve()

        self.topologies_dir = self.graphs_dir  # Uniform alias
        self.sessions_dir = (self.vault_path / settings.sessions_dir_name).resolve()
        self.scratchpad_dir = (self.vault_path / settings.scratchpad_dir_name).resolve()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for directory in [self.graphs_dir, self.sessions_dir, self.scratchpad_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str, base_dir: Optional[Path] = None) -> Path:
        """Resolves path and enforces strict containment within the vault root."""
        target_base = base_dir or self.vault_path
        target_path = (target_base / relative_path).resolve()
        
        try:
            # Enforce that target_path is strictly inside self.vault_path
            target_path.relative_to(self.vault_path)
        except ValueError:
            raise PermissionError(f"Security violation: Path '{relative_path}' escapes the vault boundary.")
        
        return target_path

    def read_note(self, note_name: str) -> str:
        """Reads a note; checks vault root and gracefully falls back to scratchpad."""
        clean_name = note_name if note_name.endswith(".md") else f"{note_name}.md"
        target_path = self._resolve_safe_path(clean_name, base_dir=self.vault_path)
        
        # Fallback: If not found in root, look in scratchpad directory
        if not target_path.exists() and not clean_name.startswith(f"{settings.scratchpad_dir_name}/"):
            fallback_path = self._resolve_safe_path(clean_name, base_dir=self.scratchpad_dir)
            if fallback_path.exists():
                target_path = fallback_path

        if not target_path.exists():
            raise FileNotFoundError(f"Note '{clean_name}' not found in vault: {target_path}")

        return target_path.read_text(encoding="utf-8")

    def append_scratchpad(self, content: str, filename: str = "Active_Scratchpad.md") -> str:
        """Safely appends text content to a scratchpad note."""
        clean_name = filename if filename.endswith(".md") else f"{filename}.md"
        target_path = self._resolve_safe_path(clean_name, base_dir=self.scratchpad_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n## [{ts}]\n{content.strip()}\n"
        
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return str(target_path)

    def read_graph_json(self, graph_name: str) -> Dict[str, Any]:
        """Loads a graph topology as JSON."""
        clean_name = graph_name if graph_name.endswith(".json") else f"{graph_name}.json"
        path = self._resolve_safe_path(clean_name, base_dir=self.graphs_dir)
        if not path.exists():
            raise FileNotFoundError(f"Topology '{graph_name}' not found at {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_graph_json(self, graph_name: str, data: Dict[str, Any]) -> str:
        """Serializes a graph topology atomically as JSON."""
        clean_name = graph_name if graph_name.endswith(".json") else f"{graph_name}.json"
        path = self._resolve_safe_path(clean_name, base_dir=self.graphs_dir)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write pattern via temporary file
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

        return str(path)

    def list_graphs(self) -> List[str]:
        """Lists all available topology files."""
        return sorted([f.stem for f in self.graphs_dir.glob("*.json")])
