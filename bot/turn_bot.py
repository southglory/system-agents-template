#!/usr/bin/env python3
"""
턴제 봇 - 채팅방 메시지를 스캔하여 board.yaml을 자동 관리한다.

사용법:
    python bot/turn-bot.py              # 한 번 실행 (Phase 1/3/5)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHATROOMS = ROOT / "chatrooms"
TASKS = ROOT / "tasks"
BOARD_FILE = TASKS / "board.yaml"
READ_STATUS_DIR = CHATROOMS / ".read-status"
BOT_STATUS_FILE = READ_STATUS_DIR / "bot.json"

TASK_TYPES = {"task-create", "task-update", "task-done", "task-claim"}


def load_board():
    if not BOARD_FILE.exists():
        return {"last_updated": None, "next_id": 1, "tasks": []}
    with open(BOARD_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return {"last_updated": None, "next_id": 1, "tasks": []}
    return data


def save_board(board):
    board["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(BOARD_FILE, "w", encoding="utf-8") as f:
        yaml.dump(board, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_read_status():
    if not BOT_STATUS_FILE.exists():
        return {}
    with open(BOT_STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_read_status(status):
    READ_STATUS_DIR.mkdir(parents=True, exist_ok=True)
    with open(BOT_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def parse_frontmatter(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, content

    return meta, parts[2].strip()


def get_new_messages(room_name, last_read):
    room_dir = CHATROOMS / room_name
    if not room_dir.exists():
        return []

    files = sorted([
        f.name for f in room_dir.iterdir()
        if f.is_file() and f.suffix == ".md"
    ])

    if last_read and last_read in files:
        idx = files.index(last_read)
        new_files = files[idx + 1:]
    else:
        new_files = files

    messages = []
    for fname in new_files:
        try:
            meta, body = parse_frontmatter(room_dir / fname)
        except Exception as e:
            print(f"[봇] 경고: {room_name}/{fname} 파싱 실패 - {e}")
            continue
        if meta and meta.get("type") in TASK_TYPES:
            messages.append({
                "file": fname,
                "room": room_name,
                "meta": meta,
                "body": body,
            })

    return messages


def scan_all_rooms(read_status):
    all_messages = []
    for item in sorted(CHATROOMS.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        room_name = item.name
        last_read = read_status.get(room_name)
        all_messages.extend(get_new_messages(room_name, last_read))

    all_messages.sort(key=lambda m: m["file"])
    return all_messages


def next_task_id(board):
    nid = board.get("next_id", 1)
    task_id = f"T-{nid:03d}"
    board["next_id"] = nid + 1
    return task_id


def find_task(board, ref):
    for task in board.get("tasks", []):
        if task.get("id") == ref:
            return task
    return None


_bot_msg_counter = 0


def send_bot_message(room, subject, body, ref=None):
    global _bot_msg_counter
    room_dir = CHATROOMS / room
    room_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    _bot_msg_counter += 1
    filename = now.strftime("%Y-%m-%d_%H%M%S") + f"_{_bot_msg_counter:02d}_bot.md"

    lines = ["---"]
    lines.append("from: bot")
    lines.append("to: all")
    lines.append(f"time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("type: message")
    lines.append(f"subject: {subject}")
    if ref:
        lines.append(f"ref: {ref}")
    lines.append("---")
    lines.append("")
    lines.append(body)

    (room_dir / filename).write_text("\n".join(lines), encoding="utf-8")
    return filename


def _create_single_task(board, meta, title=None, overrides=None):
    """Create a single task entry and append to board."""
    overrides = overrides or {}
    task_id = next_task_id(board)

    task = {
        "id": task_id,
        "title": overrides.get("title", title or meta.get("subject", "")),
        "goal": overrides.get("goal", meta.get("goal", "")),
        "phase": overrides.get("phase", meta.get("phase", "")),
        "type": overrides.get("type", meta.get("task_type", "feature")),
        "priority": overrides.get("priority", meta.get("priority", "medium")),
        "created_by": meta.get("from", ""),
        "assignee": overrides.get("assignee", meta.get("assignee", "")),
        "start": None,
        "due": overrides.get("due", meta.get("due")),
        "done": None,
        "status": "대기",
        "notes": overrides.get("notes"),
    }
    board.setdefault("tasks", []).append(task)
    return task_id, task


def _extract_tasks_block(body):
    """
    Extract the `tasks:` YAML block from a message body.

    The body may contain free-form markdown both before and after the YAML
    list. We locate `tasks:` at the start of a line, then scan forward and
    stop at the first line that clearly belongs to prose (a markdown heading
    or a non-indented non-YAML paragraph line).

    Returns the isolated YAML text (str) or None if no `tasks:` block found.
    """
    if not body:
        return None

    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        # match `tasks:` at column 0 (optionally followed by whitespace/newline)
        if line.rstrip() == "tasks:" or line.startswith("tasks:"):
            # only accept if this is at column 0 (real YAML top-level key)
            if line[:6] == "tasks:":
                start = i
                break
    if start is None:
        return None

    # find the end of the YAML block
    end = len(lines)
    # first non-tasks line marks YAML content start
    for i in range(start + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if stripped == "":
            continue  # blank lines stay inside YAML
        if line[0] in (" ", "\t", "-"):
            continue  # indented or list item -> YAML content
        # column-0 non-empty line that is not YAML content
        # (markdown heading, prose, another top-level key unrelated to tasks)
        end = i
        break

    return "\n".join(lines[start:end])


def _parse_batch_tasks(body):
    """
    Parse 'tasks:' YAML block from message body.

    Returns:
        list[dict]    — on success, the parsed tasks list
        "ignored"     — body has no tasks: block (single-task mode intended)
        "malformed"   — body has tasks: block but YAML parsing failed
                        or structure is not a list of dicts
                        (caller should warn the author)
    """
    if not body or "tasks:" not in body:
        return "ignored"

    yaml_text = _extract_tasks_block(body)
    if yaml_text is None:
        return "ignored"

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return "malformed"

    if not isinstance(parsed, dict):
        return "malformed"
    tasks = parsed.get("tasks")
    if not isinstance(tasks, list):
        return "malformed"

    return tasks


def process_create(board, msg):
    meta = msg["meta"]
    batch = _parse_batch_tasks(msg["body"])

    if isinstance(batch, list):
        # Batch mode: create multiple tasks from body YAML list
        results = []
        ids = []
        for item in batch:
            if not isinstance(item, dict) or "title" not in item:
                continue
            task_id, task = _create_single_task(board, meta, overrides=item)
            ids.append(task_id)
            results.append(f"  {task_id}: {task['title']}")

        if not ids:
            return "[task-create] 일괄 등록 실패: body에 유효한 태스크 없음"

        summary = "\n".join(results)
        send_bot_message(
            msg["room"],
            f"일괄 작업 등록: {ids[0]}~{ids[-1]}",
            f"@{meta['from']} {len(ids)}개 작업이 등록되었습니다.\n{summary}",
            ref=ids[0],
        )
        return f"[task-create] 일괄 {len(ids)}개: {', '.join(ids)}"

    # Single mode: create one task from frontmatter
    task_id, task = _create_single_task(board, meta)
    if msg["body"]:
        task["notes"] = msg["body"]

    extra_note = ""
    if batch == "malformed":
        # body had a tasks: block but YAML parsing failed
        # -> fell back to single-task mode, but warn the author so
        #    they don't silently lose batch entries
        extra_note = (
            "\n\n⚠️ body에 `tasks:` 블록이 있었지만 YAML 파싱에 실패하여 "
            "**단일 태스크로 폴백**했습니다.\n"
            "분할 등록을 원했다면 다음을 확인해 주세요:\n"
            "- `tasks:` 리스트 뒤에 마크다운 헤더(`## ...`)나 자유 텍스트가 있으면 "
            "별도 섹션으로 분리되었는지 (들여쓰기 0 + `#` 시작 라인에서 블록이 끝납니다)\n"
            "- 리스트 아이템의 들여쓰기가 일관된지 (스페이스 2개 권장)\n"
            "- notes 같은 멀티라인 값은 `|` 또는 `>` 로 시작해 블록 스칼라로 쓰는지"
        )

    send_bot_message(
        msg["room"],
        f"작업 등록: {task_id}",
        f"@{meta['from']} 요청한 작업이 등록되었습니다.\n"
        f"- ID: {task_id}\n"
        f"- 제목: {task['title']}\n"
        f"- 담당: {task['assignee']}\n"
        f"- 마감: {task['due']}" + extra_note,
        ref=task_id,
    )
    return f"[task-create] {task_id} - {task['title']}"


def process_claim(board, msg):
    meta = msg["meta"]
    ref = meta.get("ref")

    if not ref:
        send_bot_message(msg["room"], "선점 실패: ref 누락", f"@{meta['from']} task-claim 메시지에 ref 필드가 없습니다. ref: T-NNN 형식으로 대상 태스크 ID를 지정하세요.")
        return "[task-claim] 실패: ref 누락"

    task = find_task(board, ref)

    if not task:
        send_bot_message(msg["room"], f"선점 실패: {ref}", f"@{meta['from']} 작업 {ref}을(를) 찾을 수 없습니다.", ref=ref)
        return f"[task-claim] {ref} - 실패: 없는 작업"

    if task["status"] == "진행" and task["assignee"] != meta.get("from"):
        send_bot_message(msg["room"], f"선점 실패: {ref}", f"@{meta['from']} {ref}은(는) 이미 {task['assignee']}이(가) 진행 중입니다.", ref=ref)
        return f"[task-claim] {ref} - 실패: 이미 진행 중"

    task["assignee"] = meta.get("from")
    task["status"] = "진행"
    task["start"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    send_bot_message(msg["room"], f"선점 완료: {ref}", f"@{meta['from']} {ref} 작업이 배정되었습니다.", ref=ref)
    return f"[task-claim] {ref} -> {task['assignee']}"


def process_update(board, msg):
    meta = msg["meta"]
    ref = meta.get("ref")

    if not ref:
        send_bot_message(msg["room"], "업데이트 실패: ref 누락", f"@{meta['from']} task-update 메시지에 ref 필드가 없습니다. ref: T-NNN 형식으로 대상 태스크 ID를 지정하세요.")
        return "[task-update] 실패: ref 누락"

    task = find_task(board, ref)

    if not task:
        send_bot_message(msg["room"], f"업데이트 실패: {ref}", f"@{meta['from']} 작업 {ref}을(를) 찾을 수 없습니다.", ref=ref)
        return f"[task-update] {ref} - 실패: 없는 작업"

    updatable_fields = ("status", "assignee", "priority", "due", "notes", "title", "goal")
    for field in updatable_fields:
        if field in meta:
            task[field] = meta[field]
    if meta.get("status") == "진행" and not task.get("start"):
        task["start"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    send_bot_message(msg["room"], f"업데이트 완료: {ref}", f"@{meta['from']} {ref} 작업이 업데이트되었습니다.", ref=ref)
    return f"[task-update] {ref} - {task['status']}"


def process_done(board, msg):
    meta = msg["meta"]
    ref = meta.get("ref")

    if not ref:
        send_bot_message(msg["room"], "완료 처리 실패: ref 누락", f"@{meta['from']} task-done 메시지에 ref 필드가 없습니다. ref: T-NNN 형식으로 대상 태스크 ID를 지정하세요.")
        return "[task-done] 실패: ref 누락"

    task = find_task(board, ref)

    if not task:
        send_bot_message(msg["room"], f"완료 처리 실패: {ref}", f"@{meta['from']} 작업 {ref}을(를) 찾을 수 없습니다.", ref=ref)
        return f"[task-done] {ref} - 실패: 없는 작업"

    task["status"] = "완료"
    task["done"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if msg["body"]:
        # Append to existing notes instead of overwriting
        existing = task.get("notes") or ""
        separator = "\n\n---\n\n" if existing else ""
        task["notes"] = existing + separator + msg["body"]

    send_bot_message(msg["room"], f"완료 처리: {ref}", f"@{meta['from']} {ref} 작업이 완료 처리되었습니다.", ref=ref)
    return f"[task-done] {ref} - 완료"


PROCESSORS = {
    "task-create": process_create,
    "task-claim": process_claim,
    "task-update": process_update,
    "task-done": process_done,
}


def run():
    board = load_board()
    read_status = load_read_status()
    messages = scan_all_rooms(read_status)

    if not messages:
        print("[봇] 처리할 새 메시지 없음.")
        return

    results = []
    for msg in messages:
        msg_type = msg["meta"].get("type")
        processor = PROCESSORS.get(msg_type)
        if processor:
            result = processor(board, msg)
            results.append(result)
        read_status[msg["room"]] = msg["file"]

    save_board(board)
    save_read_status(read_status)

    print(f"[봇] {len(messages)}개 메시지 처리 완료:")
    for r in results:
        print(f"  {r}")


if __name__ == "__main__":
    run()
