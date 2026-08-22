"""
core/session.py
Encapsulation of session state, message history, and vault persistence.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import datetime
import json
import re

from server.vault_io import VaultIO
from .guards import calculate_history_tokens


def _sanitize_filename(name: str) -> str:
    """Strips path traversal components and illegal filesystem characters."""
    clean = Path(name).name
    clean = re.sub(r'[^\w\-_\.]', '_', clean)
    return clean.strip("._") or "session_unnamed"


class SessionManager:
    def __init__(self, session_name: str = "systemic", vault_io: Optional[VaultIO] = None):
        self.vault_io = vault_io or VaultIO()
        self.session_name = _sanitize_filename(session_name)
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.datetime.now().isoformat()
        self.active_graph: str = "default"

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content or ""})

    def add_assistant_message(self, content: Optional[str], tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        msg: Dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_response(self, content: str) -> None:
        self.messages.append({"role": "tool", "content": str(content)})

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
        """Synchronously persists the session as a Markdown note and JSON state."""
        name = _sanitize_filename(target_name or self.session_name)
        self.session_name = name
        timestamp_human = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure persistence directory exists
        self.vault_io.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 1. Markdown export for Obsidian
        md_lines = [
            f"# 🧠 Exocortex Session: {name}",
            f"**Date:** {timestamp_human} | **Graph:** `{self.active_graph}` | **Messages:** `{len(self.messages)}`\n",
            "---\n",
        ]

        for msg in self.messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "user":
                md_lines.append(f"### 👤 Operator\n\n{content}\n\n---")
            elif role == "assistant" and content:
                md_lines.append(f"### ⚡ Exocortex\n\n{content}\n\n---")
            elif role == "tool":
                md_lines.append(f"### 🔧 Tool Output\n\n```text\n{content}\n```\n\n---")

        md_path = self.vault_io.sessions_dir / f"{name}.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        # 2. JSON state export (for complete session rehydration)
        state_data = {
            "session_name": name,
            "saved_at": datetime.datetime.now().isoformat(),
            "active_graph": self.active_graph,
            "messages": self.messages,
        }
        json_path = self.vault_io.sessions_dir / f"{name}.json"
        json_path.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"markdown": str(md_path), "json": str(json_path)}

    def load_session(self, name: str) -> Dict[str, Any]:
        """Loads the complete session state from a JSON state file safely."""
        safe_name = _sanitize_filename(name)
        json_path = self.vault_io.sessions_dir / f"{safe_name}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"No session file '{safe_name}.json' found in {self.vault_io.sessions_dir}.")

        try:
            raw_content = json_path.read_text(encoding="utf-8")
            data = json.loads(raw_content)
        except json.JSONDecodeError as jde:
            raise ValueError(f"Corrupted session file '{json_path}' at line {jde.lineno}: {jde.msg}")

        self.session_name = data.get("session_name", safe_name)
        self.active_graph = data.get("active_graph", "default")
        self.messages = data.get("messages", [])
        return data
