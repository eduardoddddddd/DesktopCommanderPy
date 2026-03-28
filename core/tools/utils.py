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

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_security_config(config_path: Path) -> dict[str, Any]:
    """Load and return the security configuration from YAML.

    Falls back to a safe minimal default if the file is missing or invalid.
    """
    defaults: dict[str, Any] = {
        "security": {
            "allowed_directories": [],
            "blocked_commands": [],
            "max_file_size_bytes": 10 * 1024 * 1024,
            "max_read_lines": 2000,
            "write_blocked_extensions": [".exe", ".dll", ".sys"],
        },
        "terminal": {
            "windows_shell": "powershell.exe",
            "linux_shell": "/bin/bash",
            "macos_shell": "/bin/zsh",
            "default_timeout_seconds": 30,
            "max_output_chars": 500_000,
        },
        "logging": {"level": "INFO"},
    }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        # Merge with defaults so missing keys don't cause KeyErrors
        _deep_merge(defaults, loaded or {})
        logger.info("Security config loaded from %s", config_path)
    except FileNotFoundError:
        logger.warning("Config not found at %s — using defaults", config_path)
    except yaml.YAMLError as exc:
        logger.error("YAML parse error in config: %s — using defaults", exc)
    return defaults

def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge *override* into *base* in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Path security
# ---------------------------------------------------------------------------

def resolve_and_validate_path(
    path: str | Path,
    allowed_dirs: list[str],
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

    resolved = Path(path).resolve()

    if not allowed_dirs:
        # No restrictions configured — allow everything (dev mode)
        logger.debug("No allowed_dirs configured; access to %s permitted", resolved)
        return resolved

    for allowed in allowed_dirs:
        allowed_resolved = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_resolved)
            return resolved  # Path is inside this allowed dir
        except ValueError:
            continue

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
