# DesktopCommanderPy

> A secure, extensible MCP Server in Python — your own alternative to Desktop Commander.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What is this?

**DesktopCommanderPy** is a fully custom [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server written in Python that gives Claude (or any MCP-compatible AI) controlled access to your local machine: filesystem, terminal, and process management.

Built as a personal alternative to [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP), this project prioritizes:

- **Security first** — path sandbox, command blacklist, extension restrictions
- **Full ownership** — you read and control every line of code
- **Extensibility** — clean module structure, easy to add new tools
- **Cross-platform** — Windows (PowerShell) primary, Linux/macOS ready

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
│       ├── filesystem.py       # read, write, edit, search, list, info
│       ├── terminal.py         # execute_command, execute_command_streaming
│       ├── process.py          # list_processes, kill_process
│       └── utils.py            # Security helpers, config loader, platform
└── tests/
    └── test_basic.py           # pytest suite
```

---

## Installation

### Requirements

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### With uv (recommended)

```powershell
cd C:\Users\Edu\DesktopCommanderPy
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

### With pip

```powershell
cd C:\Users\Edu\DesktopCommanderPy
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
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
    # ... see full list in the file
```

> ⚠️ **If `allowed_directories` is empty, the sandbox is disabled (dev mode).**  
> Always add your directories before using in production.

---

## Running the server

### stdio mode (for Claude Desktop — default)

```powershell
python main.py
```

### HTTP/SSE mode (for remote clients or testing)

```powershell
python main.py --http --port 8080
```

---

## Configuring in Claude Desktop

Add this to your `claude_desktop_config.json`  
(usually at `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "DesktopCommanderPy": {
      "command": "C:\\Users\\Edu\\DesktopCommanderPy\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\DesktopCommanderPy\\main.py"],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Restart Claude Desktop after saving the config.

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
pytest tests/ -v
```

---

## Collaborating with Multiple AIs

This server is designed to work with **any MCP-compatible client**:

- **Claude Desktop** — primary use case (stdio transport)
- **Gemini CLI** — configure in MCP settings, use HTTP transport
- **Custom agents** — point any MCP client at `http://127.0.0.1:8080`

For multi-AI setups, run the server in HTTP mode and configure each
client to connect to the same endpoint.

---

## Roadmap

- [ ] `create_directory` tool
- [ ] Clipboard read/write tool
- [ ] Audit log (every operation logged with timestamp + caller)
- [ ] Per-tool directory restrictions
- [ ] Android/iOS companion via HTTP transport
- [ ] SAP-specific tools (RFC calls, transport management)

---

## License

MIT — do whatever you want, just keep the copyright notice.
