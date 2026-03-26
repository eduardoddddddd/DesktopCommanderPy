"""
DesktopCommanderPy - Basic test suite.

Run with: pytest tests/ -v
"""

import os
import tempfile
from pathlib import Path

import pytest

# Patch allowed_directories to temp dir for tests
import core.tools.filesystem as fs_module
import core.tools.utils as utils_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect all security checks to a temp directory."""
    monkeypatch.setattr(fs_module, "_security_config", {
        "security": {
            "allowed_directories": [str(tmp_path)],
            "blocked_commands": ["format", "rm -rf /"],
            "max_file_size_bytes": 10 * 1024 * 1024,
            "max_read_lines": 2000,
            "write_blocked_extensions": [".exe", ".dll"],
        },
        "terminal": {
            "windows_shell": "powershell.exe",
            "linux_shell": "/bin/bash",
            "macos_shell": "/bin/zsh",
            "default_timeout_seconds": 10,
            "max_output_chars": 100_000,
        },
    })
    return tmp_path


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------

class TestPathSecurity:
    def test_allowed_path_passes(self, tmp_allowed: Path):
        result = utils_module.resolve_and_validate_path(
            str(tmp_allowed / "test.txt"),
            [str(tmp_allowed)],
        )
        assert result == (tmp_allowed / "test.txt").resolve()

    def test_path_outside_allowed_raises(self, tmp_allowed: Path):
        with pytest.raises(PermissionError):
            utils_module.resolve_and_validate_path(
                "C:/Windows/System32/evil.dll",
                [str(tmp_allowed)],
            )

    def test_blocked_extension_raises(self, tmp_allowed: Path):
        with pytest.raises(ValueError):
            utils_module.check_extension_allowed(Path("virus.exe"), [".exe", ".dll"])

    def test_safe_extension_passes(self, tmp_allowed: Path):
        # Should not raise
        utils_module.check_extension_allowed(Path("script.py"), [".exe", ".dll"])


class TestCommandSecurity:
    def test_blocked_command_raises(self):
        with pytest.raises(PermissionError):
            utils_module.check_command_allowed("format C:", ["format"])

    def test_safe_command_passes(self):
        # Should not raise
        utils_module.check_command_allowed("Get-Process", ["format", "diskpart"])

    def test_blocked_command_case_insensitive(self):
        with pytest.raises(PermissionError):
            utils_module.check_command_allowed("FORMAT C:", ["format"])


# ---------------------------------------------------------------------------
# Filesystem tools tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFilesystemTools:
    async def test_write_and_read(self, tmp_allowed: Path):
        target = str(tmp_allowed / "hello.txt")
        await fs_module.write_file(target, "line1\nline2\nline3\n")
        content = await fs_module.read_file(target)
        assert "line1" in content
        assert "line3" in content

    async def test_read_pagination(self, tmp_allowed: Path):
        target = str(tmp_allowed / "big.txt")
        await fs_module.write_file(target, "\n".join(f"line{i}" for i in range(100)))
        content = await fs_module.read_file(target, offset=10, length=5)
        assert "line10" in content
        assert "line14" in content
        assert "line15" not in content

    async def test_edit_file_diff(self, tmp_allowed: Path):
        target = str(tmp_allowed / "edit.py")
        await fs_module.write_file(target, "x = 1\ny = 2\n")
        await fs_module.edit_file_diff(target, "x = 1", "x = 99")
        content = await fs_module.read_file(target)
        assert "x = 99" in content
        assert "y = 2" in content

    async def test_edit_file_diff_not_found(self, tmp_allowed: Path):
        target = str(tmp_allowed / "nope.txt")
        await fs_module.write_file(target, "hello world\n")
        with pytest.raises(ValueError, match="not found"):
            await fs_module.edit_file_diff(target, "DOES NOT EXIST", "replacement")

    async def test_list_directory(self, tmp_allowed: Path):
        (tmp_allowed / "a.txt").write_text("a")
        (tmp_allowed / "b.txt").write_text("b")
        result = await fs_module.list_directory(str(tmp_allowed))
        assert "a.txt" in result
        assert "b.txt" in result

    async def test_search_files(self, tmp_allowed: Path):
        (tmp_allowed / "foo.py").write_text("print('hello')")
        (tmp_allowed / "bar.txt").write_text("nothing here")
        result = await fs_module.search_files(str(tmp_allowed), "*.py")
        assert "foo.py" in result
        assert "bar.txt" not in result

    async def test_get_file_info(self, tmp_allowed: Path):
        target = tmp_allowed / "info_test.txt"
        target.write_text("test content")
        info = await fs_module.get_file_info(str(target))
        assert "File" in info
        assert "info_test.txt" in info


# ---------------------------------------------------------------------------
# Stdio transport integrity test
# ---------------------------------------------------------------------------

class TestStdioTransport:
    """
    Ensures the MCP server never emits non-JSON-RPC content to stdout.

    Background: FastMCP prints an ASCII banner to stdout by default.
    Claude Desktop speaks strict JSON-RPC over stdout; any extraneous
    output corrupts the channel and causes the app to hang or fail to
    connect. This test guards against that regression.
    """

    def test_server_stdout_is_clean_on_startup(self, tmp_path: Path):
        """Launch the server process and assert stdout has no banner/garbage."""
        import json
        import subprocess
        import sys
        import time

        python = sys.executable  # use same venv python running pytest
        main_py = Path(__file__).parent.parent / "main.py"

        proc = subprocess.Popen(
            [python, str(main_py)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        # Send a minimal JSON-RPC initialize request
        init_msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0.0"}
            }
        }) + "\n"

        proc.stdin.write(init_msg)
        proc.stdin.flush()

        # Read the first line of stdout — must be valid JSON, nothing else
        proc.stdout._CHUNK_SIZE = 1
        deadline = time.time() + 5
        first_line = ""
        while time.time() < deadline:
            ch = proc.stdout.read(1)
            if not ch:
                break
            first_line += ch
            if first_line.endswith("\n"):
                break

        proc.terminate()
        proc.wait(timeout=3)

        assert first_line.strip(), "Server produced no output on stdout — check if it started"

        # The very first byte must open a JSON object, not an ASCII banner
        stripped = first_line.strip()
        assert stripped.startswith("{"), (
            f"stdout is not clean JSON. First line was:\n{stripped!r}\n"
            "This means FastMCP is printing a banner to stdout, which will "
            "break Claude Desktop. Ensure mcp.run(..., show_banner=False) is set."
        )

        # Validate it's actually parseable JSON-RPC
        parsed = json.loads(stripped)
        assert parsed.get("jsonrpc") == "2.0", "Response is not JSON-RPC 2.0"
        assert "result" in parsed, "Expected 'result' in initialize response"
