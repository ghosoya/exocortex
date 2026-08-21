# 🧠 Exocortex (v1.4.2)

> **Topological Cognitive Substrate & Autopoietic Thinking Partner**
> An open-source, local-first cognition engine featuring dynamic phase-space memory, Model Context Protocol (MCP) integration, and bi-directional Obsidian vault synchronization.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
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

8. **Copy-on-Write Topology Isolation & State Freezing:**
Base blueprints (`topologies/base/`) remain strictly sterile in RAM during sessions. Knowledge artifacts acquired during discourse are dynamically wired into in-memory graphs. The `/freeze [tag]` command creates immutable, versioned JSON and Obsidian Canvas snapshot pairs under `Topologies/snapshots/` and `Canvases/snapshots/`.

9. **Substrate-Independent Rehydration Engine:**
The compiler (`core/compiler.py`) transforms frozen topological graph states into compact, token-efficient Markdown attractor prompts (< 350 tokens). These prompts can be piped directly into any local LLM (`ollama run`) or external API interface, transferring exact epistemic constraints without state leakage.

---

## ⚡ Topologies (Hot-Swappable Kognitionsräume)

Switch active topologies on-the-fly via `/graph <name>`:

| Topology | Focus | Target Dynamics |
| :--- | :--- | :--- |
| **`default`** | Minimal Epistemic Setup | Fast start, baseline reasoning, initial attractor calibration |
| **`systemic_kernel`** | Epistemic Rigor & Systems Theory | Falsification audits, Kolmogorov complexity reduction, anti-sycophancy |
| **`code_architect`** | Modular Software Architecture | Decoupling, bounded contexts, idempotency, side-effect isolation |
| **`regional_shojin`** | Mindful Culinary Aesthetics | Micro-seasonality, zero-waste ahimsa, texture/flavor harmony ($5 \times 5 \times 5$) |
| **`poetic_synthesis`** | Divergent Associative Reasoning | Cross-domain bisociation, defamiliarization (*Ostranenie*), structural isomorphism |

---

## 📁 Repository Structure

```text
exocortex/
├── config/
│   └── system_base.md           # Global cognitive base instructions
├── core/
│   ├── compiler.py              # Rehydration engine (JSON topology -> Markdown prompt)
│   ├── config.py                # Typed settings & environment loader
│   ├── engine.py                # ReAct loop and decoupled tool dispatching
│   ├── guards.py                # Context pruning & embedding guards
│   ├── prompts.py               # Cognitive lenses & prompt manager
│   └── session.py               # Session state, token tracking & persistence
├── docs/
│   └── topologies/              # Topological case studies & epistemic audit reports
│       ├── 01_code_architect_entropy_breakline.md
│       ├── 02_poetic_synthesis_anicca_gc.md
│       ├── 03_systemic_kernel_observer_collapse.md
│       ├── 04_systemic_kernel_jevons_verification_entropy.md
│       ├── 05_systemic_kernel_thermodynamic_decoupling.md
│       └── 06_regional_shojin_terroir_synthesis.md
├── server/
│   ├── exocortex_mcp_server.py  # FastMCP SSE / stdio daemon
│   ├── graph_store.py           # NetworkX topology, vector resonance & Canvas generator
│   └── vault_io.py              # Sandboxed filesystem & vault I/O
├── topologies/
│   ├── base/                    # Immutable cognitive blueprints (default, code_architect, ...)
│   └── snapshots/               # Frozen, versioned phase-space states (*.json)
├── chat_exocortex.py            # Unified interactive CLI runner (Local & Remote)
├── test_exocortex.py            # Modular unit & integration test suite
├── test_mcp_network.py          # Network MCP integration test
├── .env.example                 # Environment configuration template
├── LICENSE                      # Apache 2.0 License
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

The `topologies/` directory in the repository provides base templates and reference snapshots. Initialize your vault's directory structure:

```bash
mkdir -p ~/Vaults/exocortex/Topologies/{base,snapshots}
mkdir -p ~/Vaults/exocortex/Canvases/snapshots

