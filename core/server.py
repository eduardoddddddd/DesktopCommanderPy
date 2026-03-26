"""
DesktopCommanderPy - MCP Server initialization and tool registration.

This module creates the FastMCP instance and registers all tools from
the various tool modules. Add new tool modules here as the project grows.
"""

import logging
import platform
from pathlib import Path

from fastmcp import FastMCP

from core.tools.filesystem import (
    read_file,
    write_file,
    search_files,
    edit_file_diff,
    list_directory,
    get_file_info,
)
from core.tools.terminal import (
    execute_command,
    execute_command_streaming,
)
from core.tools.process import (
    list_processes,
    kill_process,
)
from core.tools.utils import load_security_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security config (loaded once at startup)
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent.parent / "config" / "security_config.yaml"
security_config = load_security_config(_CONFIG_PATH)

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="DesktopCommanderPy",
    instructions=(
        "A secure, Python-based MCP server providing filesystem, terminal, "
        "and process management tools. All operations are sandboxed to "
        "allowed directories and filtered against a command blacklist. "
        "Platform: " + platform.system()
    ),
)


# ---------------------------------------------------------------------------
# Register tools - filesystem
# ---------------------------------------------------------------------------
mcp.tool()(read_file)
mcp.tool()(write_file)
mcp.tool()(search_files)
mcp.tool()(edit_file_diff)
mcp.tool()(list_directory)
mcp.tool()(get_file_info)

# ---------------------------------------------------------------------------
# Register tools - terminal
# ---------------------------------------------------------------------------
mcp.tool()(execute_command)
mcp.tool()(execute_command_streaming)

# ---------------------------------------------------------------------------
# Register tools - process management
# ---------------------------------------------------------------------------
mcp.tool()(list_processes)
mcp.tool()(kill_process)


def get_server() -> FastMCP:
    """Return the configured FastMCP server instance."""
    return mcp
