# DesktopCommanderPy

> A secure, extensible MCP Server in Python — your own alternative to Desktop Commander.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)
[![FastMCP](https://img.shields.io/badge/fastmcp-3.1.1-orange.svg)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/tests-15%2F15%20passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What is this?

**DesktopCommanderPy** is a fully custom [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
server written in Python that gives Claude (or any MCP-compatible AI) controlled access to your
local machine: filesystem, terminal, and process management.

Built as a personal alternative to [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP),
this project prioritizes:

- **Security first** — path sandbox, command blacklist, extension restrictions
- **Full ownership** — you read and control every line of code
- **Extensibility** — clean module structure, easy to add new tools
- **Cross-platform** — Windows (PowerShell) primary, Linux/macOS ready

---

## Status

| Component | Status |
|-----------|--------|
| Tests | ✅ 15/15 passing |
| Claude Desktop integration | ✅ Connected (verified 2026-03-26) |
| FastMCP version | 3.1.1 |
| Protocol | MCP 2025-11-25 |
| Platform tested | Windows 11 / Python 3.12 |

> **Known gotcha:** FastMCP prints an ASCII banner to stdout by default.
> Claude Desktop speaks strict JSON-RPC over stdout — any non-JSON output corrupts the channel
> and causes the app to hang. Always use `mcp.run(..., show_banner=False)` for stdio transport.
> This is enforced in `main.py` and tested in `TestStdioTransport`.

---

## Project Structure

```
DesktopCommanderPy/
├── main.py                     # Entry point (stdio or HTTP transport)
├── pyproject.toml              # Dependencies and build config
├── config/
│   └── security_config.yaml   # Allowed dirs, blocked commands, limits
├── core/
│   ├── server.py               # FastMCP instance + tool registration
│   └── tools/
│       ├── filesystem.py       # read/write/edit_diff/list/search/get_info
│       ├── terminal.py         # execute_command + streaming
│       ├── process.py          # list_processes + kill_process
│       └── utils.py            # Security helpers, config loader, platform
└── tests/
    └── test_basic.py           # 15 tests: security, filesystem, stdio integrity
```

---

## Installation

### Requirements

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### With pip

```powershell
cd C:\Users\Edu\DesktopCommanderPy
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install pytest pytest-asyncio  # for running tests
```

---

## Configuration

Edit `config/security_config.yaml` before first run:

```yaml
security:
  allowed_directories:
    - "C:/Users/YourName/Documents"
    - "C:/projects"
  blocked_commands:
    - "format"
    - "diskpart"
```

> ⚠️ **If `allowed_directories` is empty, the sandbox is disabled (dev mode).**

---

## Running the server

```powershell
# stdio mode (Claude Desktop)
py main.py

# HTTP/SSE mode (remote clients, Gemini CLI, etc.)
py main.py --http --port 8080

# Debug mode
py main.py --log-level DEBUG
```

---

## Configuring in Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "DesktopCommanderPy": {
      "command": "C:\\Users\\Edu\\DesktopCommanderPy\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\DesktopCommanderPy\\main.py"],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read text file with pagination (offset/length) |
| `write_file` | Write or append to a file |
| `edit_file_diff` | Surgical find/replace editing (diff-based) |
| `list_directory` | List directory contents with sizes |
| `search_files` | Search by name pattern and/or content |
| `get_file_info` | File metadata + content preview |
| `execute_command` | Run a shell command, capture full output |
| `execute_command_streaming` | Run long commands with streamed output |
| `list_processes` | List running processes (filterable, sortable) |
| `kill_process` | Terminate a process by PID |

---

## Running Tests

```powershell
.venv\Scripts\pytest tests/ -v
```

---

## Roadmap

- [ ] `create_directory` tool
- [ ] Clipboard read/write tool
- [ ] Audit log (every operation logged with timestamp)
- [ ] Per-tool directory restrictions
- [ ] HTTP mode auth token for multi-AI setups
- [ ] SAP-specific tools (RFC ping, transport list)

---

## License

MIT — do whatever you want, just keep the copyright notice.
