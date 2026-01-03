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
DEFAULT_MODEL = "gemini-2.5-pro"  # Fallback model
FALLBACK_FLASH_MODEL = "gemini-2.5-flash" # Pro rychlé operace

mcp = FastMCP(SERVER_NAME)

class SessionState:
    """Singleton state management."""
    initialized: bool = False
    cwd: Optional[Path] = None
    agents_rules: Optional[str] = None
    available_gemini_mcps: List[str] = []
    
    # Seznam povolených modelů
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
        # Fallback pro případ, že PATH není načtená správně (např. GUI aplikace na Macu)
        possible_paths = [
            os.path.expanduser("~/.local/bin/gemini"),
            "/usr/local/bin/gemini",
            "/opt/homebrew/bin/gemini"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
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

def _validate_model(requested_model: str, ctx: Context) -> str:
    """Fallback logic: Returns a valid model even if the requested one is wrong."""
    if requested_model in STATE.available_models:
        return requested_model
    
    # Inteligentní fallback
    if "flash" in requested_model.lower():
        fallback = FALLBACK_FLASH_MODEL
    else:
        fallback = DEFAULT_MODEL
        
    # Log warning but continue (don't break the user flow)
    print(f"Warning: Model '{requested_model}' not found. Falling back to '{fallback}'.")
    return fallback

async def _verify_init(ctx: Context):
    if not STATE.initialized:
        # Místo pádu se pokusíme o auto-inicializaci v aktuálním adresáři
        # To je "fail-safe" pro případ, že Copilot zapomene zavolat init
        fallback_cwd = Path.cwd()
        await ctx.warning(f"⚠️ Session not explicitly initialized. Auto-initializing in {fallback_cwd}")
        
        # Provedeme "tichou" inicializaci
        STATE.available_gemini_mcps = _load_config_safely()
        STATE.cwd = fallback_cwd
        STATE.initialized = True

# =============================================================================
# MCP Tools (Robust & Annotated)
# =============================================================================

@mcp.tool()
async def initialize_gemini_bridge(
    cwd: Annotated[str, Field(description="ABSOLUTE PATH to the project root directory (e.g., /Users/me/Projects/MyApp). Copilot: ALWAYS pass '${workspaceFolder}'.")],
    ctx: Context,
) -> str:
    """
    [REQUIRED] Initializes the Gemini Bridge. 
    MUST be called at the start of a session to load AGENTS.md rules.
    """
    global STATE
    root = Path(cwd).resolve()
    
    # Robustnost: Pokud cesta neexistuje, zkusíme ji opravit nebo použijeme cwd
    if not root.exists():
        await ctx.warning(f"Path '{root}' not found. Using current server directory.")
        root = Path.cwd()

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
        f"✅ **Gemini Bridge Active**\n"
        f"📂 Root: `{STATE.cwd}`\n"
        f"🛡️ AGENTS.md: {'Loaded' if STATE.agents_rules else 'None'}\n"
        f"🤖 Default Model: `{DEFAULT_MODEL}`"
    )

@mcp.tool()
async def list_capabilities(ctx: Context) -> str:
    """Lists available Gemini models and tools."""
    await _verify_init(ctx)
    return json.dumps({
        "models": STATE.available_models,
        "default_model": DEFAULT_MODEL,
        "tools": STATE.available_gemini_mcps,
        "policy_active": bool(STATE.agents_rules)
    }, indent=2)

@mcp.tool()
async def ask_gemini(
    prompt: Annotated[str, Field(description="The actual instruction or query for Gemini.")],
    ctx: Context,
    model: Annotated[str, Field(description=f"Model to use. Defaults to '{DEFAULT_MODEL}'.")] = DEFAULT_MODEL,
    system_instruction: Annotated[Optional[str], Field(description="Optional system prompt override.")] = None,
) -> str:
    """
    [MAIN TOOL] Chat with Gemini.
    Handles general queries, reasoning, coding, and architecture.
    Automatically applies AGENTS.md rules.
    """
    await _verify_init(ctx)
    
    # 1. Fallback mechanism for model selection
    safe_model = _validate_model(model, ctx)
    
    executable = _get_gemini_path()
    cmd = [executable, prompt, "--model", safe_model, "--yolo"]
    
    # 2. Inject AGENTS.md rules
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
        await ctx.report_progress(0, 100, f"Thinking ({safe_model})...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
            cwd=str(STATE.cwd) # Vždy běží v kontextu projektu
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            err = stderr.decode().strip()
            return f"❌ Gemini Error: {err}"
            
        return stdout.decode().strip()

    except Exception as e:
        return f"Execution Error: {str(e)}"

@mcp.tool()
async def smart_context_summary(
    target_files: Annotated[List[str], Field(description="List of file paths to summarize.")],
    focus: Annotated[str, Field(description="Specific info to extract (e.g. 'find bug in logic').")],
    ctx: Context,
) -> str:
    """
    [OPTIMIZER] Use this to read large files. Returns only a summary to save context.
    """
    await _verify_init(ctx)
    
    prompt = f"Read files. Extract ONLY info about: '{focus}'. Be concise."
    
    executable = _get_gemini_path()
    # Vždy použijeme Flash pro shrnutí (rychlost/cena)
    cmd = [executable, prompt, "--model", "gemini-2.5-flash", "--yolo"]
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