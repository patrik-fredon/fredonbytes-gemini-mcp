import os
import shutil
from pathlib import Path

def create_sandbox():
    """Creates a temporary sandbox environment for MCP testing."""
    root = Path("./test_playground")
    
    if root.exists():
        shutil.rmtree(root)
    
    root.mkdir()
    
    # 1. Dummy Python File (Logic)
    (root / "calculator.py").write_text("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def complex_logic(x, y):
    # This function contains a deliberate bug for reasoning testing
    return (x * y) / (x - x)
""")

    # 2. Dummy Markdown (Context)
    (root / "README.md").write_text("""
# Test Project
This is a generated sandbox for Gemini MCP testing.
The calculator.py contains a fibonacci sequence and a buggy function.
""")

    # 3. Dummy Config (Hidden file)
    (root / ".env.example").write_text("API_KEY=123456")

    print(f"✅ Sandbox created at: {root.absolute()}")
    print("👉 ACTION: Open this folder in VS Code to test context indexing.")

if __name__ == "__main__":
    create_sandbox()
