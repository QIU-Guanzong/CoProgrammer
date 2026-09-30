from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from coprogrammer import cli, collaboration as co, mcp_server


class CollaborationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name).resolve()
        self.path = self.cwd / ".coprogrammer" / "events.jsonl"
        self.ctx = mcp_server.ManagerContext(self.cwd)
        self.a = co.register(self.path, self.cwd, "codex-1", "codex", "api-42")
        self.b = co.register(self.path, self.cwd, "claude-1", "claude", "api-42")

    def send(self, **kwargs):
        return co.send(self.path, self.cwd, "codex-1", "claude-1", "api-42", "Please review the API.", **kwargs)

    def tool(self, name, **args):
        return mcp_server.handle_request(self.ctx, {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args}})

    def test_registration_is_per_window_not_per_brand(self):
        co.register(self.path, self.cwd, "codex-2", "codex", "tests-42", provider="openai", model="chosen-model")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            co.register(self.path, self.cwd, "codex-1", "claude", "other")
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(len(co.sync(self.path)["sessions"]), 3)

    def test_nested_operations_see_pending_state_and_remain_recoverable(self):
        from coprogrammer.manager_store import transaction
        with transaction(self.path):
            co.register(self.path, self.cwd, "nested", "codex", "api-42")
            co.pulse(self.path, self.cwd, "nested", status="blocked", task="waiting")
            co.pulse(self.path, self.cwd, "nested", status="working")
            first = co.send(self.path, self.cwd, "nested", "claude-1", "api-42", "Nested message", key="nested-key")
            second = co.send(self.path, self.cwd, "nested", "claude-1", "api-42", "Nested message", key="nested-key")
            self.assertTrue(second["duplicate"])
            ack = co.acknowledge(self.path, self.cwd, "claude-1", first["message"]["id"])
            duplicate_ack = co.acknowledge(self.path, self.cwd, "claude-1", first["message"]["id"])
            self.assertEqual(ack["acknowledged_at"], duplicate_ack["acknowledged_at"])
            self.assertTrue(duplicate_ack["duplicate"])
        sessions, messages = co.reconstruct(cli.load_events(self.path))
        self.assertEqual(sessions["nested"]["task"], "waiting")
        self.assertEqual(len(messages), 1)
        self.assertEqual(co.sync(self.path, "claude-1")["pending_total"], 0)

    def test_nested_duplicate_registration_aborts_entire_transaction(self):
        from coprogrammer.manager_store import transaction
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            with transaction(self.path):
                co.register(self.path, self.cwd, "duplicate", "codex", "one")
                co.register(self.path, self.cwd, "duplicate", "codex", "two")
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_same_label_lease_conflicts_remain_visible(self):
        leases = {}
        for pattern in ("src/**", "src/api/**"):
            lease = cli.new_lease("codex", "path", [pattern])
            leases[lease["id"]] = lease
        conflicts = cli.lease_overlap_pairs(leases)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["left_holder"], conflicts[0]["right_holder"])

    def test_freshness_is_not_the_reported_work_status(self):
        seen = co.timestamp(self.a["last_seen"])
        self.assertEqual(co.freshness(self.a, seen + timedelta(seconds=299)), "fresh")
        self.assertEqual(co.freshness(self.a, seen + timedelta(seconds=300)), "stale")
        self.assertEqual(co.freshness(self.a, seen - timedelta(seconds=1)), "unknown")
        updated = co.pulse(self.path, self.cwd, "codex-1", "blocked", note="Waiting for API decision")
        self.assertEqual(updated["status"], "blocked")
        self.assertEqual(updated["freshness"], "fresh")

    def test_closed_session_cannot_restart_or_receive_new_work(self):
        message = self.send()["message"]
        co.pulse(self.path, self.cwd, "claude-1", "closed")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            co.pulse(self.path, self.cwd, "claude-1")
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.send()
        self.assertEqual(before, self.path.read_bytes())
        # Late receipt remains possible; closing does not discard an inbox.
        self.assertEqual(len(co.inbox(self.path, "claude-1")["messages"]), 1)
        co.acknowledge(self.path, self.cwd, "claude-1", message["id"])

    def test_concurrent_retries_store_one_message_and_reject_changed_content(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.send(key="handoff-42"), range(8)))
        self.assertEqual(sum(not r["duplicate"] for r in results), 1)
        self.assertEqual(len({r["message"]["id"] for r in results}), 1)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "different content"):
            co.send(self.path, self.cwd, "codex-1", "claude-1", "api-42", "Changed", key="handoff-42")
        self.assertEqual(before, self.path.read_bytes())

    def test_inbox_is_read_only_and_ack_is_recipient_specific_and_idempotent(self):
        sent = self.send()["message"]
        before = self.path.read_bytes()
        for _ in range(2):
            self.assertEqual(co.inbox(self.path, "claude-1")["pending_total"], 1)
        with self.assertRaisesRegex(RuntimeError, "recipient"):
            co.acknowledge(self.path, self.cwd, "codex-1", sent["id"])
        self.assertEqual(before, self.path.read_bytes())
        first = co.acknowledge(self.path, self.cwd, "claude-1", sent["id"])
        after = self.path.read_bytes()
        second = co.acknowledge(self.path, self.cwd, "claude-1", sent["id"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(after, self.path.read_bytes())
        self.assertEqual(co.inbox(self.path, "claude-1")["messages"], [])
        self.assertEqual(len(co.inbox(self.path, "claude-1", include_acked=True)["messages"]), 1)

    def test_reply_must_keep_task_and_participants(self):
        parent = self.send()["message"]
        reply = co.send(self.path, self.cwd, "claude-1", "codex-1", "api-42", "Reviewed", reply_to=parent["id"])
        self.assertEqual(reply["message"]["reply_to"], parent["id"])
        co.register(self.path, self.cwd, "other", "opencode", "api-42", provider="glm")
        before = self.path.read_bytes()
        for sender, task in (("other", "api-42"), ("claude-1", "other-task")):
            with self.assertRaisesRegex(RuntimeError, "original task and participants"):
                co.send(self.path, self.cwd, sender, "codex-1", task, "Reply", reply_to=parent["id"])
        self.assertEqual(before, self.path.read_bytes())

    def test_sync_pagination_and_unread_snapshot_survive_cursor_advancement(self):
        sent = [self.send()["message"] for _ in range(3)]
        cursor, observed = "", []
        for _ in range(10):
            page = co.sync(self.path, "claude-1", cursor, limit=1)
            observed.extend(e["id"] for e in page["changes"])
            cursor = page["next_cursor"]
            if not page["has_more"]:
                break
        self.assertEqual(observed, [e["id"] for e in cli.load_events(self.path)])
        page = co.sync(self.path, "claude-1", cursor)
        self.assertEqual(page["changes"], [])
        self.assertEqual(page["pending_total"], 3)
        self.assertEqual(len(page["inbox"]), 3)
        co.acknowledge(self.path, self.cwd, "claude-1", sent[0]["id"])
        page = co.sync(self.path, "codex-1", cursor)
        self.assertEqual(page["changes"][0]["type"], "message.acknowledged")
        with self.assertRaisesRegex(RuntimeError, "unknown sync cursor"):
            co.sync(self.path, after="evt_missing")

    def test_inbox_filters_and_pages_do_not_drop_pending_messages(self):
        expected = [self.send()["message"]["id"] for _ in range(3)]
        co.send(self.path, self.cwd, "codex-1", "claude-1", "another", "Other task")
        page = co.inbox(self.path, "claude-1", task="api-42", limit=2)
        self.assertTrue(page["has_more"])
        second = co.inbox(self.path, "claude-1", task="api-42", after=page["next_cursor"], limit=2)
        self.assertEqual([m["id"] for m in page["messages"] + second["messages"]], expected)
        self.assertFalse(second["has_more"])
        self.assertEqual(second["pending_total"], 4)

    def test_unrelated_sync_does_not_return_message_bodies(self):
        self.send()
        co.register(self.path, self.cwd, "other", "copilot", "other")
        for session in ("other", ""):
            output = co.sync(self.path, session)
            self.assertNotIn("Please review", json.dumps(output))

    def test_wrong_worktree_cannot_pulse_send_or_ack_for_session(self):
        other = self.cwd / "other"
        other.mkdir()
        sent = self.send()["message"]
        before = self.path.read_bytes()
        operations = (
            lambda: co.pulse(self.path, other, "codex-1"),
            lambda: co.send(self.path, other, "codex-1", "claude-1", "api-42", "Wrong cwd"),
            lambda: co.acknowledge(self.path, other, "claude-1", sent["id"]),
        )
        for operation in operations:
            with self.assertRaisesRegex(RuntimeError, "different worktree"):
                operation()
        self.assertEqual(before, self.path.read_bytes())

    def test_malformed_requests_and_history_fail_without_writes(self):
        before = self.path.read_bytes()
        invalid = [
            ("session_register", {"session": "bad/id", "client": "claude", "task": "x"}),
            ("session_register", {"session": "new", "client": "claude", "task": "x", "ttl_seconds": True}),
            ("session_pulse", {"session": "codex-1", "status": "alive"}),
            ("message_send", {"sender": "codex-1", "recipient": "claude-1", "task": "x", "body": "x" * 16001}),
            ("message_send", {"sender": "codex-1", "recipient": "missing", "task": "x", "body": "x"}),
            ("manager_sync", {"session": "missing"}),
            ("message_inbox", {"session": "claude-1", "limit": 0}),
        ]
        for name, args in invalid:
            result = self.tool(name, **args)
            self.assertTrue("error" in result or result["result"].get("isError"), result)
        self.assertEqual(before, self.path.read_bytes())
        malformed = cli.make_event("message.sent", "codex-1", "task:x", {"message": []})
        self.path.write_bytes(before + (json.dumps(malformed) + "\n").encode())
        with self.assertRaisesRegex(RuntimeError, "invalid message record"):
            co.sync(self.path)
        self.assertEqual(self.path.read_bytes(), before + (json.dumps(malformed) + "\n").encode())

    def test_semantically_corrupt_history_is_rejected(self):
        event = cli.make_event("message.acknowledged", "codex-1", "task:x",
                               {"recipient": "codex-1", "message_id": "msg_missing"})
        cli.append_event(self.path, event)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "acknowledgement history"):
            self.send()
        self.assertEqual(before, self.path.read_bytes())

    def test_cli_message_and_mcp_inbox_share_state(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli.main(["manager", "message", "send", "--cwd", str(self.cwd),
                             "--from", "codex-1", "--to", "claude-1", "--task", "api-42",
                             "--kind", "handoff", "--body", "接口变更待审阅", "--key", "cli-42"])
        self.assertEqual(code, 0)
        message_id = json.loads(stdout.getvalue())["message"]["id"]
        response = self.tool("message_inbox", session="claude-1")
        inbox = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(inbox["messages"][0]["id"], message_id)
        self.assertEqual(inbox["messages"][0]["body"], "接口变更待审阅")

    def test_raw_cli_cannot_bypass_message_state_checks(self):
        before = self.path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            result = cli.main(["manager", "event", "append", "--cwd", str(self.cwd),
                               "--type", "message.acknowledged", "--actor", "codex-1"])
        self.assertEqual(result, 2)
        self.assertEqual(before, self.path.read_bytes())

    def test_existing_status_commands_include_directory_without_message_bodies(self):
        self.send()
        result = self.tool("manager_status")
        status = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(len(status["sessions"]), 2)
        self.assertEqual(status["pending_messages"], 1)
        self.assertNotIn("Please review", json.dumps(status))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = cli.main(["manager", "status", "--cwd", str(self.cwd), "--json"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), status)

    def test_body_file_unicode_errors_and_oversize_do_not_write(self):
        body = self.cwd / "message.txt"
        before = self.path.read_bytes()
        for content in (b'\xff', b'x' * 16001):
            body.write_bytes(content)
            with contextlib.redirect_stderr(io.StringIO()):
                result = cli.main(["manager", "message", "send", "--cwd", str(self.cwd),
                                   "--from", "codex-1", "--to", "claude-1", "--task", "api-42",
                                   "--body-file", str(body)])
            self.assertEqual(result, 2)
        self.assertEqual(before, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
