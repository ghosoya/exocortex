# 🧠 Exocortex (v1.4.2)

> **Topological Cognitive Substrate & Autopoietic Thinking Partner**
> An open-source, local-first cognition engine featuring dynamic phase-space memory, Model Context Protocol (MCP) integration, and bi-directional Obsidian vault synchronization.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENCE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/MCP-FastMCP-brightgreen.svg)](https://modelcontextprotocol.io/)
[![Backend](https://img.shields.io/badge/LLM%20Backend-Ollama-orange.svg)](https://ollama.ai/)
[![Co-Authored](https://img.shields.io/badge/Co--Authored%20with-Gemini-8E44AD.svg)](https://deepmind.google/technologies/gemini/)

---

## ⚡ Core Architecture

The Exocortex is designed as a persistent, high-density reasoning substrate for the operator. It decouples high-level reasoning from state mutation and integrates topological memory into the LLM context loop.

```text
                  ┌─────────────────────────────────────┐
                  │          Operator / CLI             │
                  │        (chat_exocortex.py)          │
                  └──────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
   [ Embedded Mode ]                                   [ Remote Mode ]
 Direct in-process loop                              FastMCP Client (SSE)
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │    ExecutionEngine (ReAct)   │
                      │  - Context-Aware Assembly    │
                      │  - History Pruning & Guards  │
                      └──────────────┬───────────────┘
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     ▼                               ▼                               ▼
┌──────────────┐             ┌──────────────┐                ┌──────────────┐
│ PromptEngine │             │  GraphStore  │                │   VaultIO    │
│ - default    │             │ - NetworkX   │                │ - Obsidian   │
│ - socratic   │             │ - bge-m3 vec │                │   Scratchpad │
│ - architect  │             │ - .canvas    │                │ - Sessions   │
└──────────────┘             └──────────────┘                └──────────────┘

```

### Key Pillars

1. **Topological Phase Space (NetworkX + Vector Resonance):**
Long-term memory is represented as a directed semantic graph with typed nodes (`BoundaryConstraint`, `PotentialWell`, `TrajectoryOperator`, `PhaseSpaceTrace`). Relevant nodes are retrieved via vector cosine similarity (`bge-m3`) and injected dynamically as system context.

2. **Real-Time Obsidian Canvas Projection:**
Every graph mutation or topology switch automatically writes an interactive, color-coded `.canvas` file directly into your Obsidian vault.


3. **Epistemic Phase Space (Node Taxonomy)**
* **`BoundaryConstraint` (Red):** Inviolable epistemic invariants (Anti-Sycophancy, Side-Effect Isolation, Epistemic Sovereignty).
* **`PotentialWell` (Cyan):** Gravitational attractor states defining the conceptual grounding (First Principles, Domain Contexts, Four-Layer Architecture).
* **`TrajectoryOperator` (Purple):** Directional operators driving transformation, refactoring, and complexity reduction.
* **`PhaseSpaceTrace` (Green):** Transient operational traces representing current execution states, hypotheses, and life cycles.

4. **Synaptic Plasticity & Mutation Actions**
The model or operator can actively reshape the phase space during runtime:
* `STRENGTHEN` / `DECAY`: Relative weight modulation ($\Delta w$).
* `SET_WEIGHT`: Absolute weight calibration ($[0.05, 3.0]$).
* `UPDATE`: Payload rewriting with automatic re-embedding via `bge-m3`.
* `PRUNE`: Topological deletion of obsolete hypothesis traces and redundant vectors.


5. **Dual-Mode Runner:**
* **Local Mode:** Self-contained in-memory execution loop without network overhead.
* **Remote Mode:** Client-server setup via FastMCP over SSE, enabling external agent architectures and remote tool calls.

6. **Cognitive Lenses:**
Runtime-switchable cognitive modes (`default`, `socratic`, `architect`) to adapt the epistemological stance on the fly.
7. **Defensive Guards:**
Automatic token budgeting, code-block stripping for embeddings, and sliding-window turn pruning to avoid context overflow (HTTP 500 mitigation).

---

## ⚡ Topologies (Hot-Swappable Kognitionsräume)

Switch active topologies on-the-fly via `/graph <name>`:

| Topology | Focus | Target Dynamics |
| :--- | :--- | :--- |
| **`default`** | Minimal Epistemic Setup | Fast start, baseline reasoning, initial attractor calibration |
| **`systemic_kernel`** | Epistemic Rigor & Systems Theory | Falsification audits, Kolmogorov complexity reduction, anti-sycophancy |
| **`code_architect`** | Modular Software Architecture | Decoupling, bounded contexts, idempotency, side-effect isolation |

---

## 📁 Repository Structure

```text
exocortex/
├── config/
│   └── system_base.md          # Global cognitive base instructions
├── core/
│   ├── config.py               # Typed settings & environment loader
│   ├── engine.py               # ReAct loop and decoupled tool dispatching
│   ├── guards.py               # Context pruning & embedding guards
│   ├── prompts.py              # Cognitive lenses & prompt manager
│   └── session.py              # Session state, token tracking & persistence
├── server/
│   ├── exocortex_mcp_server.py # FastMCP SSE / stdio daemon
│   ├── graph_store.py          # NetworkX topology & Canvas generator
│   └── vault_io.py             # Sandboxed filesystem & vault I/O
├── topologies/
│   └── code_architect.json     # Modular software architecture
│   ├── default.json            # Canonical starter topology (template)
│   └── systemic_kernel.json    # Epistemic rigor & systems theory
├── chat_exocortex.py           # Unified interactive CLI runner
├── test_exocortex.py           # Modular unit & integration test suite
├── test_mcp_network.py         # Network MCP integration test
├── .env.example                # Environment configuration template
├── LICENCE                     # Apache 2.0 License
└── README.md

```

---

## 🚀 Quickstart

### 1. Prerequisites

* **Python 3.10+**
* **Ollama** installed and running locally:
```bash
ollama pull gemma4:12b
ollama pull bge-m3

```


* *(Optional)* **Obsidian** for visual graph exploration via Canvas.

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/ghosoya/exocortex.git
cd exocortex

python3 -m venv .venv
source .venv/bin/activate
pip install ollama networkx mcp python-dotenv prompt_toolkit

```

### 3. Configuration

Copy `.env.example` to `.env` and set your vault path:

```bash
cp .env.example .env

```

Edit `.env`:

```ini
EXOCORTEX_VAULT_PATH=~/Vaults/exocortex
EXOCORTEX_SCRATCHPAD_DIR=Scratchpad
EXOCORTEX_SESSIONS_DIR=Sessions
EXOCORTEX_TOPOLOGIES_DIR=Topologies

EXOCORTEX_OLLAMA_HOST=http://127.0.0.1:11434
EXOCORTEX_CHAT_MODEL=gemma4:12b
EXOCORTEX_EMBEDDING_MODEL=bge-m3
EXOCORTEX_NUM_CTX=65536

```

### 4. Setup Starter Topology

The `topologies/` directory in the repository provides base templates. Initialize your vault's `Topologies/` directory with the default topology:

```bash
mkdir -p ~/Vaults/exocortex/Topologies
cp topologies/default.json ~/Vaults/exocortex/Topologies/default.json

```

---

## 💻 Usage

### Local Interactive CLI

Launch the embedded runner:

```bash
python chat_exocortex.py

```

### Remote MCP Server Daemon

Start the FastMCP daemon in SSE mode:

```bash
python server/exocortex_mcp_server.py --host 127.0.0.1 --port 8000

```

Connect via CLI runner:

```bash
python chat_exocortex.py --remote

```

---

## 🛠️ CLI Slash Commands

| Command | Description |
| --- | --- |
| `/prompt list` | Lists all available cognitive lenses (`default`, `socratic`, `architect`). |
| `/prompt set <lens>` | Activates a specific cognitive lens. |
| `/prompt show` | Displays the active base system prompt. |
| `/graph` | Displays active topology name, node distribution, and edge counts. |
| `/graph <name>` | Switches active topology and synchronizes Canvas. |
| `/save [name]` | Persists session simultaneously as Markdown note and JSON state. |
| `/load [name]` | Restores or lists saved sessions. |
| `/context` | Shows estimated token utilization and turn count. |
| `/clear` | Clears conversation history. |
| `exit` | Closes the session. |

---

## 🧪 Testing

Run the automated unit test suite:

```bash
python test_exocortex.py

```

Run the remote MCP network verification:

```bash
python test_mcp_network.py

```

## 🤝 Genesis & Collaboration

Exocortex is engineered through a continuous, autopoietic human–AI collaboration between **Georg Hosoya** (System Architecture & Conceptual Framing) and **Gemini** (Substrate Implementation, Formal Verification & Refactoring). 

It stands as a live demonstration of symbiotic cognition and high-density technical resonance.

---

## 📜 License

Licensed under the **Apache License, Version 2.0**. See [LICENCE](LICENCE) for details.

