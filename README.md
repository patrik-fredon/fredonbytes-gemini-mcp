---
description: 'Official Documentation for Gemini-Copilot MCP Bridge'
version: '1.0'
authority: 'FredonBytes'
license: 'FredonBytes Source License (FBSL) v1.0'
---

# Gemini-Copilot MCP Bridge

[Image of Gemini MCP Architecture Diagram]

**A FredonBytes Production**

The **Gemini-Copilot Bridge** is a high-performance Model Context Protocol (MCP) server that connects **VS Code Copilot Chat** directly to your local **Gemini CLI**.

It enables Copilot to "offload" complex tasks to **Gemini 3 Pro** (Reasoning) or huge context summaries to **Gemini 3 Flash**, all while maintaining strict project context awareness and adhering to local `AGENTS.md` rules.

## ⚡ Core Capabilities

1. **Reasoning Engine**: Access `gemini-3-pro-preview` for complex architecture and refactoring tasks inside VS Code.
2. **Context Optimization**: `smart_context_summary` tool reads files via Gemini Flash and returns only relevant tokens to Copilot, saving context window.
3. **Project Sovereignty**: Automatically detects and enforces `AGENTS.md` rules found in the project root.
4. **YOLO Mode**: Runs in `--yolo` (autonomous) mode for seamless agentic workflows.

## 🛠️ Prerequisites

* **Python**: 3.12+
* **Package Manager**: `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
* **Gemini CLI**: Installed and configured (`npm i -g @google/gemini-cli` or equivalent).
* **API Key**: Configured in `~/.gemini/config.json`.

## 🚀 Installation

### 1. Initialize & Install

```bash
# Clone or create directory
mkdir gemini-copilot-bridge
cd gemini-copilot-bridge

# Initialize with uv
uv init
uv add "mcp[cli]" pydantic

# (Optional) Verify server script presence
# Ensure src/gemini_copilot_mcp/server.py exists with the provided code.
