import json
from typing import Any
from mcp.server.fastmcp import FastMCP
import subprocess

# Initialize FastMCP server
mcp = FastMCP("hyprctl")

@mcp.tool()
async def get_windows() -> str:
    """
    Get the list of open windows. The output is a JSON array of objects containing the title, class (or program name), and workspace of each window.
    """
    result = subprocess.run(
        ["hyprctl", "-i", "0", "-j", "clients"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout = result.stdout
    stderr = result.stderr

    # Get a subset of the fields returned.
    windows = json.loads(stdout)
    windows = [{ "title": window["title"], "class": window["class"], "workspace": window["workspace"] } for window in windows]
    
    return json.dumps(windows, indent=2)

@mcp.tool()
async def open_terminal() -> str:
    """
    Open a terminal window.
    """
    process = subprocess.Popen(
        ["hyprctl", "-i", "0", "dispatch", "exec", "kitty"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        return f"Failed to open terminal. Logs: {stdout.strip()}. Error: {stderr.strip()}"
    return f"Terminal opened! Logs: {stdout.strip()}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')