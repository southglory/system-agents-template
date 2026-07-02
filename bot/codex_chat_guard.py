#!/usr/bin/env python3
"""Codex PreToolUse guard for the system-agents chat protocol.

The guard is intentionally small: it translates common Codex hook payloads into
file write intents, then enforces the same protocol constraints as the Claude
hook layer.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any


TASK_TYPES_NEED_REF = {"task-update", "task-done", "task-claim"}
REQUIRED_FIELDS = ["from", "to", "time", "type", "subject"]
FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}_[a-z0-9_-]+\.md$")


class ProtocolViolation(Exception):
    """Raised when a proposed tool call violates the system-agents protocol."""


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.lstrip().startswith("---"):
        return None
    body = text.lstrip()[3:]
    end = body.find("\n---")
    if end == -1:
        return None

    frontmatter: dict[str, str] = {}
    for line in body[:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line.rstrip())
        if match:
            frontmatter[match.group(1).lower()] = match.group(2).strip()
    return frontmatter


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def _is_board_path(norm: str) -> bool:
    return norm.endswith("/tasks/board.yaml") or norm == "tasks/board.yaml"


def _is_chatroom_message_path(norm: str) -> bool:
    if "/chatrooms/" not in norm and not norm.startswith("chatrooms/"):
        return False
    if not norm.endswith(".md"):
        return False

    base = os.path.basename(norm)
    if base == "PROTOCOL.md":
        return False
    if "/.read-status/" in norm or "/attachments/" in norm:
        return False
    return True


def validate_write(path: str, content: str | None, mode: str = "write") -> None:
    norm = _normalize(path)

    if _is_board_path(norm):
        raise ProtocolViolation(
            "Agents must not edit tasks/board.yaml directly. "
            "Send task-* messages and let bot/turn_bot.py update the board."
        )

    if not _is_chatroom_message_path(norm):
        return

    if mode in {"update", "delete"}:
        raise ProtocolViolation(
            "Chatroom messages are append-only. Write a new message file instead "
            "of editing or deleting an existing message."
        )

    base = os.path.basename(norm)
    if not FILENAME_RE.match(base):
        raise ProtocolViolation(
            f"Message filename does not match the protocol: {base}\n"
            "Expected: YYYY-MM-DD_HHMMSS_agent.md"
        )

    if content is None:
        raise ProtocolViolation(
            "Cannot validate the chatroom message because the proposed write did "
            "not include full file content."
        )

    frontmatter = parse_frontmatter(content)
    if frontmatter is None:
        raise ProtocolViolation(
            "Chatroom messages must include frontmatter delimited by --- lines."
        )

    missing = [field for field in REQUIRED_FIELDS if not frontmatter.get(field)]
    if missing:
        raise ProtocolViolation(
            "Missing required frontmatter fields: " + ", ".join(missing)
        )

    message_type = frontmatter.get("type", "")
    if message_type in TASK_TYPES_NEED_REF:
        ref = frontmatter.get("ref", "")
        if not re.match(r"^T-\d+$", ref):
            raise ProtocolViolation(
                f"{message_type} messages require ref: T-NNN. Current ref: "
                f"{ref or 'missing'}"
            )


def extract_patch_writes(patch: str) -> list[tuple[str, str | None, str]]:
    writes: list[tuple[str, str | None, str]] = []
    current_path: str | None = None
    current_mode: str | None = None
    add_lines: list[str] = []

    def flush() -> None:
        nonlocal current_path, current_mode, add_lines
        if current_path is None or current_mode is None:
            return
        content = "\n".join(add_lines) + ("\n" if add_lines else "")
        writes.append((current_path, content if current_mode == "add" else None, current_mode))
        current_path = None
        current_mode = None
        add_lines = []

    for line in patch.splitlines():
        if line.startswith("*** Add File: "):
            flush()
            current_path = line.removeprefix("*** Add File: ").strip()
            current_mode = "add"
            add_lines = []
            continue
        if line.startswith("*** Update File: "):
            flush()
            current_path = line.removeprefix("*** Update File: ").strip()
            current_mode = "update"
            add_lines = []
            continue
        if line.startswith("*** Delete File: "):
            flush()
            path = line.removeprefix("*** Delete File: ").strip()
            writes.append((path, None, "delete"))
            continue
        if current_mode == "add" and line.startswith("+"):
            add_lines.append(line[1:])

    flush()
    return writes


def _tool_inputs(payload: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for key in ("tool_input", "input", "arguments", "parameters", "args"):
        if key in payload:
            values.append(payload[key])
    return values


def extract_write_intents(payload: dict[str, Any]) -> list[tuple[str, str | None, str]]:
    intents: list[tuple[str, str | None, str]] = []

    for tool_input in _tool_inputs(payload):
        if isinstance(tool_input, str):
            if "*** Begin Patch" in tool_input:
                intents.extend(extract_patch_writes(tool_input))
            continue

        if not isinstance(tool_input, dict):
            continue

        path = tool_input.get("file_path") or tool_input.get("path")
        if isinstance(path, str):
            content = tool_input.get("content")
            if content is None:
                content = tool_input.get("new_string")
            intents.append((path, content if isinstance(content, str) else None, "write"))

        for patch_key in ("patch", "diff"):
            patch = tool_input.get(patch_key)
            if isinstance(patch, str) and "*** Begin Patch" in patch:
                intents.extend(extract_patch_writes(patch))

    return intents


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if not isinstance(payload, dict):
        return 0

    try:
        for path, content, mode in extract_write_intents(payload):
            validate_write(path, content, mode)
    except ProtocolViolation as exc:
        sys.stderr.write("system-agents protocol violation:\n\n" + str(exc) + "\n")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
