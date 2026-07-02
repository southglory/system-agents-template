"""Tests for the Codex system-agents protocol guard."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from codex_chat_guard import (
    ProtocolViolation,
    extract_patch_writes,
    extract_write_intents,
    validate_write,
)


VALID_MESSAGE = """---
from: alice
to: all
time: 2026-03-19 14:30:52 UTC
type: message
subject: Hello
---

Hello.
"""


class TestCodexChatGuard(unittest.TestCase):
    def test_valid_message_write(self):
        validate_write("chatrooms/general/2026-03-19_143052_alice.md", VALID_MESSAGE)

    def test_blocks_board_write(self):
        with self.assertRaises(ProtocolViolation):
            validate_write("tasks/board.yaml", "tasks: []\n")

    def test_requires_ref_for_task_claim(self):
        content = VALID_MESSAGE.replace("type: message", "type: task-claim")
        with self.assertRaises(ProtocolViolation):
            validate_write("chatrooms/general/2026-03-19_143052_alice.md", content)

    def test_blocks_existing_message_update(self):
        with self.assertRaises(ProtocolViolation):
            validate_write("chatrooms/general/2026-03-19_143052_alice.md", None, "update")

    def test_extracts_add_file_patch_content(self):
        patch = """*** Begin Patch
*** Add File: chatrooms/general/2026-03-19_143052_alice.md
+---
+from: alice
+to: all
+time: 2026-03-19 14:30:52 UTC
+type: message
+subject: Hello
+---
+
+Hello.
*** End Patch
"""
        writes = extract_patch_writes(patch)
        self.assertEqual(len(writes), 1)
        path, content, mode = writes[0]
        self.assertEqual(path, "chatrooms/general/2026-03-19_143052_alice.md")
        self.assertEqual(mode, "add")
        self.assertIn("subject: Hello", content)

    def test_extracts_payload_tool_input(self):
        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "chatrooms/general/2026-03-19_143052_alice.md",
                "content": VALID_MESSAGE,
            },
        }
        writes = extract_write_intents(payload)
        self.assertEqual(writes[0][0], "chatrooms/general/2026-03-19_143052_alice.md")


if __name__ == "__main__":
    unittest.main()
