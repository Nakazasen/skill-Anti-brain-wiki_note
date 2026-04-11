# 🧠 Hybrid Anti-Brain-Wiki (Hybrid ABW)

> **Version:** 1.1.0  
> **Tagline:** Elevating AI from "Instant Response" to "Multi-layer Deliberation."

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

**Hybrid ABW** is a knowledge and reasoning architecture for AI Agents, designed to address the biggest challenges in modern LLMs: **Lack of reliable long-term memory and shallow reasoning**.

---

## ✨ Why Hybrid ABW?

Instead of letting AI "hallucinate" answers, Hybrid ABW forces it through a rigorous reasoning framework, cross-checking every claim against verified evidence (Grounding).

### 1. The 4-Layer Memory Architecture
Knowledge is separated into distinct layers for optimized retrieval:
- **Layer 1: Operation Memory** (`.brain/`): Remembers current session context, active tasks, and blockers.
- **Layer 2: Persistent Knowledge** (`wiki/`): Compiled, cited, and verified knowledge. This is your "Eternal Brain."
- **Layer 3: Grounding Engine** (NotebookLM): Connects to deep private data for automated cross-checking.
- **Layer 4: Logic Gap Logging** (`knowledge_gaps.json`): Honestly records what the AI doesn't know, preventing hallucinations.

### 2. Test-Time Compute (TTC) Deliberation Engine
Inspired by modern reinforcement learning and reasoning techniques, Hybrid ABW provides the `/abw-query-deep` command – triggering a 5-pass thinking loop:
1. **Decomposition**: Break the problem into sub-tasks.
2. **Evidence Assembly**: Gather evidence from the Wiki.
3. **Grounding**: Verify via NotebookLM.
4. **Self-Critique**: Score the reasoning (Exit Gate).
5. **Repair**: Fix logic gaps before final delivery.

---

## 🛠️ Installation & Usage (Quick Start)

Designed as a **Global Skill** for the Antigravity IDE, allowing you to carry this brain across any project.

### 1. Install MCP Bridge
Install the required CLI tool:
```powershell
uv tool install notebooklm-mcp-cli
```

### 2. Initialize & Setup
In your IDE, run these two commands:
- `/abw-init`: Scaffolds the standard directory structure (wiki, raw, .brain).
- `/abw-setup`: Interactive wizard for NotebookLM login and connection testing.

### 3. Standard Workflow
1. Drop source files into the `raw/` folder.
2. Run `/abw-ingest` to extract and compile knowledge into the Wiki.
3. Query using `/abw-query` (Fast) or `/abw-query-deep` (Slow/Deep thinking).

---

## 🛡️ Grounding Principles
> **"A cited answer beats a confident guess. A logged gap beats a fake answer."**

The system strictly adheres to the **AGENTS.md** Spec – ensuring every piece of data in the Wiki has a clear provenance chain.

---

## 🤝 Contributing
We welcome contributions to improve the Deliberation Engine and Knowledge Schemas. See [CONTRIBUTING.md](CONTRIBUTING.md).

---
**Developed by Advanced Agentic Coding Team - Google DeepMind.**
*(Note: This is an open-source research and development project.)*
