"""
DesktopCommanderPy - Runtime configuration tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from core.runtime_config import (
    RuntimeConfig,
    get_runtime_config,
    reload_runtime_config,
    save_runtime_config,
)


_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
_FIELD_DEFS: dict[str, dict[str, str | bool]] = {
    "security.allowed_directories": {"valueType": "array", "editable": True},
    "security.blocked_commands": {"valueType": "array", "editable": True},
    "security.max_file_size_bytes": {"valueType": "number", "editable": True},
    "security.max_read_lines": {"valueType": "number", "editable": True},
    "security.write_blocked_extensions": {"valueType": "array", "editable": True},
    "terminal.windows_shell": {"valueType": "string", "editable": True},
    "terminal.linux_shell": {"valueType": "string", "editable": True},
    "terminal.macos_shell": {"valueType": "string", "editable": True},
    "terminal.default_timeout_seconds": {"valueType": "number", "editable": True},
    "terminal.max_output_chars": {"valueType": "number", "editable": True},
    "logging.level": {"valueType": "string", "editable": True},
    "logging.log_to_file": {"valueType": "boolean", "editable": True},
    "logging.log_file": {"valueType": "string", "editable": True},
}


def _get_nested_value(config: RuntimeConfig, dotted_key: str) -> Any:
    current: Any = config
    for part in dotted_key.split("."):
        current = getattr(current, part)
    return current


def _set_nested_value(config: RuntimeConfig, dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current: Any = config
    for part in parts[:-1]:
        current = getattr(current, part)
    setattr(current, parts[-1], value)


def _coerce_value(value: Any, value_type: str) -> Any:
    if value_type == "string":
        return str(value)
    if value_type == "number":
        if isinstance(value, bool):
            raise ValueError("Boolean is not valid for number fields.")
        return int(value)
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        raise ValueError("Boolean fields require true/false.")
    if value_type == "array":
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [line.strip() for line in stripped.splitlines() if line.strip()]
        raise ValueError("Array fields require a list or newline-separated string.")
    return value


async def get_config() -> dict[str, Any]:
    """Return the active runtime configuration with type metadata."""
    config = get_runtime_config()
    entries: list[dict[str, Any]] = []
    for key, definition in _FIELD_DEFS.items():
        entries.append(
            {
                "key": key,
                "value": _get_nested_value(config, key),
                "valueType": definition["valueType"],
                "editable": definition["editable"],
            }
        )
    return {
        "config": config.to_dict(),
        "entries": entries,
        "configPath": str(_CONFIG_PATH),
    }


async def set_config_value(
    key: Annotated[str, "Dot-separated runtime config key to update."],
    value: Annotated[Any, "New value to store. Type is validated against the config field."],
) -> dict[str, Any]:
    """Update a runtime config value and persist it to YAML."""
    if key not in _FIELD_DEFS:
        raise ValueError(f"Unknown config key: {key}")
    definition = _FIELD_DEFS[key]
    config = get_runtime_config()
    coerced = _coerce_value(value, str(definition["valueType"]))
    _set_nested_value(config, key, coerced)
    save_runtime_config(config)
    reloaded = reload_runtime_config()
    return {
        "updated": key,
        "value": _get_nested_value(reloaded, key),
        "config": reloaded.to_dict(),
    }
