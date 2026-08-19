  # Exocortex (v1.4.0)

> A modular cognitive layer and deterministic substrate connecting Large Language Models with topological knowledge graphs, Obsidian vaults, and cognitive lenses.

Exocortex augments local and remote LLMs (via Ollama or FastMCP) with stateful context topologies, fault-tolerant Markdown/Vault I/O, and specialized cognitive profiles designed to mitigate context-drift and sycophancy.

---

## Key Features

* **Dual-Mode Runner (`chat_exocortex.py`):** Unified interactive CLI supporting direct in-process execution as well as decoupled network operation via FastMCP / Server-Sent Events (SSE).
* **Cognitive Lenses (`PromptManager`):** Dynamic runtime switching of thinking modes (`default`, `socratic`, `architect`) without disrupting the conversation state.
* **Topological Knowledge Graphs (`GraphStore`):** Phase-space analysis and dynamic topological context switching (`/graph load <topology>`).
* **Vault & Scratchpad Integrity (`VaultIO`):** Resilient note reading, append-only scratchpad logging with automatic directory creation (`mkdir -p`), and intelligent path resolution.
* **Cross-Mode Session Hydration:** Seamless transition between local and remote environments with full conversation and token state preservation (`/save`, `/load`).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    chat_exocortex.py                        │
│                 (Unified Terminal Client)                   │
└───────────────┬─────────────────────────────┬───────────────┘
                │ (Local Mode)                │ (Remote Mode: --remote)
                ▼                             ▼
┌──────────────────────────────┐  ┌─────────────────────────────┐
│     core.engine              │  │ server.exocortex_mcp_server │
│  (ExecutionEngine / Local)   │  │   (FastMCP / SSE Daemon)    │
└───────────────┬──────────────┘  └───────────┬─────────────────┘
                │                             │
                └──────────────┬──────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Substrate Layer                       │
│  • core.config (Pydantic Configuration)                     │
│  • core.prompts (Cognitive Profile Manager)                 │
│  • server.graph_store (Network Topology Engine)             │
│  • server.vault_io (Obsidian Vault & Scratchpad I/O)        │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Tool Reference (Model Context Protocol)

The Exocortex FastMCP daemon exposes standard JSON-RPC tools accessible by any MCP-compliant client (Exocortex CLI, Claude Desktop, Cursor, etc.).

| Tool Name | Parameters | Purpose | Output Format |
| :--- | :--- | :--- | :--- |
| `exocortex_temporal_anchor` | `scope` *(str, default: "system")* | Establishes chronological anchoring (ISO-8601, calendar week, system time) to prevent temporal drift. | `<temporal_anchor>` XML block |
| `exocortex_gauge_field` | — | Inspects the currently active graph topology, resonance nodes, and edge connections. | `<gauge_field>` XML representation |
| `append_scratchpad` | `content` *(str)*,<br>`filename` *(str, default: "Active_Scratchpad.md")* | Appends entries with timestamp headers (`## [YYYY-MM-DD HH:MM:SS]`) to the vault's scratchpad directory. Automatically ensures directory creation. | `<scratchpad status='appended' path='...' />` |
| `read_vault_note` | `note_name` *(str)* | Reads Markdown files from the Obsidian vault root with automatic fallback to the `Scratchpad/` subfolder. | `<vault_note path='...'>...</vault_note>` |
| `switch_topology` | `topology_name` *(str)* | Dynamically changes the active knowledge graph loaded in memory. | `<topology_switched name='...' node_count='...' />` |
| `list_topologies` | — | Discovers all available graph topologies stored in the vault. | `<topologies list='...' />` |

---

## Installation & Setup

1. **Clone the repository:**
```bash
   git clone [https://github.com/your-username/exocortex.git](https://github.com/your-username/exocortex.git)
   cd exocortex
```

2. **Create and activate a virtual environment:**
    
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
    
2. **Configure environment variables:**
    
    ```bash
    cp .env.example .env
    ```
    
    Edit `.env` according to your local environment:
    
    ```Ini, TOML
    EXOCORTEX_VAULT_PATH="/home/user/Vaults/exocortex"
    EXOCORTEX_CHAT_MODEL="gemma4:12b"
    EXOCORTEX_CONTEXT_WINDOW=8192
    EXOCORTEX_OLLAMA_HOST="[http://127.0.0.1:11434](http://127.0.0.1:11434)"
    EXOCORTEX_REMOTE_URL="[http://127.0.0.1:8000/sse](http://127.0.0.1:8000/sse)"
    ```
    

## Usage Modes

### 1. Local Mode (Embedded / In-Process)

Runs the cognitive engine locally with direct, in-process access to the Obsidian vault and topological graphs:

```bash
python chat_exocortex.py
```

### 2. Remote Mode (Decoupled FastMCP over SSE)

Run the server daemon as a background service and connect via the dual-mode client:


- **Start the FastMCP Server (Terminal 1):**
    
    ```bash
    python server/exocortex_mcp_server.py
    ```
    
- **Connect the Client (Terminal 2):**
    
    ```bash
    python chat_exocortex.py --remote
    ```


## Interactive Slash-Commands

The CLI runner provides runtime control commands:

|**Command**|**Arguments**|**Function**|
|---|---|---|
|`/prompt`|`list` \| `show` \| `set <profile>`|Inspects or switches cognitive profiles (`default`, `socratic`, `architect`).|
|`/graph`|`list` \| `info` \| `load <name>`|Manages and inspects knowledge graph topologies.|
|`/save`|`<session_name>`|Persists the active session as `.md` and `.json` in the Vault.|
|`/load`|`[session_name]`|Lists available sessions or restores an existing session.|
|`/context`|—|Displays current token consumption and message count.|
|`/clear`|—|Resets conversation history while maintaining active lenses and topology.|
|`/help`|—|Displays the interactive command reference.|

## Epistemic Integrity

Exocortex is intentionally designed to counter sycophantic model alignment and context-drift. By enforcing deterministic tool responses, explicit temporal anchoring, and structured cognitive lenses, it maintains an intellectually honest space for complex systems design and critical reflection.

