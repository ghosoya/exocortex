# 🧠 Exocortex (v1.4.8)

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
Long-term concepts and rules are stored in a directed graph. Relevant nodes are retrieved via cosine similarity (`bge-m3` embeddings) and injected into the prompt context when needed.
2. **Real-Time Obsidian Canvas Sync:**
Every graph update automatically writes an interactive, color-coded `.canvas` file directly into your Obsidian vault.
3. **Structured Node Types:**
* 🔴 **Guardrails / Rules:** Hard constraints (e.g., anti-sycophancy, modular code design, verification criteria).
* 🔵 **Core Concepts:** Foundational domain definitions and reference knowledge.
* 🟣 **Action Guidelines:** Heuristics and workflows for refactoring, analysis, or critique.
* 🟢 **Working Notes:** Ephemeral session notes, active hypotheses, and task traces.


4. **Prompt Compiler & Snapshot Freezing:**
Export any frozen graph state into a compact, token-efficient Markdown system prompt (< 350 tokens) that can be piped into any local LLM or API.
5. **Anti-Sycophancy Telemetry:**
Measures semantic drift and prompt mirroring live after each turn to ensure the model acts as a rigorous sparring partner rather than a sycophantic echo chamber.
6. **Dual-Mode Operation:**
* **Local CLI:** Fast, self-contained terminal interface for daily writing and thinking.
* **Remote MCP Server:** FastMCP daemon exposing tools over SSE to Claude Desktop or external agents.



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
EXOCORTEX_VAULT_PATH=~/Vaults/my-vault
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
mkdir -p ~/Vaults/my-vault/Topologies/{base,snapshots}
mkdir -p ~/Vaults/my-vault/Canvases/snapshots
cp -r topologies/* ~/Vaults/my-vault/Topologies/

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
# Compile a graph snapshot and pipe it directly into a fresh Ollama run:
python -m core.compiler my_snapshot_name | ollama run gemma4:12b "Analyze this architecture"

```

---

## ⌨️ Useful Commands in Chat

* `/graph` — Show current graph statistics (nodes, connections).
* `/graph <name>` — Load a graph preset or saved snapshot.
* `/freeze [tag]` — Save current graph state as JSON and an Obsidian `.canvas` file.
* `/prompt [list|set]` — Switch cognitive mode (`default`, `socratic`, `architect`).
* `/context` — Check token count and context window usage.
* `/clear` — Reset active conversation history.
* `/help` — Shows available commands.
---

## 📚 Examples & Benchmarks

Practical evaluations and CLI session benchmarks demonstrating graph memory and anti-sycophancy guardrails are available in `docs/topologies/`:

* **[Software Design Review](docs/topologies/01_software_design_review.md)** — Preventing monolithic "god functions", isolating side effects, and enforcing modular boundaries.
* **[Regional Shojin Cooking](docs/topologies/02_regional_shojin_recipe.md)** — Applying structured graph constraints to seasonal cooking, texture pairing, and zero-waste preparation.
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


