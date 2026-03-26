"""
DesktopCommanderPy - Filesystem tools.

Provides read, write, diff-based edit, search, and directory listing.
All operations are sandboxed via utils.resolve_and_validate_path().
"""

import logging
import os
import re
from pathlib import Path
from typing import Annotated

from core.tools.utils import (
    check_extension_allowed,
    load_security_config,
    resolve_and_validate_path,
)

logger = logging.getLogger(__name__)

# Lazy-load config reference (set by server.py after startup)
_security_config: dict | None = None


def _cfg() -> dict:
    """Return the active security config, loading defaults if needed."""
    global _security_config
    if _security_config is None:
        _cfg_path = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
        _security_config = load_security_config(_cfg_path)
    return _security_config


def _allowed() -> list[str]:
    return _cfg()["security"]["allowed_directories"]


def _blocked_ext() -> list[str]:
    return _cfg()["security"].get("write_blocked_extensions", [])


def _max_lines() -> int:
    return _cfg()["security"].get("max_read_lines", 2000)


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

async def read_file(
    path: Annotated[str, "Absolute path to the file to read."],
    offset: Annotated[int, "Line number to start reading from (0-based). Default 0."] = 0,
    length: Annotated[int, "Maximum number of lines to read. 0 means use configured limit."] = 0,
) -> str:
    """Read a text file and return its contents, with optional pagination.

    Pagination via *offset* and *length* allows reading large files in chunks
    without loading everything into the LLM context. The security sandbox is
    enforced: the path must be inside an allowed directory.

    Returns the file text. Raises PermissionError or FileNotFoundError on error.
    """
    resolved = resolve_and_validate_path(path, _allowed())

    max_lines = length if length > 0 else _max_lines()

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except IsADirectoryError:
        raise ValueError(f"'{resolved}' is a directory, not a file.")

    total = len(lines)
    chunk = lines[offset: offset + max_lines]
    result = "".join(chunk)

    if offset + max_lines < total:
        result += f"\n[... {total - offset - max_lines} more lines not shown. Use offset={offset + max_lines} to continue ...]"

    return result


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

async def write_file(
    path: Annotated[str, "Absolute path to the file to write."],
    content: Annotated[str, "Text content to write to the file."],
    mode: Annotated[str, "Write mode: 'rewrite' (default) overwrites; 'append' adds at end."] = "rewrite",
) -> str:
    """Write or append text content to a file.

    The parent directory is created automatically if it doesn't exist.
    The path must be inside an allowed directory and the extension must
    not be in the blocked list.

    Returns a success message with the number of lines written.
    """
    resolved = resolve_and_validate_path(path, _allowed())
    check_extension_allowed(resolved, _blocked_ext())

    resolved.parent.mkdir(parents=True, exist_ok=True)

    file_mode = "w" if mode == "rewrite" else "a"
    with open(resolved, file_mode, encoding="utf-8") as f:
        f.write(content)

    lines_written = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    action = "Written" if mode == "rewrite" else "Appended"
    return f"{action} {lines_written} lines to '{resolved}'."


# ---------------------------------------------------------------------------
# edit_file_diff — surgical find/replace editing
# ---------------------------------------------------------------------------

async def edit_file_diff(
    path: Annotated[str, "Absolute path to the file to edit."],
    old_string: Annotated[str, "Exact text to find in the file (must be unique or use expected_replacements)."],
    new_string: Annotated[str, "Replacement text. Use empty string to delete old_string."],
    expected_replacements: Annotated[int, "Expected number of occurrences to replace. Default 1."] = 1,
) -> str:
    """Edit a file by replacing an exact text snippet with new content.

    This is the preferred editing approach: send only the changed part
    instead of rewriting the whole file. The old_string must match exactly
    (whitespace, indentation) and should include enough context to be unique.

    Raises ValueError if old_string is not found or found more/fewer times
    than expected_replacements.
    """
    resolved = resolve_and_validate_path(path, _allowed())
    check_extension_allowed(resolved, _blocked_ext())

    original = resolved.read_text(encoding="utf-8")
    count = original.count(old_string)

    if count == 0:
        raise ValueError(f"old_string not found in '{resolved}'.")
    if count != expected_replacements:
        raise ValueError(
            f"Expected {expected_replacements} occurrence(s) of old_string, found {count}."
        )

    updated = original.replace(old_string, new_string, expected_replacements)
    resolved.write_text(updated, encoding="utf-8")
    return f"Replaced {expected_replacements} occurrence(s) in '{resolved}'."


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------

