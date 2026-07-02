"""Tests for round_loop.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from round_loop import (  # type: ignore
    discover_agents,
    missing_turn_ends,
    parse_agent_list,
    snapshot_turn_ends,
    wait_for_turn_ends,
)


def _write_agent(root: Path, name: str, filename: str = "role.md") -> None:
    path = root / "agents" / name / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {name}\n", encoding="utf-8")


def _write_message(
    root: Path,
    room: str,
    filename: str,
    sender: str,
    message_type: str = "turn-end",
) -> None:
    path = root / "chatrooms" / room / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f"from: {sender}",
                "to: all",
                "time: 2026-03-19 14:30:52 UTC",
                f"type: {message_type}",
                "subject: done",
                "---",
                "",
                "done",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class TestRoundLoop(unittest.TestCase):
    def test_parse_agent_list(self):
        self.assertEqual(parse_agent_list("alice,bob"), ["alice", "bob"])
        self.assertEqual(parse_agent_list(" alice, ,bob "), ["alice", "bob"])
        self.assertIsNone(parse_agent_list(None))

    def test_discover_agents_excludes_bootstrap_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_agent(root, "_example")
            _write_agent(root, "recruiter")
            _write_agent(root, "antigravity")
            _write_agent(root, "alice")
            _write_agent(root, "bob", "CLAUDE.md")

            self.assertEqual(discover_agents(root), ["alice", "bob"])
            self.assertEqual(
                discover_agents(root, include_stock=True),
                ["alice", "antigravity", "bob", "recruiter"],
            )

    def test_snapshot_turn_ends_filters_by_type_and_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_message(root, "general", "2026-03-19_143052_alice.md", "alice")
            _write_message(
                root,
                "general",
                "2026-03-19_143053_bob.md",
                "bob",
                message_type="message",
            )

            seen = snapshot_turn_ends(root, ["alice", "bob"])

            self.assertEqual(
                seen["alice"],
                {"chatrooms/general/2026-03-19_143052_alice.md"},
            )
            self.assertEqual(seen["bob"], set())

    def test_missing_turn_ends_uses_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_message(root, "general", "2026-03-19_143052_alice.md", "alice")
            baseline = snapshot_turn_ends(root, ["alice"])

            self.assertEqual(missing_turn_ends(root, ["alice"], baseline), ["alice"])

            _write_message(root, "general", "2026-03-19_143053_alice.md", "alice")
            self.assertEqual(missing_turn_ends(root, ["alice"], baseline), [])

    def test_wait_for_turn_ends_times_out_with_missing_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = snapshot_turn_ends(root, ["alice"])

            missing = wait_for_turn_ends(
                root=root,
                agents=["alice"],
                baseline=baseline,
                poll_seconds=0,
                timeout_seconds=0.001,
                sleeper=lambda _seconds: None,
                monotonic=iter([0.0, 1.0]).__next__,
            )

            self.assertEqual(missing, ["alice"])


if __name__ == "__main__":
    unittest.main()
