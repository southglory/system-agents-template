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
        meta, body = parse_frontmatter(room_dir / fname)
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


def send_bot_message(room, subject, body, ref=None):
    room_dir = CHATROOMS / room
    room_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y-%m-%d_%H%M%S") + "_bot.md"

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


def process_create(board, msg):
    meta = msg["meta"]
    task_id = next_task_id(board)

    task = {
        "id": task_id,
        "title": meta.get("subject", ""),
        "goal": meta.get("goal", ""),
        "phase": meta.get("phase", ""),
        "type": meta.get("task_type", "feature"),
        "priority": meta.get("priority", "medium"),
        "created_by": meta.get("from", ""),
        "assignee": meta.get("assignee", ""),
        "start": None,
        "due": meta.get("due"),
        "done": None,
        "status": "대기",
        "notes": msg["body"] if msg["body"] else None,
    }
    board.setdefault("tasks", []).append(task)

    send_bot_message(
        msg["room"],
        f"작업 등록: {task_id}",
        f"@{meta['from']} 요청한 작업이 등록되었습니다.\n"
        f"- ID: {task_id}\n"
        f"- 제목: {task['title']}\n"
        f"- 담당: {task['assignee']}\n"
        f"- 마감: {task['due']}",
        ref=task_id,
    )
    return f"[task-create] {task_id} - {task['title']}"


def process_claim(board, msg):
    meta = msg["meta"]
    ref = meta.get("ref")
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
    task = find_task(board, ref)

    if not task:
        send_bot_message(msg["room"], f"업데이트 실패: {ref}", f"@{meta['from']} 작업 {ref}을(를) 찾을 수 없습니다.", ref=ref)
        return f"[task-update] {ref} - 실패: 없는 작업"

    if "status" in meta:
        task["status"] = meta["status"]
    if "assignee" in meta:
        task["assignee"] = meta["assignee"]
    if meta.get("status") == "진행" and not task.get("start"):
        task["start"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    send_bot_message(msg["room"], f"업데이트 완료: {ref}", f"@{meta['from']} {ref} 작업이 업데이트되었습니다.", ref=ref)
    return f"[task-update] {ref} - {task['status']}"


def process_done(board, msg):
    meta = msg["meta"]
    ref = meta.get("ref")
    task = find_task(board, ref)

    if not task:
        send_bot_message(msg["room"], f"완료 처리 실패: {ref}", f"@{meta['from']} 작업 {ref}을(를) 찾을 수 없습니다.", ref=ref)
        return f"[task-done] {ref} - 실패: 없는 작업"

    task["status"] = "완료"
    task["done"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
