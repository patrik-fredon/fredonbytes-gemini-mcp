import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Optional, List, Annotated, Any

from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

# =============================================================================
# Configuration
# =============================================================================

SERVER_NAME = "gemini-copilot-bridge"
mcp = FastMCP(SERVER_NAME)

class SessionState:
    """Singleton state management."""
    initialized: bool = False
    cwd: Optional[Path] = None
    agents_rules: Optional[str] = None
    available_gemini_mcps: List[str] = []
    
    # Define models explicitly
    available_models: List[str] = [
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash"
    ]

STATE = SessionState()

# =============================================================================
# Helpers
# =============================================================================

def _get_gemini_path() -> str:
    path = shutil.which("gemini")
    if not path:
        raise FileNotFoundError("Critical: 'gemini' executable not found in PATH.")
    return path

def _load_config_safely() -> List[str]:
    """Load ~/.gemini/config.json safely."""
    paths = [
        Path.home() / ".gemini" / "config.json",
        Path.home() / ".gemini" / "settings.json",
    ]
    mcps = []
    for p in paths:
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                if "mcpServers" in data:
                    mcps.extend(list(data["mcpServers"].keys()))
                break
            except Exception:
                pass
    return mcps

async def _verify_init(ctx: Context):
    if not STATE.initialized:
        await ctx.error("❌ Session NOT initialized.")
        raise RuntimeError("You must call 'initialize_gemini_bridge' first.")

# =============================================================================
# MCP Tools (Using Annotated for Strict Schema)
# =============================================================================

@mcp.tool()
async def initialize_gemini_bridge(
    cwd: Annotated[str, Field(description="ABSOLUTE PATH to the project root directory. Copilot: You MUST pass the ${workspaceFolder} here.")],
    ctx: Context,
) -> str:
    """
    [REQUIRED] Initializes the connection between Copilot and Gemini CLI.
    
    MUST be called at the start of every session.
    1. Sets the working directory for context.
    2. Loads AGENTS.md rules.
    3. Discovers available internal tools.
    """
    global STATE
    root = Path(cwd).resolve()
    
    if not root.exists():
        return f"❌ Error: Path '{root}' does not exist."

    # Load State
    STATE.available_gemini_mcps = _load_config_safely()
    
    agents_file = root / "AGENTS.md"
    if agents_file.exists():
        try:
            STATE.agents_rules = agents_file.read_text("utf-8")
        except Exception:
            STATE.agents_rules = None
    else:
        STATE.agents_rules = None
    
    STATE.cwd = root
    STATE.initialized = True
    
    await ctx.info(f"Initialized in {root}")
    
    return (
        f"✅ **Gemini Bridge Initialized**\n"
        f"- **Root**: `{STATE.cwd}`\n"
        f"- **AGENTS.md**: {'Active 🛡️' if STATE.agents_rules else 'Not found'}\n"
        f"- **Tools**: {', '.join(STATE.available_gemini_mcps) or 'None'}\n"
        f"- **Models**: {', '.join(STATE.available_models)}\n"
    )

@mcp.tool()
async def list_capabilities(
    ctx: Context
) -> str:
    """
    Lists all available Gemini models and internal MCP tools (skills).
    """
    await _verify_init(ctx)
    return json.dumps({
        "models": STATE.available_models,
        "tools": STATE.available_gemini_mcps,
        "policy_active": bool(STATE.agents_rules)
    }, indent=2)

@mcp.tool()
async def ask_gemini(
    prompt: Annotated[str, Field(description="The query or instruction for Gemini.")],
    ctx: Context,
    model: Annotated[str, Field(description="Model to use.")] = "gemini-3-flash-preview",
    system_instruction: Annotated[Optional[str], Field(description="Optional system prompt override.")] = None,
) -> str:
    """
    [MAIN TOOL] Chat with the Gemini CLI.
    
    Automatically enforces project rules (AGENTS.md) and handles yolo mode.
    Use 'gemini-3-pro-preview' for complex logic, 'gemini-3-flash-preview' for speed.
    """
    await _verify_init(ctx)
    executable = _get_gemini_path()
    
    cmd = [executable, prompt, "--model", model, "--yolo"]
    
    # Inject AGENTS.md rules
    sys_prompt = []
    if STATE.agents_rules:
        sys_prompt.append("=== PROJECT RULES (AGENTS.md) ===")
        sys_prompt.append(STATE.agents_rules)
        sys_prompt.append("=== END RULES ===")
    
    if system_instruction:
        sys_prompt.append(system_instruction)
        
    if sys_prompt:
        cmd.extend(["--system", "\n\n".join(sys_prompt)])

    try:
        await ctx.report_progress(0, 100, "Waiting for Gemini...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
            cwd=str(STATE.cwd)
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return f"❌ Error: {stderr.decode().strip()}"
            
        return stdout.decode().strip()

    except Exception as e:
        return f"Execution Error: {str(e)}"

@mcp.tool()
async def smart_context_summary(
    target_files: Annotated[List[str], Field(description="List of file paths to read.")],
    focus: Annotated[str, Field(description="What specific information to extract.")],
    ctx: Context,
) -> str:
    """
    [OPTIMIZER] Reads files and returns ONLY relevant info to save context window.
    """
    await _verify_init(ctx)
    
    # Optimization: Use Flash model explicitly for summarizing
    prompt = f"Read these files. Extract ONLY info regarding: '{focus}'. Concise summary."
    
    executable = _get_gemini_path()
    cmd = [executable, prompt, "--model", "gemini-3-flash-preview", "--yolo"]
    cmd.extend(target_files)
    
    if STATE.agents_rules:
        cmd.extend(["--system", STATE.agents_rules])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(STATE.cwd),
            env=os.environ.copy()
        )
        stdout, _ = await process.communicate()
        return f"💡 **Smart Summary**:\n{stdout.decode().strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
