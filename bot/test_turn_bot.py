"""
Unit tests for turn-bot.py — focused on the `_parse_batch_tasks` pipeline.

Run with:
    python -m unittest bot/test_turn_bot.py -v

No external deps beyond `pyyaml` (already required by turn-bot).
"""

import unittest

# turn-bot.py is alongside this file; import by module name
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from turn_bot import _parse_batch_tasks, _extract_tasks_block  # type: ignore


class TestExtractTasksBlock(unittest.TestCase):
    def test_simple_block(self):
        body = "tasks:\n  - title: A\n  - title: B\n"
        out = _extract_tasks_block(body)
        self.assertEqual(out.strip(), "tasks:\n  - title: A\n  - title: B")

    def test_preceded_by_prose(self):
        body = "Intro paragraph.\n\ntasks:\n  - title: A\n"
        out = _extract_tasks_block(body)
        self.assertIn("tasks:", out)
        self.assertIn("title: A", out)

    def test_stops_at_markdown_heading(self):
        body = (
            "tasks:\n"
            "  - title: A\n"
            "  - title: B\n"
            "\n"
            "## Notes\n"
            "- extra prose that is NOT part of the tasks list\n"
        )
        out = _extract_tasks_block(body)
        self.assertIn("title: A", out)
        self.assertIn("title: B", out)
        # the prose after `## Notes` must be excluded
        self.assertNotIn("Notes", out)
        self.assertNotIn("extra prose", out)

    def test_no_tasks_returns_none(self):
        self.assertIsNone(_extract_tasks_block("just a message"))
        self.assertIsNone(_extract_tasks_block(""))
        self.assertIsNone(_extract_tasks_block(None))

    def test_inline_tasks_word_does_not_match(self):
        # `tasks:` must be at column 0, not inside prose
        body = "This document lists the tasks: A, B, C."
        self.assertIsNone(_extract_tasks_block(body))


class TestParseBatchTasks(unittest.TestCase):
    def test_valid_batch(self):
        body = (
            "Please register these:\n\n"
            "tasks:\n"
            "  - title: First task\n"
            "    assignee: alice\n"
            "  - title: Second task\n"
            "    assignee: bob\n"
        )
        result = _parse_batch_tasks(body)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "First task")
        self.assertEqual(result[1]["assignee"], "bob")

    def test_valid_batch_with_trailing_markdown(self):
        """
        Regression test: the original bug.

        A body that has a valid tasks: YAML list followed by a
        markdown `## Section` and a prose bullet list used to
        fail YAML parsing and silently fall back to single-task mode.
        """
        body = (
            "Intro.\n\n"
            "tasks:\n"
            "  - title: task A\n"
            "    notes: |\n"
            "      multi\n"
            "      line\n"
            "  - title: task B\n"
            "\n"
            "## 우선순위 & 의존성\n"
            "\n"
            "- A is independent\n"
            "- B depends on A\n"
        )
        result = _parse_batch_tasks(body)
        self.assertIsInstance(result, list, f"expected list, got {result!r}")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "task A")
        self.assertEqual(result[1]["title"], "task B")

    def test_no_tasks_marker_returns_ignored(self):
        """Body has no `tasks:` — single-task mode is the intent, not an error."""
        self.assertEqual(_parse_batch_tasks("plain body"), "ignored")
        self.assertEqual(_parse_batch_tasks(""), "ignored")
        self.assertEqual(_parse_batch_tasks(None), "ignored")

    def test_malformed_yaml_returns_malformed(self):
        """Body claims to have tasks: but YAML is broken."""
        body = (
            "tasks:\n"
            "  - title: broken\n"
            "    notes: |\n"
            "     bad indent\n"
            "\t- mixed tabs and spaces\n"
        )
        # the bad indent may or may not fail depending on YAML parser;
        # we use a clearly invalid structure instead
        broken = "tasks:\n  - title: x\n : : :\n"
        result = _parse_batch_tasks(broken)
        self.assertEqual(
            result, "malformed",
            f"expected 'malformed', got {result!r}",
        )

    def test_tasks_not_a_list_returns_malformed(self):
        """Top-level has `tasks:` but value isn't a list."""
        body = "tasks: not_a_list\n"
        self.assertEqual(_parse_batch_tasks(body), "malformed")

    def test_tasks_word_inline_returns_ignored(self):
        # `tasks:` inside prose shouldn't trigger parsing
        body = "Here are the tasks: first, second, third."
        self.assertEqual(_parse_batch_tasks(body), "ignored")


if __name__ == "__main__":
    unittest.main()
