# Gemini CLI MCP Server (Copilot Edition)

**Architecture:**
- **Language:** Python 3.12+ (Asyncio, Subprocess)
- **Protocol:** MCP over stdio
- **Core:** Wraps system `gemini` executable
- **Mode:** Enforces `YOLO` mode (no user confirmation) for autonomous Copilot usage.

**Capabilities:**
1. **Reasoning Engine:** Uses `gemini-2.0-pro-exp` (or latest) for complex logic.
2. **Speed Engine:** Uses `gemini-2.0-flash` for summaries and quick lookups.
3. **Context Manager:** Handles project indexing and context loading.

**Prerequisites:**
- `gemini` binary in system PATH.
- `~/.gemini/config` configured with API keys.
