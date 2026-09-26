from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from coprogrammer import channels, cli, collaboration as co
from coprogrammer.manager_store import transaction


class ChannelTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name).resolve()
        self.path = self.cwd / ".coprogrammer" / "events.jsonl"
        for session, client in (("codex", "codex"), ("claude", "claude"),
                                ("other", "copilot"), ("fourth", "opencode")):
            co.register(self.path, self.cwd, session, client, "api-42")
        self.cursor = co.sync(self.path, "claude")["next_cursor"]

    def send(self, sender="codex", recipient="claude", task="api-42", body="Review API", **kwargs):
        return co.send(self.path, self.cwd, sender, recipient, task, body, **kwargs)["message"]

    def test_timeout_preserves_log_pulse_and_cursor(self):
        before = self.path.read_bytes()
        started = time.monotonic()
        result = channels.wait(self.path, "claude", self.cursor, timeout_seconds=0.03)
        self.assertGreaterEqual(time.monotonic() - started, 0.03)
        self.assertEqual(result["wait_status"], "timeout")
        self.assertEqual(result["next_cursor"], self.cursor)
        self.assertEqual(result["cursor"], self.cursor)
        self.assertEqual(self.path.read_bytes(), before)

    def test_wait_requires_existing_cursor_and_bounded_inputs(self):
        before = self.path.read_bytes()
        for cursor in ("", "evt_missing", None):
            with self.subTest(cursor=cursor), self.assertRaises(RuntimeError):
                channels.wait(self.path, "claude", cursor, timeout_seconds=0)
        for timeout in (-1, 26, True, "1", float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaisesRegex(RuntimeError, "timeout_seconds"):
                channels.wait(self.path, "claude", self.cursor, timeout_seconds=timeout)
        with self.assertRaisesRegex(RuntimeError, "unknown session"):
            channels.wait(self.path, "missing", self.cursor, timeout_seconds=0)
        with self.assertRaisesRegex(RuntimeError, "limit"):
            channels.wait(self.path, "claude", self.cursor, timeout_seconds=0, limit=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_delayed_delivery_can_write_while_receiver_waits(self):
        # Signal exactly when the waiter sleeps, then write in another thread.
        # Holding a transaction across sleep would deadlock or fail this test.
        sleeping = threading.Event()
        real_sleep = time.sleep

        def sleep(seconds):
            sleeping.set()
            real_sleep(seconds)

        with ThreadPoolExecutor(max_workers=2) as pool:
            with mock.patch.object(channels.time, "sleep", side_effect=sleep):
                waiting = pool.submit(channels.wait, self.path, "claude", self.cursor, 2)
                self.assertTrue(sleeping.wait(1))
                with transaction(self.path, timeout=0.2):
                    message = self.send()
                result = waiting.result(timeout=3)
        self.assertEqual(result["wait_status"], "changed")
        self.assertEqual(result["inbox"][0]["id"], message["id"])
        self.assertIsNone(co.inbox(self.path, "claude")["messages"][0]["acknowledged_at"])

    def test_seen_but_unacknowledged_message_returns_pending_immediately(self):
        message = self.send()
        cursor = co.sync(self.path, "claude")["next_cursor"]
        before = self.path.read_bytes()
        with mock.patch.object(channels.time, "sleep", side_effect=AssertionError("must not sleep")):
            result = channels.wait(self.path, "claude", cursor, timeout_seconds=25)
        self.assertEqual(result["wait_status"], "pending")
        self.assertEqual(result["inbox"][0]["id"], message["id"])
        self.assertEqual(before, self.path.read_bytes())
        co.acknowledge(self.path, self.cwd, "claude", message["id"])
        cursor = co.sync(self.path, "claude")["next_cursor"]
        result = channels.wait(self.path, "claude", cursor, timeout_seconds=0)
        self.assertEqual(result["wait_status"], "timeout")
        self.assertEqual(result["inbox"], [])

    def test_hidden_message_pages_advance_cursor_without_wakeup_or_body_leak(self):
        hidden = [self.send("other", "fourth", body="PRIVATE hidden content") for _ in range(2)]
        before = self.path.read_bytes()
        with mock.patch.object(channels, "POLL_SECONDS", 0.01):
            result = channels.wait(self.path, "claude", self.cursor, timeout_seconds=0.05, limit=1)
        self.assertEqual(result["wait_status"], "timeout")
        self.assertEqual(result["next_cursor"], hidden[-1]["event_id"])
        self.assertFalse(result["has_more"])
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(before, self.path.read_bytes())

    def test_hidden_backlog_is_bounded_and_relevant_later_page_is_preserved(self):
        hidden = [self.send("other", "fourth", body="PRIVATE") for _ in range(3)]
        message = self.send("claude", "codex", body="Relevant outbound")
        first = channels.wait(self.path, "claude", self.cursor, timeout_seconds=0, limit=1)
        self.assertEqual(first["wait_status"], "timeout")
        self.assertEqual(first["next_cursor"], hidden[0]["event_id"])
        self.assertTrue(first["has_more"])
        with mock.patch.object(channels, "POLL_SECONDS", 0.01):
            second = channels.wait(self.path, "claude", first["next_cursor"], timeout_seconds=1, limit=1)
        self.assertEqual(second["wait_status"], "changed")
        self.assertEqual(second["changes"][0]["id"], message["event_id"])
        self.assertNotIn("PRIVATE", json.dumps(second))

    def test_session_expiry_wakes_without_appended_event(self):
        before = self.path.read_bytes()
        original = co.freshness
        future = datetime.now(timezone.utc) + timedelta(seconds=301)
        with mock.patch.object(channels.time, "sleep") as sleep:
            def freshness(session):
                return original(session, future) if sleep.called else original(session)
            with mock.patch.object(co, "freshness", side_effect=freshness):
                result = channels.wait(self.path, "claude", self.cursor, timeout_seconds=1)
        self.assertEqual(result["wait_status"], "changed")
        self.assertEqual(result["changes"], [])
        self.assertEqual({s["freshness"] for s in result["sessions"]}, {"stale"})
        self.assertEqual(before, self.path.read_bytes())

    def test_lease_expiry_wakes_without_appended_event(self):
        lease = cli.new_lease("codex", "path", ["src/**"])
        lease["status"] = "active"
        lease["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        cli.append_event(self.path, cli.make_event("lease.granted", "manager", "repo:test", {"lease": lease}))
        cursor = co.sync(self.path, "claude")["next_cursor"]
        before = self.path.read_bytes()
        now = datetime.now(timezone.utc)
        with mock.patch.object(channels.time, "sleep") as sleep:
            with mock.patch.object(cli, "datetime") as clock:
                clock.fromisoformat = datetime.fromisoformat
                clock.now.side_effect = lambda _: now + timedelta(seconds=31 if sleep.called else 0)
                result = channels.wait(self.path, "claude", cursor, timeout_seconds=1)
        self.assertEqual(result["wait_status"], "changed")
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["active_leases"], [])
        self.assertEqual(before, self.path.read_bytes())

    def test_thread_includes_both_directions_ack_and_only_participant_messages(self):
        first = self.send()
        reply = self.send("claude", "codex", body="Reviewed", reply_to=first["id"])
        co.acknowledge(self.path, self.cwd, "claude", first["id"])
        self.send("other", "fourth", body="PRIVATE same task")
        self.send("codex", "claude", task="another", body="PRIVATE other task")
        before = self.path.read_bytes()
        result = channels.thread(self.path, "claude", "api-42")
        self.assertEqual([m["id"] for m in result["messages"]], [first["id"], reply["id"]])
        self.assertTrue(result["messages"][0]["acknowledged_at"])
        self.assertIsNone(result["messages"][1]["acknowledged_at"])
        self.assertEqual(result["total"], 2)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(before, self.path.read_bytes())

    def test_thread_cursor_pagination_and_closed_session_read(self):
        expected = [self.send()["id"] for _ in range(3)]
        first = channels.thread(self.path, "claude", "api-42", limit=2)
        self.assertTrue(first["has_more"])
        co.pulse(self.path, self.cwd, "claude", status="closed")
        second = channels.thread(self.path, "claude", "api-42", after=first["next_cursor"], limit=2)
        self.assertEqual([m["id"] for m in first["messages"] + second["messages"]], expected)
        self.assertFalse(second["has_more"])
        self.assertEqual(second["total"], 3)
        for kwargs in ({"after": "missing"}, {"limit": 0}, {"after": None}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):
                channels.thread(self.path, "claude", "api-42", **kwargs)
        with self.assertRaises(RuntimeError):
            channels.thread(self.path, "missing", "api-42")
        with self.assertRaises(RuntimeError):
            channels.thread(self.path, "claude", "")


if __name__ == "__main__":
    unittest.main()
