"""
DesktopCommanderPy - Security helpers and path utilities.

All filesystem and terminal tools MUST use the functions in this module
before performing any operation. This is the single point of truth for
security enforcement.
"""

import logging
import platform
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

    Matching is case-insensitive substring search so partial patterns work.
    E.g., blocking "net user" also blocks "NET USER /add foo".
    """
    cmd_lower = command.lower()
    for blocked in blocked_commands:
        if blocked.lower() in cmd_lower:
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
