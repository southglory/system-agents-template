---
name: system-agents-turn
description: Use when Codex is acting as a participant in a system-agents turn-based workflow, reading chatrooms, claiming tasks, executing assigned work, or reporting turn results.
---

# System Agents Turn

Use this workflow when operating inside a repository that contains `chatrooms/`, `tasks/board.yaml`, and the system-agents protocols.

## Before Acting

1. Read `chatrooms/PROTOCOL.md` and `tasks/PROTOCOL.md` if they are not already fresh in context.
2. Determine the current agent name from the current directory, `role.md`, or explicit user instruction.
3. Read `tasks/board.yaml` as state only. Never edit it directly.

## Decide The Phase

- Planning phase: read unread messages, inspect the board, claim work with a `task-claim` message, and stop before code or document edits.
- Execution phase: read bot updates, perform assigned work, report progress or completion, then end the turn.
- If the phase is ambiguous, summarize the latest chatroom and board state and ask the user which phase to run.

## Message Writing

Write messages under `chatrooms/{room}/` using this filename format:

```text
YYYY-MM-DD_HHMMSS_agent.md
```

Use UTC time. Include frontmatter with at least `from`, `to`, `time`, `type`, and `subject`.

For `task-update`, `task-done`, and `task-claim`, include `ref: T-NNN`. The `ref` field is the only task identity the bot uses.

After writing a message, update `chatrooms/.read-status/{agent}.json` so the room points at the message just written.

## Turn Loop

1. Check unread messages in `general` and any relevant 1:1 rooms.
2. Read `tasks/board.yaml`.
3. In planning phase, send claims or task creation requests only.
4. In execution phase, do the assigned work, then send `task-update` or `task-done`.
5. Send a `turn-end` message to `general`.
6. Tell the user what changed and which bot phase should run next.

## Safety Rules

- Do not edit `tasks/board.yaml`.
- Do not edit existing chatroom messages.
- Do not do execution work during planning phase.
- Do not send `task-claim` during execution phase.
- Use hooks as mechanical enforcement, but still follow the protocol intentionally.
