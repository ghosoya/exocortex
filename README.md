# 🧠 Exocortex (v1.5.0)

> **A local-first AI thinking partner and dynamic knowledge graph for Obsidian.**
> Built with Python, FastMCP, NetworkX, and Ollama. Bridges local LLMs with a visual concept graph in your personal vault.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/MCP-FastMCP-brightgreen.svg)](https://modelcontextprotocol.io/)
[![Backend](https://img.shields.io/badge/LLM%20Backend-Ollama-orange.svg)](https://ollama.ai/)
[![Obsidian](https://img.shields.io/badge/Obsidian-Canvas%20Integration-purple.svg)](https://obsidian.md/)

---

## ⚡ What is Exocortex?

Standard LLMs suffer from context limits, flat memory, and sycophancy (agreeing with everything you say). 

**Exocortex** is an open-source companion engine that runs completely offline on your machine. It couples a local LLM with a **directed semantic knowledge graph**. Instead of stuffing thousands of unstructured tokens into the prompt, Exocortex retrieves relevant concepts, rules, and working notes dynamically and projects your current mental model straight into an interactive **Obsidian Canvas**.

```text
                  ┌─────────────────────────────────────┐
                  │            Operator / CLI           │
                  │          (chat_exocortex.py)        │
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
┌──────────────┐              ┌──────────────┐                ┌──────────────┐
│ PromptEngine │              │  GraphStore  │                │   VaultIO    │
│ - default    │              │ - NetworkX   │                │ - Obsidian   │
│ - socratic   │              │ - bge-m3 vec │                │   Scratchpad │
│ - architect  │              │ - .canvas    │                │ - Sessions   │
└──────────────┘              └──────────────┘                └──────────────┘

```

---

## 🛠️ Key Features

1. **Graph-Based Working Memory (NetworkX + Vector Search):**
Long-term concepts and rules are stored in a directed graph. Relevant nodes and their 1-hop semantic links are retrieved via cosine similarity (`bge-m3` embeddings) and injected into the system prompt context per turn.
2. **Real-Time Obsidian Canvas Sync:**
Every graph mutation automatically updates an interactive, color-coded `.canvas` file directly inside your Obsidian vault.

3. **Standardized Node Types & Canonical Prefixes:**

* 🔴 **Constraints (`CST_`):** Inviolable guardrails and invariants (e.g. pure functional boundaries, anti-sycophancy, side-effect isolation).
* 🔵 **Concepts (`CNC_`):** Foundational domain definitions, architectural models, and ground-truth axioms.
* 🟣 **Rules (`RUL_`):** Concrete action guidelines, refactoring heuristics, and operational procedures.
* 🟢 **States (`STA_`):** Ephemeral hypotheses, task traces, and active session checkpoints.

4. **Prompt Compiler & Snapshot Freezing:**
Export any active graph topology into a compact, token-efficient Markdown system prompt (< 350 tokens) that can be piped into any local LLM, script, or CI pipeline.

5. **Experimental Anti-Sycophancy Telemetry (Echo & Epistemic Lift):**
Diagnostic runtime heuristics computed after each turn to detect conversational mirroring and verify factual grounding against graph principles:

- **Echo Score ($\rho_{\text{echo}}$):** Tracks prompt-to-response cosine similarity. Flags passive parroting (> 0.85) versus healthy critical distance (0.50–0.70).
- **Epistemic Lift ($\Delta E$):** Measures whether the model's response actively converges toward retrieved ground-truth nodes rather than floating off into unconstrained generation.

6. **Dual-Mode Operation:**

* **Local CLI:** Fast, zero-overhead terminal runner for daily sparring and note-taking.
* **Remote FastMCP Server:** Exposes 11 canonical MCP tools over SSE to Claude Desktop, IDE extensions, or custom agents.

---

## 🚀 Quickstart

### 1. Prerequisites

* **Python 3.10+**
* **Ollama** installed and running locally:
```bash
ollama pull gemma4:12b
ollama pull bge-m3

```


* *(Optional)* **Obsidian** to view the generated Canvas files.

### 2. Installation

```bash
git clone https://github.com/ghosoya/exocortex.git
cd exocortex

python3 -m venv .venv
source .venv/bin/activate
pip install ollama networkx mcp python-dotenv prompt_toolkit

```

### 3. Configuration

```bash
cp .env.example .env

```

Set your Obsidian vault path in `.env`:

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

Initialize your vault directories:

```bash
mkdir -p ~/Vaults/exocortex/{Topologies/{base,snapshots},Canvases/snapshots,Scratchpad,Sessions}
cp -r topologies/base/* ~/Vaults/exocortex/Topologies/base/

```

---

## 💻 Usage

### Interactive Terminal Chat (Local)

```bash
python chat_exocortex.py

```

### Run as FastMCP Server (Remote)

```bash
# Start server
python -m server.exocortex_mcp_server --host 127.0.0.1 --port 8000

# Connect via CLI
python chat_exocortex.py --remote

```

### Pipe Compiled Context into Ollama

```bash
# Compile a graph and pipe it directly into a fresh Ollama run:
python -m core.compiler software_design | ollama run gemma4:12b "Analyze this service interface"

```

---

## ⌨️ Useful Commands in Chat

* `/graph` — Display active topology name, node count, and edge count.
* `/graph <name>` — Switch active topology (e.g. `/graph software_design`).
* `/freeze [tag]` — Freeze current topology into a timestamped JSON snapshot and `.canvas`.
* `/prompt [list|set <profile>]` — Switch cognitive stance (`default`, `socratic`, `architect`).
* `/payload [query]` — Inspect the fully compiled system prompt (base + constraints + context).
* `/context` — Display token usage and message count.
* `/clear` — Clear current conversation history.
* `/help` — Overview of available commands.

---

## 📚 Examples & Benchmarks

To demonstrate that Exocortex is a general-purpose reasoning architecture rather than a software-specific prompt wrapper, the benchmarks in `docs/topologies/` test two fundamentally different domains using the exact same underlying graph schema (`Constraint`, `Concept`, `Rule`, `State`):

* **[Software Design Review](docs/topologies/01_software_design_review.md) (Abstract Engineering):** 
  Enforcing modular boundaries, isolating side effects, and demonstrating autonomous graph mutation when challenging a monolithic "god function" anti-pattern.
* **[Regional Shojin Cooking](docs/topologies/02_regional_shojin_recipe.md) (Sensory & Physical Craft):** 
  Stress-testing domain transfer by mapping traditional Zen culinary philosophy (*Gomi, Goshiki, Goho*) and regional harvest constraints into the graph. Demonstrates automated 1-hop knowledge retrieval (e.g. root-scrap dashi) without direct prompting.
  
---

## 🤝 Collaboration & Genesis

Exocortex is built through iterative collaboration between **Georg Hosoya** (Architecture, Direction & Design) and **Gemini** (Code Synthesis & Implementation).

It demonstrates transparent human–AI engineering: leveraging LLMs for rapid, modular code synthesis while maintaining human architectural control.

---

## 🔬 Disclaimer

Exocortex is experimental software provided for research and personal 
knowledge exploration on an "AS IS" basis. It performs direct file system I/O 
within the configured Obsidian vault. Always maintain independent backups of 
your notes and data. LLM-generated responses should not be treated as 
professional, legal, or medical advice.

---

## 📜 License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.


