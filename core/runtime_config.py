"""
DesktopCommanderPy - Central runtime configuration.

This module provides a single source of truth for configuration values
loaded from YAML and used by all tools at runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any

import yaml


@dataclass
class SecuritySettings:
    allowed_directories: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=list)
    max_file_size_bytes: int = 10 * 1024 * 1024
    max_read_lines: int = 2000
    write_blocked_extensions: list[str] = field(default_factory=lambda: [".exe", ".dll", ".sys"])


@dataclass
class TerminalSettings:
    windows_shell: str = "powershell.exe"
    linux_shell: str = "/bin/bash"
    macos_shell: str = "/bin/zsh"
    default_timeout_seconds: int = 30
    max_output_chars: int = 500_000


@dataclass
class LoggingSettings:
    level: str = "INFO"
    log_to_file: bool = False
    log_file: str = "logs/desktopcommanderpy.log"


@dataclass
class RuntimeConfig:
    security: SecuritySettings = field(default_factory=SecuritySettings)
    terminal: TerminalSettings = field(default_factory=TerminalSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_CONFIG_PATH = Path(__file__).parent.parent / "config" / "security_config.yaml"
_LOCK = RLock()
_CONFIG: RuntimeConfig | None = None


def _coerce_str_list(value: Any, fallback: list[str]) -> list[str]:
    if value is None:
        return list(fallback)
    if isinstance(value, list):
        return [str(item) for item in value]
    return list(fallback)


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return fallback


def _coerce_int(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _merge_runtime_config(data: dict[str, Any] | None) -> RuntimeConfig:
    payload = data or {}
    security = payload.get("security") or {}
    terminal = payload.get("terminal") or {}
    logging = payload.get("logging") or {}

    return RuntimeConfig(
        security=SecuritySettings(
            allowed_directories=_coerce_str_list(
                security.get("allowed_directories"),
                [],
            ),
            blocked_commands=_coerce_str_list(
                security.get("blocked_commands"),
                [],
            ),
            max_file_size_bytes=_coerce_int(
                security.get("max_file_size_bytes"),
                10 * 1024 * 1024,
            ),
            max_read_lines=_coerce_int(
                security.get("max_read_lines"),
                2000,
            ),
            write_blocked_extensions=_coerce_str_list(
                security.get("write_blocked_extensions"),
                [".exe", ".dll", ".sys"],
            ),
        ),
        terminal=TerminalSettings(
            windows_shell=str(terminal.get("windows_shell", "powershell.exe")),
            linux_shell=str(terminal.get("linux_shell", "/bin/bash")),
            macos_shell=str(terminal.get("macos_shell", "/bin/zsh")),
            default_timeout_seconds=_coerce_int(
                terminal.get("default_timeout_seconds"),
                30,
            ),
            max_output_chars=_coerce_int(
                terminal.get("max_output_chars"),
                500_000,
            ),
        ),
        logging=LoggingSettings(
            level=str(logging.get("level", "INFO")),
            log_to_file=_coerce_bool(logging.get("log_to_file"), False),
            log_file=str(logging.get("log_file", "logs/desktopcommanderpy.log")),
        ),
    )


def load_runtime_config(config_path: Path | None = None, *, force_reload: bool = False) -> RuntimeConfig:
    global _CONFIG
    path = config_path or _CONFIG_PATH
    with _LOCK:
        if _CONFIG is not None and not force_reload:
            return _CONFIG
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = None
        except yaml.YAMLError:
            data = None
        _CONFIG = _merge_runtime_config(data)
        return _CONFIG


def get_runtime_config() -> RuntimeConfig:
    return load_runtime_config()


def save_runtime_config(config: RuntimeConfig, config_path: Path | None = None) -> None:
    path = config_path or _CONFIG_PATH
    path.write_text(
        yaml.safe_dump(config.to_dict(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def reload_runtime_config() -> RuntimeConfig:
    return load_runtime_config(force_reload=True)
