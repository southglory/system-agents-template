#!/usr/bin/env python3
"""
chat_guard.py — PreToolUse hook: 채팅 프로토콜(chatrooms/PROTOCOL.md) 규칙을 강제한다.

Claude Code의 PreToolUse hook으로 등록되어, Write/Edit가
  - chatrooms/ 아래 메시지 파일을 쓸 때 → 프로토콜 검증
  - tasks/board.yaml 을 에이전트가 직접 수정할 때 → 차단
하는 것을 검사한다.

hook 입력: stdin 으로 JSON ({tool_name, tool_input:{file_path, content|new_string}, ...}).
차단: exit code 2 + stderr 에 사유(에이전트가 읽고 스스로 고침).
통과: exit code 0.

검증 항목 (PROTOCOL.md 기준):
  1. ref 누락 차단   — task-update/done/claim 에 `ref: T-NNN` 필수
  2. 필수 frontmatter — from/to/time/type/subject
  3. 파일명 규칙      — {YYYY-MM-DD}_{HHMMSS}_{agent}.md
  4. board.yaml 직접수정 차단 — 에이전트는 task-* 메시지로만
"""
import json
import os
import re
import sys

TASK_TYPES_NEED_REF = {"task-update", "task-done", "task-claim"}
REQUIRED_FIELDS = ["from", "to", "time", "type", "subject"]
FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}_[a-z0-9_-]+\.md$")


def block(reason: str):
    """차단: 사유를 stderr로 내보내고 exit 2."""
    sys.stderr.write("⛔ 채팅 프로토콜 위반으로 차단되었습니다.\n\n" + reason + "\n")
    sys.exit(2)


def parse_frontmatter(text: str):
    """--- ... --- 사이 frontmatter를 아주 단순하게 key: value 로 파싱."""
    if not text.lstrip().startswith("---"):
        return None
    body = text.lstrip()[3:]
    end = body.find("\n---")
    if end == -1:
        return None
    fm = {}
    for line in body[:end].splitlines():
        line = line.rstrip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1).lower()] = m.group(2).strip()
    return fm


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # 입력 파싱 실패 시 통과(안전쪽으로 hook이 작업을 막지 않음)

    ti = payload.get("tool_input", {}) or {}
    fp = ti.get("file_path") or ti.get("path") or ""
    content = ti.get("content")
    if content is None:
        content = ti.get("new_string", "")
    norm = fp.replace("\\", "/")

    # 4) board.yaml 직접수정 차단
    if norm.endswith("tasks/board.yaml") or norm.endswith("/board.yaml"):
        block(
            "에이전트는 `tasks/board.yaml`을 직접 수정할 수 없습니다.\n"
            "작업 변경은 반드시 `task-create` / `task-update` / `task-done` 메시지로 보내세요.\n"
            "→ `/send-message` 스킬로 task-* type 메시지를 작성하면 봇이 board.yaml을 갱신합니다."
        )

    # chatrooms/ 아래 .md 메시지 파일만 검증 대상
    if "/chatrooms/" not in norm and not norm.startswith("chatrooms/"):
        sys.exit(0)
    if not norm.endswith(".md"):
        sys.exit(0)
    # PROTOCOL.md, read-status 등 메시지가 아닌 파일은 제외
    base = os.path.basename(norm)
    if base == "PROTOCOL.md" or "/.read-status/" in norm or "/attachments/" in norm:
        sys.exit(0)

    # 3) 파일명 규칙
    if not FILENAME_RE.match(base):
        block(
            f"메시지 파일명이 규칙에 맞지 않습니다: `{base}`\n"
            "형식: `{YYYY-MM-DD}_{HHMMSS}_{agent}.md` (UTC, 에이전트명 소문자)\n"
            "예: `2026-03-19_143052_alice.md`\n"
            "→ 동시 작성 충돌을 막기 위한 규칙입니다. `/send-message` 스킬을 쓰면 자동으로 맞춰집니다."
        )

    fm = parse_frontmatter(content or "")
    if fm is None:
        block(
            "메시지에 frontmatter(--- ... ---)가 없습니다.\n"
            f"필수 필드: {', '.join(REQUIRED_FIELDS)} (type에 따라 ref 추가)."
        )

    # 2) 필수 frontmatter 필드
    missing = [f for f in REQUIRED_FIELDS if not fm.get(f)]
    if missing:
        block(
            f"필수 frontmatter 필드 누락: {', '.join(missing)}\n"
            f"모든 메시지는 {', '.join(REQUIRED_FIELDS)} 를 포함해야 합니다."
        )

    # 1) ref 누락 차단 (최우선)
    mtype = fm.get("type", "")
    if mtype in TASK_TYPES_NEED_REF:
        ref = fm.get("ref", "")
        if not re.match(r"^T-\d+$", ref):
            block(
                f"`{mtype}` 메시지에는 `ref: T-NNN` 이 반드시 필요합니다 (현재: `{ref or '없음'}`).\n"
                "`ref`는 봇이 태스크를 식별하는 유일한 키입니다. 없으면 봇이 아무 처리도 못 합니다.\n"
                "→ frontmatter에 `ref: T-001` 형식으로 대상 태스크 ID를 추가하세요."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
