# System Agents Template

This repository defines a file-based, turn-based multi-agent protocol.

## Codex Guidance

- Treat `chatrooms/PROTOCOL.md` and `tasks/PROTOCOL.md` as the source of truth.
- `tasks/board.yaml` is read-only for agents. Do not edit it directly. Send a `task-create`, `task-update`, `task-claim`, or `task-done` message instead.
- Chatroom messages are append-only. Do not edit an existing message file; write a new message file to correct or supersede it.
- When acting as an agent turn, prefer the `$system-agents-turn` skill if it is available.
- Keep platform-neutral protocol behavior in `chatrooms/`, `tasks/`, and `bot/`. Keep model or client adapters in platform-specific folders such as `.claude/`, `.codex/`, and `.agents/skills/`.

## Validation

- After changing task parsing or turn-bot behavior, run `python -m unittest bot/test_turn_bot.py -v`.
- After changing the Codex protocol guard, run `python -m unittest bot/test_codex_chat_guard.py -v`.
- After changing the updater, run `pytest bot/tests -q`.
