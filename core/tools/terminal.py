"""
DesktopCommanderPy - Terminal execution tools.

Provides execute_command (blocking, captured output) and
execute_command_streaming (async generator for long-running commands).

Security: all commands are checked against the blacklist before execution.
Platform: auto-detects Windows (PowerShell) vs Linux/macOS (bash/zsh).
"""

import asyncio
import logging
from pathlib import Path
from typing import Annotated, AsyncGenerator

from core.tools.utils import (
    build_subprocess_env,
    check_command_allowed,
    get_default_timeout,
    get_shell,
    load_security_config,
)

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
_security_config: dict | None = None


def _cfg() -> dict:
    global _security_config
    if _security_config is None:
        _security_config = load_security_config(_CONFIG_PATH)
    return _security_config


def _blocked() -> list[str]:
    return _cfg()["security"].get("blocked_commands", [])


def _max_output() -> int:
    return _cfg().get("terminal", {}).get("max_output_chars", 500_000)


# ---------------------------------------------------------------------------
# execute_command — blocking, full output capture
# ---------------------------------------------------------------------------

async def execute_command(
    command: Annotated[str, "Shell command to execute. Use PowerShell syntax on Windows."],
    working_directory: Annotated[str, "Working directory for the command. Defaults to user home."] = "",
    timeout_seconds: Annotated[int, "Timeout in seconds. 0 = use configured default."] = 0,
    environment: Annotated[dict[str, str], "Additional environment variables as a dict."] = {},
) -> str:
    """Execute a shell command and return its combined stdout+stderr output.

    Uses PowerShell on Windows, bash/zsh on Linux/macOS.
    The command is checked against the security blacklist before execution.
    Output is captured and returned as a string (truncated if too large).

    Returns the combined output. On non-zero exit code, output includes
    the exit code so the caller can detect failures.
    """
    check_command_allowed(command, _blocked())

    shell_args = get_shell(_cfg())
    timeout = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    cwd = working_directory if working_directory else str(Path.home())

    env = build_subprocess_env(environment or {})

    logger.info("Executing command: %r (cwd=%s, timeout=%ds)", command, cwd, timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            *shell_args, command,
            stdin=asyncio.subprocess.DEVNULL,   # prevent child from inheriting MCP stdin
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # merge stderr into stdout
            cwd=cwd,
            env=env,
        )
        try:
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"[TIMEOUT] Command exceeded {timeout}s limit and was killed.\nPartial output may be unavailable."

        output = stdout_bytes.decode("utf-8", errors="replace")
        max_chars = _max_output()
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n[TRUNCATED: output exceeded {max_chars} chars]"

        exit_note = f"\n[Exit code: {proc.returncode}]" if proc.returncode != 0 else ""
        return output.rstrip() + exit_note

    except FileNotFoundError as exc:
        raise RuntimeError(f"Shell not found: {shell_args[0]}. Error: {exc}") from exc
    except Exception as exc:
        logger.error("Command execution failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# execute_command_streaming — async generator for long-running commands
# ---------------------------------------------------------------------------

async def execute_command_streaming(
    command: Annotated[str, "Shell command to execute with streaming output."],
    working_directory: Annotated[str, "Working directory for the command."] = "",
    timeout_seconds: Annotated[int, "Overall timeout in seconds. 0 = use configured default."] = 0,
    environment: Annotated[dict[str, str], "Additional environment variables as a dict."] = {},
) -> str:
    """Execute a long-running command and return output incrementally.

    Intended for commands that produce output over time (builds, tests,
    long scripts). Output is collected line by line and returned as a
    single string; for true streaming, the MCP client would use SSE.

    The command is blocked if it matches the security blacklist.
    """
    check_command_allowed(command, _blocked())

    shell_args = get_shell(_cfg())
    timeout = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    cwd = working_directory if working_directory else str(Path.home())

    env = build_subprocess_env(environment or {})

    logger.info("Streaming command: %r", command)

    lines_collected: list[str] = []
    max_chars = _max_output()
    total_chars = 0

    try:
        proc = await asyncio.create_subprocess_exec(
            *shell_args, command,
            stdin=asyncio.subprocess.DEVNULL,   # prevent child from inheriting MCP stdin
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )

        async def _read_lines() -> None:
            nonlocal total_chars
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace")
                lines_collected.append(line)
                total_chars += len(line)
                if total_chars >= max_chars:
                    lines_collected.append("[TRUNCATED]\n")
                    proc.kill()
                    break

        try:
            await asyncio.wait_for(_read_lines(), timeout=timeout)
            await proc.wait()
        except asyncio.TimeoutError:
            proc.kill()
            lines_collected.append(f"\n[TIMEOUT] Command exceeded {timeout}s\n")

        output = "".join(lines_collected)
        exit_note = f"\n[Exit code: {proc.returncode}]" if proc.returncode and proc.returncode != 0 else ""
        return output.rstrip() + exit_note

    except Exception as exc:
        logger.error("Streaming command failed: %s", exc)
        raise
