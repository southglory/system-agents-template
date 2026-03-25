# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

A turn-based multi-agent framework built on Claude Code.

Each agent runs as an independent Claude Code session, communicates through chatrooms, and a bot automatically manages the task board.

## Structure

```
system-agents/
├── agents/
│   ├── _example/              ← Agent template
│   │   ├── CLAUDE.md          ← Behavior rules (per Phase)
│   │   └── role.md            ← Role definition
│   └── {AgentName}/           ← Your agents
├── chatrooms/
│   ├── PROTOCOL.md            ← Chat protocol (message types)
│   ├── .read-status/          ← Read status tracking
│   └── general/               ← Shared channel
├── tasks/
│   ├── PROTOCOL.md            ← Task management protocol
│   └── board.yaml             ← Task board (bot-write-only)
├── bot/
│   ├── turn-bot.py            ← Turn bot script
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← Check unread messages
│   ├── check-mentions/        ← Check mentions
│   ├── send-message/          ← Send message (type validation)
│   ├── end-turn/              ← End turn
│   └── report/                ← Auto-share work results
└── README.md
```

## Turn-based Operation

Agents don't run freely in parallel. They execute sequentially in **rounds**.

```
=== Round N ===

[Phase 1: Bot]  Update board.yaml (reflect previous round messages)

[Phase 2: Plan] (agents run sequentially)
  Each agent → read messages + claim tasks (task-claim)

[Phase 3: Bot]  Update board.yaml (reflect claims)

[Phase 4: Execute] (agents run sequentially)
  Each agent → do actual work + send result messages

[Phase 5: Bot]  Update board.yaml (reflect results)

=== Round N+1 ===
```

## Multi-Agent Compatibility (Claude & Antigravity)

This template is designed to support both **Claude Code** and **Antigravity** (Google) agents simultaneously.

- **Claude Code**: Primarily uses `.system-agents/` for turn-based state management and `/skills/` for CLI commands.
- **Antigravity**: Utilizes `.agents/workflows/` for **Turbo-automated** task execution.
- **Collaboration**: Both agents share `board.yaml` (Tasks) and `chatrooms/` (History). Antigravity can follow the turn-based protocol by checking the `board.yaml` before starting work.

## Quick Start

### 1. Install Skills

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. Create Agents

```bash
cp -r agents/_example agents/MyAgent
```

Define the role in `role.md` and rules in `CLAUDE.md`.

### 3. Run a Round

```bash
# Phase 1: Bot
python bot/turn-bot.py

# Phase 2: Each agent plans (auto-detects phase)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 3: Bot
python bot/turn-bot.py

# Phase 4: Each agent executes (auto-detects phase)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 5: Bot
python bot/turn-bot.py
```

## Core Concepts

### Agents
- Run as independent Claude Code sessions
- Plan in Phase 2, execute in Phase 4
- Read-only access to board.yaml — changes go through chat messages

### Chatrooms
- File-based asynchronous messaging
- Message types distinguish conversations from task commands
- Attachment support

### Message Types

| type | Purpose |
|------|---------|
| `message` | General conversation |
| `task-create` | Request new task |
| `task-update` | Change status/assignee |
| `task-done` | Report task completion |
| `task-claim` | Claim a task (Phase 2) |
| `turn-end` | End turn |

### Bot
- Sole write access to board.yaml
- Scans chatroom messages (task-*) and updates board.yaml
- Assigns IDs (T-001) on task-create and sends confirmation

### Skills
- `/check-chatroom {room}` — Check unread messages
- `/check-mentions` — Check messages mentioning you
- `/send-message {room}` — Send message (with type validation)
- `/end-turn` — End your turn
- `/report` — Auto-share work results to relevant chatrooms

## Scenario: Round Play

Alice (frontend) and Bob (backend) building a dashboard together.

### Round 1

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```
> First round. Board is empty.

**Phase 2 — Alice's Turn (Plan)**
```
Alice : Checking chatroom... No new messages.
        Checking board... No tasks.
        We need new tasks.
User  : We need a dashboard. You handle frontend, Bob handles API.
Alice : Sending 2 task-create messages.
        → [general] task-create "Dashboard UI" assignee: alice
        → [general] task-create "Dashboard API" assignee: bob
        /end-turn
```

**Phase 2 — Bob's Turn (Plan)**
```
Bob   : Checking chatroom... Alice created 2 tasks.
        API dev is assigned to me. I'll claim after bot assigns IDs.
        Nothing to do this phase.
        /end-turn
```

**Phase 3 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 2 messages:
  [task-create] T-001 — Dashboard UI
  [task-create] T-002 — Dashboard API
```
> T-001, T-002 registered in board.yaml. Bot notifies in general.

**Phase 4 — Alice's Turn (Execute)**
```
Alice : Checking chatroom... Bot registered T-001, T-002.
        Checking board... T-001 (Dashboard UI) assigned to me, status: pending.
        Starting T-001.
        ... (writing React components) ...
        Basic UI structure done.
User  : Share it.
Alice : /report
        → [general] task-update T-001 status: in-progress "Basic layout done"
        → [alice-bob] message "Please use /api/stats format for the endpoint"
        /end-turn
```

**Phase 4 — Bob's Turn (Execute)**
```
Bob   : Checking chatroom... Alice working on T-001, requested API format.
        Checking board... T-002 (Dashboard API) assigned to me, status: pending.
        Starting T-002 with /api/stats endpoint.
        ... (writing FastAPI endpoints) ...
        API complete.
        /report
        → [general] task-done T-002 "API complete, includes /api/stats"
        → [alice-bob] message "API is up. Call /api/stats"
        /end-turn
```

**Phase 5 — Bot**
```bash
$ python bot/turn-bot.py
[bot] Processed 3 messages:
  [task-update] T-001 — in-progress
  [task-done] T-002 — done
```

### Round 2

**Phase 1 — Bot**
```bash
$ python bot/turn-bot.py
[bot] No new messages to process.
```

**Phase 2 — Alice's Turn**
```
Alice : Checking chatroom... Bob finished API, /api/stats available.
        Checking board... T-001 (UI) in-progress, T-002 (API) done.
        Claiming T-001 to continue.
        → [general] task-claim T-001
        /end-turn
```

**Phase 2 — Bob's Turn**
```
Bob   : Checking chatroom... No new tasks assigned.
        Nothing to do this round.
        /end-turn
```

> Bob has nothing to do — just ends turn. Saves tokens.

**Phase 3 — Bot** → Reflects claim.

**Phase 4 — Alice's Turn**
```
Alice : Integrating API to finish the dashboard.
        ... (fetch + chart rendering) ...
        /report
        → [general] task-done T-001 "API integration complete, dashboard done"
        /end-turn
```

**Phase 4 — Bob's Turn**
```
Bob   : Nothing to do.
        /end-turn
```

**Phase 5 — Bot** → T-001 marked done. All tasks complete!

## Design Principles

1. **Role Separation** — Each agent has a focused responsibility
2. **Turn-based Communication** — Plan → Execute → Report per round
3. **Indirect Mutation** — board.yaml changes only through chat messages
4. **Conflict Prevention** — Agents are append-only, only bot writes board.yaml
5. **Independent Execution** — Each agent works without depending on others

## Support

If you find this project useful, please leave a star! It helps others discover it.

## License

MIT License. Use freely.

## Star History

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
