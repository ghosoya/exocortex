"""
server/vault_io.py
Isolierte, sandboxed I/O-Schicht für die Interaktion mit dem Obsidian-Vault.
"""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import settings


class VaultIO:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = Path(vault_path or settings.vault_path).resolve()
        
        # Topologie-Verzeichnis (aus settings, mit sicherem Fallback auf 'graphs')
        topo_name = settings.topologies_dir_name
        if not (self.vault_path / topo_name).exists() and (self.vault_path / "graphs").exists():
            self.graphs_dir = self.vault_path / "graphs"
        else:
            self.graphs_dir = self.vault_path / topo_name

        self.topologies_dir = self.graphs_dir  # Einheitlicher Alias
        self.sessions_dir = self.vault_path / settings.sessions_dir_name
        self.scratchpad_dir = self.vault_path / settings.scratchpad_dir_name
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for directory in [self.graphs_dir, self.sessions_dir, self.scratchpad_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str, base_dir: Optional[Path] = None) -> Path:
        target_base = base_dir or self.vault_path
        target_path = (target_base / relative_path).resolve()
        if not str(target_path).startswith(str(self.vault_path)):
            raise PermissionError(f"Sicherheitsverletzung: Pfad '{relative_path}' liegt außerhalb des Vaults.")
        return target_path

    def read_note(self, note_name: str) -> str:
        """Liest eine Markdown-Notiz aus dem Vault (mit oder ohne .md Endung)."""
        clean_name = note_name if note_name.endswith(".md") else f"{note_name}.md"
        path = self._resolve_safe_path(clean_name)
        if not path.exists():
            raise FileNotFoundError(f"Notiz '{note_name}' nicht im Vault gefunden: {path}")
        return path.read_text(encoding="utf-8")

    def append_scratchpad(self, content: str, filename: str = "Scratchpad.md") -> str:
        # Garantiert stets die .md Endung im Obsidian Vault
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
            
        target_path = self._resolve_safe_path(self.scratchpad_dir / filename)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n## [{ts}]\n{content.strip()}\n"
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return str(target_path)

    def read_graph_json(self, graph_name: str) -> Dict[str, Any]:
        """Lädt eine Graph-Topologie als JSON."""
        clean_name = graph_name if graph_name.endswith(".json") else f"{graph_name}.json"
        path = self._resolve_safe_path(clean_name, base_dir=self.graphs_dir)
        if not path.exists():
            raise FileNotFoundError(f"Topologie '{graph_name}' nicht gefunden unter {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_graph_json(self, graph_name: str, data: Dict[str, Any]) -> str:
        """Speichert eine Graph-Topologie als JSON."""
        clean_name = graph_name if graph_name.endswith(".json") else f"{graph_name}.json"
        path = self._resolve_safe_path(clean_name, base_dir=self.graphs_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(path)

    def list_graphs(self) -> List[str]:
        """Listet alle verfügbaren Topologie-Dateien auf."""
        return sorted([f.stem for f in self.graphs_dir.glob("*.json")])
