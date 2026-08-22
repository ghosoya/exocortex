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


def _sanitize_tool_calls(tool_calls: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
    """Converts Ollama ToolCall objects or raw dicts into plain JSON-serializable structures."""
    if not tool_calls:
        return None

    clean_calls = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            clean_calls.append(tc)
        elif hasattr(tc, "model_dump"):  # Pydantic v2
            clean_calls.append(tc.model_dump())
        elif hasattr(tc, "__dict__"):
            clean_calls.append(tc.__dict__)
        else:
            fn = getattr(tc, "function", None)
            if fn:
                fn_name = getattr(fn, "name", "")
                fn_args = getattr(fn, "arguments", {})
                clean_calls.append({
                    "function": {
                        "name": fn_name,
                        "arguments": fn_args if isinstance(fn_args, dict) else str(fn_args)
                    }
                })
            else:
                clean_calls.append({"raw": str(tc)})
    return clean_calls


class SessionManager:
    def __init__(self, session_name: str = "systemic", vault_io: Optional[VaultIO] = None):
        self.vault_io = vault_io or VaultIO()
        self.session_name = _sanitize_filename(session_name)
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.datetime.now().isoformat()
        self.active_graph: str = "default"

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content or ""})

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Any]] = None) -> None:
        msg: Dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = _sanitize_tool_calls(tool_calls)
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
        """Synchronously persists the session as a Markdown note and sanitized JSON state."""
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

        # 2. Defensively sanitized JSON state export
        sanitized_messages = []
        for m in self.messages:
            clean_m = dict(m)
            if clean_m.get("tool_calls"):
                clean_m["tool_calls"] = _sanitize_tool_calls(clean_m["tool_calls"])
            sanitized_messages.append(clean_m)

        state_data = {
            "session_name": name,
            "saved_at": datetime.datetime.now().isoformat(),
            "active_graph": self.active_graph,
            "messages": sanitized_messages,
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
