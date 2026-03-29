"""
DesktopCommanderPy - Security helpers and path utilities.

All filesystem and terminal tools MUST use the functions in this module
before performing any operation. This is the single point of truth for
security enforcement.
"""

import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

from core.runtime_config import get_runtime_config

logger = logging.getLogger(__name__)


def load_security_config(config_path: Path | None = None) -> dict[str, Any]:
    """Compatibility wrapper around the central runtime config loader."""
    return get_runtime_config().to_dict()


# ---------------------------------------------------------------------------
# Path security
# ---------------------------------------------------------------------------

def resolve_and_validate_path(
    path: str | Path,
    allowed_dirs: list[str],
    cwd: str | Path | None = None,
) -> Path:
    """Resolve *path* to an absolute Path and verify it's inside an allowed dir.

    Args:
        path: The path to validate (relative or absolute).
        allowed_dirs: List of allowed root directories (from security config).

    Returns:
        Resolved absolute Path if valid.

    Raises:
        PermissionError: If *path* is outside all allowed directories.
        ValueError: If *path* is empty or invalid.
    """
    if not path:
        raise ValueError("Path must not be empty.")

    raw = str(path).strip()
    expanded = os.path.expanduser(raw)
    base_dir = Path(cwd).expanduser() if cwd else Path.cwd()

    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = base_dir / candidate

    resolved = candidate.resolve(strict=False)
    if resolved.exists():
        try:
            resolved = resolved.resolve(strict=True)
        except OSError:
            pass

    if not allowed_dirs:
        # No restrictions configured - allow everything (dev mode)
        logger.debug("No allowed_dirs configured; access to %s permitted", resolved)
        return resolved

    resolved_norm = os.path.normcase(os.path.normpath(str(resolved)))

    for allowed in allowed_dirs:
        allowed_expanded = Path(os.path.expanduser(str(allowed).strip()))
        allowed_resolved = allowed_expanded.resolve(strict=False)
        allowed_norm = os.path.normcase(os.path.normpath(str(allowed_resolved)))

        if resolved_norm == allowed_norm:
            return resolved

        if resolved_norm.startswith(allowed_norm + os.sep):
            return resolved

        if os.name == "nt":
            drive_root = os.path.splitdrive(allowed_norm)[0]
            if allowed_norm in {drive_root, drive_root + os.sep} and drive_root:
                if resolved_norm.startswith(drive_root):
                    return resolved

    raise PermissionError(
        f"Access denied: '{resolved}' is outside all allowed directories.\n"
        f"Allowed: {allowed_dirs}"
    )


def check_extension_allowed(
    path: Path,
    blocked_extensions: list[str],
) -> None:
    """Raise ValueError if *path* has a blocked extension."""
    ext = path.suffix.lower()
    blocked_lower = [e.lower() for e in blocked_extensions]
    if ext in blocked_lower:
        raise ValueError(
            f"Write operation blocked: extension '{ext}' is not allowed.\n"
            f"Blocked extensions: {blocked_extensions}"
        )


# ---------------------------------------------------------------------------
# Command security
# ---------------------------------------------------------------------------

def check_command_allowed(command: str, blocked_commands: list[str]) -> None:
    """Raise PermissionError if *command* matches any blocked pattern.

    Uses word-boundary regex (case-insensitive) so short tokens like 'dd'
    don't accidentally block 'add', 'address', 'hidden', 'adding', etc.
    Multi-word patterns like 'net user' still match 'NET USER /add foo'.
    """
    cmd_lower = command.lower()
    for blocked in blocked_commands:
        pattern = r"\b" + re.escape(blocked.lower()) + r"\b"
        if re.search(pattern, cmd_lower):
            raise PermissionError(
                f"Command blocked by security policy: matched '{blocked}'.\n"
                f"Command attempted: {command!r}"
            )


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

def get_shell(config: dict) -> list[str]:
    """Return the appropriate shell command list for the current OS."""
    system = platform.system()
    terminal_cfg = config.get("terminal", {})

    if system == "Windows":
        shell = terminal_cfg.get("windows_shell", "powershell.exe")
        return [shell, "-Command"]
    elif system == "Darwin":
        shell = terminal_cfg.get("macos_shell", "/bin/zsh")
        return [shell, "-c"]
    else:
        shell = terminal_cfg.get("linux_shell", "/bin/bash")
        return [shell, "-c"]


def get_default_timeout(config: dict) -> int:
    """Return the configured default terminal timeout in seconds."""
    return config.get("terminal", {}).get("default_timeout_seconds", 30)


def resolve_working_directory(working_directory: str | Path | None = None) -> str:
    """Resolve a working directory to an absolute path string."""
    if not working_directory:
        return str(Path.home())
    expanded = os.path.expanduser(str(working_directory).strip())
    return str(Path(expanded).resolve(strict=False))


# ---------------------------------------------------------------------------
# Subprocess environment helpers
# ---------------------------------------------------------------------------

def build_subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build an env dict suitable for subprocess execution.

    Enriches PATH with Python-related directories so subprocesses can find
    'python', 'python3', 'py', 'pip', etc. even when the parent process
    was launched with a minimal PATH (e.g. from Claude Desktop).

    Always sets PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 to prevent
    UnicodeEncodeError on Windows consoles using cp1252.

    Args:
        extra: Additional env vars to merge (these override os.environ).

    Returns:
        A copy of os.environ enriched with Python paths and UTF-8 settings.
    """
    env = os.environ.copy()

    # UTF-8 everywhere — prevents UnicodeEncodeError on cp1252 consoles
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # Collect Python directories to prepend to PATH
    python_dirs: list[str] = []

    # 1. Current venv Scripts dir — has python.exe, pip.exe, etc.
    venv_scripts = Path(sys.executable).parent
    python_dirs.append(str(venv_scripts))

    # 2. Base Python installation Scripts dir (outside venv)
    try:
        base_scripts = Path(sys.base_prefix) / "Scripts"
        if base_scripts != venv_scripts:
            python_dirs.append(str(base_scripts))
    except Exception:
        pass

    # 3. Windows py.exe launcher — typically in C:\Windows
    for candidate in [Path(r"C:\Windows"), Path(r"C:\Windows\System32")]:
        if (candidate / "py.exe").exists():
            python_dirs.append(str(candidate))
            break

    # 4. Common user-level Python install on Windows
    try:
        local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
        if local_app.exists():
            for py_dir in sorted(local_app.iterdir(), reverse=True):
                if py_dir.is_dir() and py_dir.name.startswith("Python"):
                    python_dirs.append(str(py_dir))
                    python_dirs.append(str(py_dir / "Scripts"))
                    break
    except Exception:
        pass

    # Prepend dirs not already present in PATH
    current_path = env.get("PATH", "")
    path_lower = current_path.lower()
    for d in reversed(python_dirs):
        if d.lower() not in path_lower:
            current_path = d + os.pathsep + current_path
            path_lower = current_path.lower()

    env["PATH"] = current_path

    if extra:
        env.update(extra)

    return env
