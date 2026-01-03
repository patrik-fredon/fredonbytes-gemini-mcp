# 2. `COPILOT_INSTRUCTIONS.md` (Settings Injection)

Add these instructions to your VS Code settings to ensure Copilot knows how to drive this specific MCP server.

**File:** `.vscode/settings.json` (Workspace) OR Global User Settings.

```json
"github.copilot.chat.codeGeneration.instructions": [
    {
        "text": "GEMINI BRIDGE PROTOCOL:\n1. ALWAYS begin a session involving '@gemini-bridge' by calling the 'initialize_gemini_bridge' tool. Pass the absolute path of the current ${workspaceFolder}.\n2. FOR COMPLEX LOGIC: Explicitly use 'model='gemini-3-pro-preview'' in the 'ask_gemini' tool when the user asks for 'reasoning', 'architecture', or 'deep thought'.\n3. FOR LARGE FILES: If the user adds many files to context, suggest using 'smart_context_summary' to save context window tokens.\n4. AGENTS.MD: The server automatically injects project rules. Do not manually read AGENTS.md unless asked."
    }
]
