# Codex Support

## Decision

Extend this template with a Codex adapter instead of maintaining a separate Codex version.

The durable module is the system-agents protocol: append-only chatrooms, a bot-owned board, task messages, and turn phases. Claude Code, Antigravity, and Codex should be adapters around that protocol, not separate protocol forks.

Fork only if a client needs incompatible task semantics, different board ownership, or a non-file-based transport.

## Layering

- Shared protocol: `chatrooms/PROTOCOL.md`, `tasks/PROTOCOL.md`, `tasks/board.yaml`.
- Shared implementation: `bot/turn_bot.py` and update tooling.
- Claude adapter: per-agent `.claude/` settings, skills, and hooks.
- Codex adapter: `AGENTS.md`, `.agents/skills/system-agents-turn/`, and `.codex/hooks.json`.

This keeps the interface small: agents communicate by writing validated messages, and only the bot mutates the board.

## Hooks, Skills, And Loops

Use hooks for mechanical enforcement:

- block direct writes to `tasks/board.yaml`
- block malformed chatroom message writes
- block edits to existing chatroom messages

Use skills for reusable behavior:

- read messages
- decide the phase
- claim work
- report results

Use loops or automations for cadence:

- run the bot at phase boundaries
- wake a thread to continue a turn loop
- poll for new work or failed checks

Do not put loop mechanics into the protocol itself. The protocol should remain simple enough for any agent client to follow.

## Codex Setup

1. Open Codex at the repository root.
2. Review and trust the project hooks when Codex prompts for hook trust.
3. Use `$system-agents-turn` when asking Codex to act as an agent participant.
4. Run `python bot/turn-bot.py` at bot phases, or wrap it in a local loop script if you want a full round runner.

## Round Loop Runner

`bot/round_loop.py` owns phase cadence without changing the protocol:

- discovers configured project agents, excluding stock bootstrap agents by default
- runs bot phases through the existing `turn_bot.py`
- prompts each agent in order for planning or execution
- waits for that agent to append a fresh `turn-end` before moving on

Example:

```bash
python bot/round_loop.py --agents alice,bob --timeout-seconds 900
```

Keep the agents themselves running in their normal clients. The runner watches
`chatrooms/` and advances only after the phase participants end their turns.
