#!/usr/bin/env python3
"""Round runner for the system-agents turn protocol.

This script owns only phase cadence. It runs the existing turn bot at bot
phases and waits for named agents to append `turn-end` messages during agent
phases. The agents themselves still run in their own Claude/Codex/other
clients and communicate through chatrooms.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable

import yaml

import turn_bot


ROOT = Path(__file__).resolve().parent.parent
CHATROOMS_DIRNAME = "chatrooms"
AGENTS_DIRNAME = "agents"
BOOTSTRAP_AGENTS = {"antigravity", "recruiter"}


class RoundLoopError(RuntimeError):
    """Raised when a round cannot continue."""


def discover_agents(root: Path = ROOT, include_stock: bool = False) -> list[str]:
    """Discover configured project agents.

    Stock/bootstrap agents are excluded by default so a fresh template does not
    wait forever on `recruiter` or the Antigravity template. Pass
    `--include-stock` or `--agents` when those should participate.
    """

    agents_dir = root / AGENTS_DIRNAME
    if not agents_dir.exists():
        return []

    names: list[str] = []
    for child in sorted(agents_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name.startswith("_"):
            continue
        if not include_stock and name in BOOTSTRAP_AGENTS:
            continue
        if (child / "role.md").exists() or (child / "CLAUDE.md").exists():
            names.append(name)
    return names


def parse_agent_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    names = [part.strip() for part in raw.split(",") if part.strip()]
    return names


def _iter_message_files(root: Path) -> list[Path]:
    chatrooms = root / CHATROOMS_DIRNAME
    if not chatrooms.exists():
        return []

    files: list[Path] = []
    for room in sorted(chatrooms.iterdir(), key=lambda p: p.name):
        if not room.is_dir() or room.name.startswith("."):
            continue
        files.extend(sorted(room.glob("*.md"), key=lambda p: p.name))
    return files


def _read_frontmatter(path: Path) -> dict | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def snapshot_turn_ends(root: Path, agents: list[str]) -> dict[str, set[str]]:
    """Return known `turn-end` message keys per agent."""

    expected = set(agents)
    seen: dict[str, set[str]] = {agent: set() for agent in agents}
    for path in _iter_message_files(root):
        meta = _read_frontmatter(path)
        if not meta:
            continue
        sender = str(meta.get("from", ""))
        if meta.get("type") != "turn-end" or sender not in expected:
            continue
        key = path.relative_to(root).as_posix()
        seen[sender].add(key)
    return seen


def missing_turn_ends(
    root: Path,
    agents: list[str],
    baseline: dict[str, set[str]],
) -> list[str]:
    current = snapshot_turn_ends(root, agents)
    missing: list[str] = []
    for agent in agents:
        new_messages = current.get(agent, set()) - baseline.get(agent, set())
        if not new_messages:
            missing.append(agent)
    return missing


def wait_for_turn_ends(
    root: Path,
    agents: list[str],
    baseline: dict[str, set[str]],
    poll_seconds: float,
    timeout_seconds: float | None,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[str]:
    """Wait until all agents have sent a new `turn-end`.

    Returns an empty list on success, or the agents still missing when the
    timeout expires.
    """

    deadline = None
    if timeout_seconds is not None and timeout_seconds > 0:
        deadline = monotonic() + timeout_seconds

    while True:
        missing = missing_turn_ends(root, agents, baseline)
        if not missing:
            return []

        if deadline is None:
            sleeper(poll_seconds)
            continue

        remaining = deadline - monotonic()
        if remaining <= 0:
            return missing
        sleeper(min(poll_seconds, remaining))


def format_agent_prompt(agent: str, phase_number: int, phase_name: str) -> str:
    return (
        f"- {agent}: run its agent turn for Phase {phase_number} "
        f"({phase_name}), then append a turn-end message."
    )


def _run_bot_phase(phase_number: int, label: str, bot_runner: Callable[[], None]) -> None:
    print(f"\n[round-loop] Phase {phase_number}: {label}")
    bot_runner()


def _run_agent_phase(
    root: Path,
    agents: list[str],
    phase_number: int,
    phase_name: str,
    poll_seconds: float,
    timeout_seconds: float | None,
) -> None:
    print(f"\n[round-loop] Phase {phase_number}: {phase_name}")
    for agent in agents:
        print(format_agent_prompt(agent, phase_number, phase_name))
        baseline = snapshot_turn_ends(root, [agent])
        missing = wait_for_turn_ends(
            root=root,
            agents=[agent],
            baseline=baseline,
            poll_seconds=poll_seconds,
            timeout_seconds=timeout_seconds,
        )
        if missing:
            raise RoundLoopError(f"Timed out waiting for turn-end from: {agent}")
        print(f"[round-loop] {agent} ended the phase.")
    print("[round-loop] All agents ended the phase.")


def run_round(
    root: Path,
    agents: list[str],
    poll_seconds: float,
    timeout_seconds: float | None,
    bot_runner: Callable[[], None] = turn_bot.run,
) -> None:
    if not agents:
        raise RoundLoopError(
            "No agents discovered. Add project agents under agents/ or pass "
            "--agents alice,bob."
        )

    _run_bot_phase(1, "Bot updates board", bot_runner)
    _run_agent_phase(root, agents, 2, "Plan", poll_seconds, timeout_seconds)
    _run_bot_phase(3, "Bot reflects claims", bot_runner)
    _run_agent_phase(root, agents, 4, "Execute", poll_seconds, timeout_seconds)
    _run_bot_phase(5, "Bot reflects results", bot_runner)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one system-agents round by coordinating phase cadence."
    )
    parser.add_argument(
        "--agents",
        help="Comma-separated agent names. Defaults to discovered project agents.",
    )
    parser.add_argument(
        "--include-stock",
        action="store_true",
        help="Include stock bootstrap agents such as recruiter and antigravity.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=2.0,
        help="Seconds between chatroom checks while waiting for turn-end.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=0,
        help="Max seconds to wait per agent phase. 0 means wait forever.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    explicit_agents = parse_agent_list(args.agents)
    agents = explicit_agents or discover_agents(ROOT, include_stock=args.include_stock)
    timeout = args.timeout_seconds if args.timeout_seconds > 0 else None

    try:
        run_round(
            root=ROOT,
            agents=agents,
            poll_seconds=args.poll_seconds,
            timeout_seconds=timeout,
        )
    except RoundLoopError as exc:
        print(f"[round-loop] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n[round-loop] Interrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
