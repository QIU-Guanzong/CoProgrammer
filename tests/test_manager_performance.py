from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from coprogrammer import cli, collaboration as co, scheduler
from coprogrammer.manager_store import transaction


class ManagerSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "events.jsonl"
        self.sender = self.root / "sender"
        self.receiver = self.root / "receiver"
        self.sender.mkdir()
        self.receiver.mkdir()
        co.register(self.path, self.sender, "sender", "codex", "upgrade")
        co.register(self.path, self.receiver, "receiver", "claude", "upgrade")
        scheduler.create(self.path, self.sender, "sender", "upgrade", "Improve snapshots", ["src/**"])

    def messages(self, count=128):
        # One transaction builds a realistic history without making fixture
        # construction itself repeatedly replay that history.
        with transaction(self.path) as current:
            for index in range(count):
                message = {"id": f"msg_{index}", "sender": "sender", "recipient": "receiver",
                           "task": "upgrade", "kind": "update", "body": f"Update {index}",
                           "reply_to": "", "key": ""}
                current.append(cli.make_event("message.sent", "sender", "task:upgrade",
                                              {"message": message}))

    def test_directory_replays_each_collaboration_event_only_once(self):
        self.messages()
        events = cli.load_events(self.path)
        collaboration_count = sum(event["type"] in co.EVENT_TYPES for event in events)
        with mock.patch.object(co, "validate_event", wraps=co.validate_event) as validate:
            result = co.directory(events)
        self.assertEqual(validate.call_count, collaboration_count)
        self.assertEqual(result["pending_messages"], 128)
        self.assertEqual(result["task_counts"], {"queued": 1, "claimed": 0, "done": 0})
        self.assertTrue(result["tasks"][0]["ready"])

    def test_sync_keeps_storage_validation_and_one_collaboration_replay(self):
        self.messages()
        events = cli.load_events(self.path)
        collaboration_count = sum(event["type"] in co.EVENT_TYPES for event in events)
        before = self.path.read_bytes()
        with mock.patch.object(co, "validate_event", wraps=co.validate_event) as validate:
            result = co.sync(self.path, "receiver", limit=50)
        self.assertEqual(validate.call_count, collaboration_count * 2)
        self.assertEqual(result["pending_total"], 128)
        self.assertEqual(len(result["inbox"]), 50)
        self.assertTrue(result["inbox_has_more"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_standalone_task_board_still_validates_collaboration_history(self):
        self.messages()
        events = cli.load_events(self.path)
        with mock.patch.object(co, "reconstruct", wraps=co.reconstruct) as reconstruct:
            tasks = scheduler.board(events)
        self.assertEqual(reconstruct.call_count, 1)
        self.assertEqual(tasks, co._snapshot(events)[2])

    def test_all_snapshot_views_reject_invalid_collaboration_history(self):
        self.messages(1)
        # Storage validation accepts this well-formed record; history validation
        # must still reject its duplicate message identity in every entry point.
        events = cli.load_events(self.path)
        cli.append_event(self.path, events[-1])
        events = cli.load_events(self.path)
        for read in (lambda: co._snapshot(events), lambda: co.directory(events),
                     lambda: co.sync(self.path, "receiver"), lambda: scheduler.board(events)):
            with self.subTest(read=read), self.assertRaisesRegex(RuntimeError, "duplicate ID"):
                read()

    def test_combined_snapshot_still_rejects_invalid_task_history(self):
        events = cli.load_events(self.path)
        cli.append_event(self.path, events[-1])
        events = cli.load_events(self.path)
        for read in (lambda: co.directory(events), lambda: co.sync(self.path, "receiver")):
            with self.subTest(read=read), self.assertRaisesRegex(RuntimeError, "duplicate task"):
                read()

    def test_nested_transaction_snapshots_see_new_pending_events(self):
        before = self.path.read_bytes()
        with transaction(self.path):
            first = co.sync(self.path, "receiver")
            message = co.send(self.path, self.sender, "sender", "receiver", "upgrade", "Ready")
            second = co.sync(self.path, "receiver", after=first["next_cursor"])
            self.assertEqual(first["pending_total"], 0)
            self.assertEqual(second["pending_total"], 1)
            self.assertEqual(second["inbox"][0]["id"], message["message"]["id"])
            self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(co.sync(self.path, "receiver")["pending_total"], 1)

    def test_failed_nested_transaction_does_not_leave_snapshot_state(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with transaction(self.path):
                co.send(self.path, self.sender, "sender", "receiver", "upgrade", "Discard")
                self.assertEqual(co.sync(self.path, "receiver")["pending_total"], 1)
                raise RuntimeError("abort")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(co.sync(self.path, "receiver")["pending_total"], 0)

    def test_snapshot_recomputes_expiry_without_new_events(self):
        scheduler.claim(self.path, self.receiver, "receiver", "upgrade", ttl_seconds=30)
        before = self.path.read_bytes()
        first = co.sync(self.path, "receiver")
        self.assertEqual(first["tasks"][0]["lease_status"], "active")
        future = datetime.now(timezone.utc) + timedelta(seconds=301)

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return future if tz else future.replace(tzinfo=None)

        with mock.patch.object(cli, "datetime", Later), mock.patch.object(co, "datetime", Later):
            second = co.sync(self.path, "receiver", after=first["next_cursor"])
        self.assertEqual(second["changes"], [])
        self.assertEqual(second["active_leases"], [])
        self.assertEqual(second["tasks"][0]["lease_status"], "expired_or_missing")
        self.assertIn("owner_unavailable", second["tasks"][0]["blocked_reasons"])
        self.assertEqual({session["freshness"] for session in second["sessions"]}, {"stale"})
        self.assertEqual(self.path.read_bytes(), before)

    def test_fixed_snapshot_moment_keeps_owner_and_lease_consistent(self):
        scheduler.claim(self.path, self.receiver, "receiver", "upgrade", ttl_seconds=30)
        events = cli.load_events(self.path)
        moment = datetime.now(timezone.utc)
        future = moment + timedelta(seconds=301)

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return future if tz else future.replace(tzinfo=None)

        with mock.patch.object(cli, "datetime", Later), mock.patch.object(co, "datetime", Later):
            sessions, _, fixed = co._snapshot(events, now=moment)
            live = scheduler.board(events)
            self.assertEqual(co.freshness(sessions["receiver"], moment), "fresh")
        self.assertEqual(fixed["tasks"][0]["lease_status"], "active")
        self.assertEqual(fixed["tasks"][0]["blocked_reasons"], [])
        self.assertEqual(live["tasks"][0]["lease_status"], "expired_or_missing")
        self.assertIn("owner_unavailable", live["tasks"][0]["blocked_reasons"])


if __name__ == "__main__":
    unittest.main()