cp -r topologies/* ~/Vaults/exocortex/Topologies/
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
python -m server.exocortex_mcp_server --host 127.0.0.1 --port 8000

```

Connect via CLI runner:

```bash
python chat_exocortex.py --remote

```

### Substrate Rehydration & Shell Pipes

Compile any frozen snapshot directly into a lightweight attractor prompt or pipe it straight into a stateless LLM runner:

```bash
# 1. Output compiled attractor prompt to stdout
python -m core.compiler 20260821_080324_code_architect_monolith_vs_microservices

# 2. Pipe phase-space state directly into a fresh Ollama instance
python -m core.compiler 20260821_080324_code_architect_monolith_vs_microservices | ollama run gemma4:12b "Evaluate payment boundary extraction against the entropy breakline."

# 3. Copy attractor directly to system clipboard
python -m core.compiler 20260821_080324_code_architect_monolith_vs_microservices --copy
```
---

## 🛠️ CLI Slash Commands

| Command | Description |
| :--- | :--- |
| `/prompt [list\|set\|show\|reset]` | Manages cognitive profiles and lenses. |
| `/graph` | Displays active topology name, node distribution, and edge counts. |
| `/graph <name>` | Loads base blueprint or frozen snapshot (Local Mode). |
| `/switch <name>` | Switches active topology on remote daemon (Remote Mode). |
| **`/freeze [tag]`** | **Freezes active phase-space state into versioned JSON snapshot & Canvas.** |
| `/save [name]` | Persists session transcript simultaneously as Markdown note and JSON state. |
| `/load [name]` | Restores or lists saved sessions. |
| `/context` | Shows estimated token utilization and turn count. |
| `/clear` | Clears conversation history. |
| `exit` | Closes the session. |

---

## 📚 Topological Case Studies

* **[Showcase 01: Code Architect & The Entropy Breakline](docs/topologies/01_code_architect_entropy_breakline.md)** 
  *Audit of Monolith vs. Microservices trade-offs, dynamic tensor-link wiring, collision-safe ID allocation, and cross-model rehydration.*
* **[Showcase 02: Poetic Synthesis & The Anicca–GC Bisociation](docs/topologies/02_poetic_synthesis_anicca_gc.md)** 
  *A/B benchmark against Vanilla Gemma 4 12B demonstrating anti-cliché invariants, structural isomorphism, and process-oriented ontological synthesis.*
* **[Showcase 03: Systemic Kernel & The Observer-Collapse Audit](docs/topologies/03_systemic_kernel_observer_collapse.md)** 
  *A/B benchmark on Second-Order Cybernetics and Goodhart's Law, deconstructing RLHF alignment theater into formal boundary constraints.*
* **[Showcase 04: Systemic Kernel & The Jevons Verification Paradox](docs/topologies/04_systemic_kernel_jevons_verification_entropy.md)** 
  *Information-theoretic audit of LLM deployment, modeling the phase transition from generative synthesis to forensic Audit Engineering.*
* **[Showcase 05: Systemic Kernel & The Thermodynamic Decoupling Audit](docs/topologies/05_systemic_kernel_thermodynamic_decoupling.md)** 
  *Non-equilibrium thermodynamic audit of 'Green Growth', demonstrating why digitalization is an entropy relocation rather than dematerialization.
* **[Showcase 06: Regional Shojin & The Brandenburg Terroir Synthesis](docs/topologies/06_regional_shojin_terroir_synthesis.md)** 
  *Aesthetic and micro-seasonal translation of Zen temple cuisine (Ichijū Sansai, Gohō, Mottainai) into the regional terroir of Central Europe.*
  
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

## 🔬 Disclaimer

Exocortex is experimental software provided for research and personal 
knowledge exploration on an "AS IS" basis. It performs direct file system I/O 
within the configured Obsidian vault. Always maintain independent backups of 
your notes and data. LLM-generated responses should not be treated as 
professional, legal, or medical advice.

## 📜 License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.

