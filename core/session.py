"""
core/session.py
Kapselung des Session-Zustands, Verlaufshistorie und Vault-Persistenz.
"""

from typing import Any, Dict, List, Optional
import datetime
import json
from pathlib import Path

from server.vault_io import VaultIO
from .guards import calculate_history_tokens


class SessionManager:
    def __init__(self, session_name: str = "systemic", vault_io: Optional[VaultIO] = None):
        self.vault_io = vault_io or VaultIO()
        self.session_name = session_name
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.datetime.now().isoformat()
        self.active_graph: str = "default"

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_response(self, content: str) -> None:
        self.messages.append({"role": "tool", "content": content})

    def clear(self) -> None:
        self.messages.clear()

    def get_token_usage(self) -> Dict[str, Any]:
        count = calculate_history_tokens(self.messages)
        return {
            "estimated_tokens": count,
            "message_count": len(self.messages),
            "session_name": self.session_name,
        }

    def save_session(self, target_name: Optional[str] = None) -> Dict[str, str]:
        """Speichert die Session synchron als Markdown-Notiz und JSON-State."""
        name = target_name or self.session_name
        self.session_name = name
        timestamp_human = datetime.datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        # 1. Markdown Export für Obsidian
        md_lines = [
            f"# 🧠 Exocortex Session: {name}",
            f"**Datum:** {timestamp_human} | **Graph:** `{self.active_graph}` | **Nachrichten:** `{len(self.messages)}`\n",
            "---\n",
        ]

        for msg in self.messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                md_lines.append(f"### 👤 Georg\n\n{content}\n\n---")
            elif role == "assistant" and content:
                md_lines.append(f"### ⚡ Exocortex\n\n{content}\n\n---")

        md_path = self.vault_io.sessions_dir / f"{name}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        # 2. JSON State Export (für vollständige Rekonstruktion)
        state_data = {
            "session_name": name,
            "saved_at": datetime.datetime.now().isoformat(),
            "active_graph": self.active_graph,
            "messages": self.messages,
        }
        json_path = self.vault_io.sessions_dir / f"{name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

        return {"markdown": str(md_path), "json": str(json_path)}

    def load_session(self, name: str) -> Dict[str, Any]:
        """Lädt den vollständigen Zustand einer Session aus dem JSON-State."""
        json_path = self.vault_io.sessions_dir / f"{name}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Keine Session-Datei '{name}.json' in {self.vault_io.sessions_dir} gefunden.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.session_name = data.get("session_name", name)
        self.active_graph = data.get("active_graph", "default")
        self.messages = data.get("messages", [])
        return data