async def list_directory(
    path: Annotated[str, "Absolute path to the directory to list."],
    recursive: Annotated[bool, "If True, list subdirectories recursively. Default False."] = False,
    max_depth: Annotated[int, "Maximum recursion depth when recursive=True. Default 3."] = 3,
) -> str:
    """List the contents of a directory with file sizes and types.

    Returns a formatted tree showing [DIR] and [FILE] entries with sizes.
    Respects the allowed_directories sandbox.
    """
    resolved = resolve_and_validate_path(path, _allowed())

    if not resolved.is_dir():
        raise ValueError(f"'{resolved}' is not a directory.")

    lines: list[str] = [f"Directory listing: {resolved}\n"]

    def _walk(current: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            lines.append(f"{prefix}[...depth limit reached]")
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}[DENIED]")
            return

        for entry in entries:
            if entry.is_dir():
                lines.append(f"{prefix}[DIR]  {entry.name}/")
                if recursive:
                    _walk(entry, depth + 1, prefix + "    ")
            else:
                try:
                    size = entry.stat().st_size
                    size_str = _human_size(size)
                except OSError:
                    size_str = "?"
                lines.append(f"{prefix}[FILE] {entry.name} ({size_str})")

    _walk(resolved, 1, "  ")
    return "\n".join(lines)


def _human_size(n: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------

async def search_files(
    root: Annotated[str, "Absolute path to directory to search in."],
    pattern: Annotated[str, "Glob pattern (e.g. '*.py') or substring to match in file names."],
    content_search: Annotated[str, "Optional text to search inside file contents. Empty = skip content search."] = "",
    case_sensitive: Annotated[bool, "Case-sensitive matching. Default False."] = False,
    max_results: Annotated[int, "Maximum number of results to return. Default 100."] = 100,
) -> str:
    """Search for files by name pattern and/or content substring.

    - *pattern* is matched against file names using glob syntax OR substring match.
    - *content_search* scans file contents (text files only, skips binary).
    - Returns a list of matching absolute paths with optional match context.
    """
    resolved = resolve_and_validate_path(root, _allowed())

    if not resolved.is_dir():
        raise ValueError(f"'{resolved}' is not a directory.")

    flag = 0 if case_sensitive else re.IGNORECASE
    results: list[str] = []

    # Compile content regex if needed
    content_re = re.compile(re.escape(content_search), flag) if content_search else None

    for file_path in resolved.rglob("*"):
        if len(results) >= max_results:
            break
        if not file_path.is_file():
            continue

        # Name match
        name = file_path.name
        name_match = (
            re.search(re.escape(pattern.replace("*", "\x00").replace("?", "\x01"))
                      .replace(r"\x00", ".*").replace(r"\x01", "."), name, flag)
            or (not any(c in pattern for c in "*?") and
                (pattern.lower() in name.lower() if not case_sensitive else pattern in name))
        )

        if not name_match:
            continue

        if content_re is None:
            results.append(str(file_path))
        else:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                matches = content_re.findall(text)
                if matches:
                    results.append(f"{file_path}  [{len(matches)} match(es)]")
            except OSError:
                pass

    if not results:
        return f"No files found matching '{pattern}'" + (
            f" with content '{content_search}'" if content_search else ""
        ) + f" under '{resolved}'."

    header = f"Found {len(results)} file(s) matching '{pattern}'"
    if content_search:
        header += f" containing '{content_search}'"
    header += f" under '{resolved}':\n"
    return header + "\n".join(results)


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------

async def get_file_info(
    path: Annotated[str, "Absolute path to the file or directory."],
) -> str:
    """Return metadata about a file or directory.

    Includes: type, size, creation time, modification time, permissions,
    and a content preview for text files (first 10 lines).
    """
    resolved = resolve_and_validate_path(path, _allowed())

    try:
        stat = resolved.stat()
    except FileNotFoundError:
        raise FileNotFoundError(f"'{resolved}' does not exist.")

    import datetime

    kind = "Directory" if resolved.is_dir() else "File"
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    ctime = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds")

    info_lines = [
        f"Path:     {resolved}",
        f"Type:     {kind}",
        f"Size:     {_human_size(stat.st_size)}  ({stat.st_size} bytes)",
        f"Modified: {mtime}",
        f"Created:  {ctime}",
    ]

    if resolved.is_file():
        info_lines.append(f"Extension: {resolved.suffix or '(none)'}")
        # Try text preview
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                preview_lines = [f.readline() for _ in range(10)]
            preview = "".join(preview_lines).rstrip()
            info_lines.append(f"\n--- Content preview (first 10 lines) ---\n{preview}")
        except Exception:
            info_lines.append("(binary file — no preview)")

    return "\n".join(info_lines)
