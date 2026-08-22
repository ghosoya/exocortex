"""
core/config.py
Central configuration module for Exocortex.
Loads environment variables / .env and provides typed, fail-safe settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any

# Resolve repository root anchor
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Attempt to load python-dotenv if installed
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


def _safe_int(env_var: str, default: int) -> int:
    """Safely cast environment variables to integer with fallback."""
    val = os.getenv(env_var)
    if val is None or not val.strip():
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class ExocortexConfig:
    # Project Root Anchor
    project_root: Path = PROJECT_ROOT

    # Vault & File Paths
    vault_path: Path = Path(
        os.getenv("EXOCORTEX_VAULT_PATH", str(Path.home() / "Daten" / "Vaults" / "exocortex"))
    ).expanduser().resolve()

    scratchpad_dir_name: str = os.getenv("EXOCORTEX_SCRATCHPAD_DIR", "Scratchpad")
    sessions_dir_name: str = os.getenv("EXOCORTEX_SESSIONS_DIR", "Sessions")
    topologies_dir_name: str = os.getenv("EXOCORTEX_TOPOLOGIES_DIR", "Topologies")

    # LLM & Embedding Settings
    ollama_host: str = os.getenv("EXOCORTEX_OLLAMA_HOST", "http://127.0.0.1:11434")
    chat_model: str = os.getenv("EXOCORTEX_CHAT_MODEL", "gemma4:12b")
    embedding_model: str = os.getenv("EXOCORTEX_EMBEDDING_MODEL", "bge-m3")
    context_window: int = _safe_int("EXOCORTEX_NUM_CTX", 65536)

    # Server / Network Settings
    mcp_host: str = os.getenv("EXOCORTEX_MCP_HOST", "127.0.0.1")
    mcp_port: int = _safe_int("EXOCORTEX_MCP_PORT", 8000)

    # Derived Vault Paths
    @property
    def scratchpad_path(self) -> Path:
        return self.vault_path / self.scratchpad_dir_name

    @property
    def sessions_path(self) -> Path:
        return self.vault_path / self.sessions_dir_name

    @property
    def topologies_path(self) -> Path:
        return self.vault_path / self.topologies_dir_name


# Global singleton instance for convenient import
settings = ExocortexConfig()
