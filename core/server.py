"""
DesktopCommanderPy - MCP Server initialization and tool registration.

This module creates the FastMCP instance and registers all tools from
the various tool modules. Add new tool modules here as the project grows.
"""

import logging
import platform

from fastmcp import FastMCP

from core.tools.filesystem import (
    read_file,
    write_file,
    search_files,
    edit_file_diff,
    list_directory,
    get_file_info,
    create_directory,
    move_file,
    read_multiple_files,
)
from core.tools.process_sessions import (
    start_process,
    read_process_output,
    interact_with_process,
    list_sessions,
    force_terminate,
)
from core.tools.hana import (
    hana_test_connection,
    hana_execute_query,
    hana_execute_ddl,
    hana_list_schemas,
    hana_list_tables,
    hana_describe_table,
    hana_get_row_count,
    hana_get_system_info,
)
from core.tools.terminal import (
    execute_command,
    execute_command_streaming,
)
from core.tools.process import (
    list_processes,
    kill_process,
)
from core.tools.config_tools import (
    get_config,
    set_config_value,
)

logger = logging.getLogger(__name__)

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
mcp.tool()(create_directory)
mcp.tool()(move_file)
mcp.tool()(read_multiple_files)
mcp.tool()(get_config)
mcp.tool()(set_config_value)

# ---------------------------------------------------------------------------
# Register tools - terminal
# ---------------------------------------------------------------------------
mcp.tool()(execute_command)
mcp.tool()(execute_command_streaming)

# ---------------------------------------------------------------------------
# Register tools - process management (single-shot)
# ---------------------------------------------------------------------------
mcp.tool()(list_processes)
mcp.tool()(kill_process)

# ---------------------------------------------------------------------------
# Register tools - process sessions (stateful / interactive)
# ---------------------------------------------------------------------------
mcp.tool()(start_process)
mcp.tool()(read_process_output)
mcp.tool()(interact_with_process)
mcp.tool()(list_sessions)
mcp.tool()(force_terminate)

# ---------------------------------------------------------------------------
# Register tools - SAP HANA Cloud
# ---------------------------------------------------------------------------
mcp.tool()(hana_test_connection)
mcp.tool()(hana_execute_query)
mcp.tool()(hana_execute_ddl)
mcp.tool()(hana_list_schemas)
mcp.tool()(hana_list_tables)
mcp.tool()(hana_describe_table)
mcp.tool()(hana_get_row_count)
mcp.tool()(hana_get_system_info)


def get_server() -> FastMCP:
    """Return the configured FastMCP server instance."""
    return mcp
