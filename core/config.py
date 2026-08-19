"""
core/config.py
Central configuration module for Exocortex (v1.4.0).
Loads environment variables / .env and provides typed settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass

# Attempt to load python-dotenv if installed; fallback to raw os.environ
try:
    from dotenv import load_dotenv
    # Search for .env in project root
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


@dataclass(frozen=True)
class ExocortexConfig:
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
    context_window: int = int(os.getenv("EXOCORTEX_NUM_CTX", "65536"))

    # Server / Network Settings
    mcp_host: str = os.getenv("EXOCORTEX_MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("EXOCORTEX_MCP_PORT", "8000"))

    # Derived Paths
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
