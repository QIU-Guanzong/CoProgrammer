from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import multiprocessing
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from coprogrammer import cli
from coprogrammer.manager_store import transaction


def _request_in_process(path: str, holder: str, start, results) -> None:
    start.wait(15)
    try:
        result = cli.request_lease(Path(path), holder, "path", ["src/**"])
        results.put(("ok", result["granted"]))
    except Exception as exc:
        results.put(("error", str(exc)))


def _hold_transaction(path: str, entered, release) -> None:
    with transaction(Path(path)):
        entered.set()
        release.wait(15)


class ManagerStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / ".coprogrammer" / "events.jsonl"

    def request(self, holder="codex", patterns=None, ttl_seconds=3600):
        return cli.request_lease(self.path, holder, "path", patterns or ["src/**"],
                                 ttl_seconds=ttl_seconds)

    def test_multiprocess_race_grants_only_one_owner(self) -> None:
        ctx = multiprocessing.get_context("spawn")
        start = ctx.Event()
        results = ctx.Queue()
        processes = [ctx.Process(target=_request_in_process,
                                 args=(str(self.path), f"agent-{i}", start, results))
                     for i in range(6)]
        for process in processes:
            process.start()
        try:
            start.set()
            values = [results.get(timeout=20) for _ in processes]
            self.assertTrue(all(status == "ok" for status, _ in values), values)
            self.assertEqual(sum(granted for _, granted in values), 1)
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join()
            results.close()
        events = cli.load_events(self.path)
        self.assertEqual(len(events), 12)
        self.assertEqual(len(cli.active_leases(events)), 1)

    def test_process_lock_timeout_is_bounded_and_preserves_log(self) -> None:
        self.request()
        before = self.path.read_bytes()
        ctx = multiprocessing.get_context("spawn")
        entered, release = ctx.Event(), ctx.Event()
        process = ctx.Process(target=_hold_transaction, args=(str(self.path), entered, release))
        process.start()
        try:
            self.assertTrue(entered.wait(15))
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                with transaction(self.path, timeout=0.05):
                    self.fail("entered a transaction owned by another process")
            self.assertEqual(self.path.read_bytes(), before)
        finally:
            release.set()
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join()
        self.assertEqual(process.exitcode, 0)

    def test_threads_share_atomic_check_and_append(self) -> None:
        start = threading.Barrier(8)
        def request(i):
            start.wait()
            return self.request(holder=f"thread-{i}")["granted"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            grants = list(pool.map(request, range(8)))
        self.assertEqual(sum(grants), 1)
        self.assertEqual(len(cli.load_events(self.path)), 16)

    def test_empty_lock_file_can_be_contended_without_bootstrap_writes(self) -> None:
        self.path.parent.mkdir(parents=True)
        lock = self.path.with_name(self.path.name + ".lock")
        lock.write_bytes(b"")
        ctx = multiprocessing.get_context("spawn")
        entered, release = ctx.Event(), ctx.Event()
        process = ctx.Process(target=_hold_transaction, args=(str(self.path), entered, release))
        process.start()
        try:
            self.assertTrue(entered.wait(15))
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                with transaction(self.path, timeout=0.05):
                    self.fail("entered another process's empty-file lock")
        finally:
            release.set()
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join()
        self.assertEqual(process.exitcode, 0)
        self.assertEqual(lock.read_bytes(), b"")
        self.assertFalse(self.path.exists())

    def test_all_event_writers_are_serialized(self) -> None:
        def append(i):
            cli.append_event(self.path, cli.make_event("agent.heartbeat", str(i), "repo:test"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(append, range(50)))
        events = cli.load_events(self.path)
        self.assertEqual(len(events), 50)
        self.assertEqual(len({event["id"] for event in events}), 50)

    def test_nested_writer_uses_same_transaction_without_deadlock(self) -> None:
        with transaction(self.path):
            self.assertTrue(self.request()["granted"])
            self.assertFalse(self.request(holder="claude")["granted"])
        self.assertEqual(len(cli.active_leases(cli.load_events(self.path))), 1)

    def test_expired_lease_does_not_block_or_allow_renewal(self) -> None:
        lease = cli.new_lease("old", "path", ["src/**"])
        lease["status"] = "active"
        lease["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        cli.append_event(self.path, cli.make_event("lease.granted", "manager", "repo:test", {"lease": lease}))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "expired"):
            cli.renew_lease(self.path, lease["id"], "old")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(self.request(holder="new")["granted"])

    def test_owner_checked_on_renewal_and_release(self) -> None:
        lease = self.request()["lease"]
        before = self.path.read_bytes()
        for operation in (cli.release_lease, cli.renew_lease):
            with self.assertRaisesRegex(RuntimeError, "only lease holder"):
                operation(self.path, lease["id"], "claude")
            self.assertEqual(self.path.read_bytes(), before)
        renewed = cli.renew_lease(self.path, lease["id"], "codex", ttl_seconds=7200)
        self.assertGreater(renewed["lease"]["expires_at"], lease["expires_at"])
        self.assertEqual(len(cli.active_leases(cli.load_events(self.path))), 1)
        self.assertTrue(cli.release_lease(self.path, lease["id"], "codex")["released"])
        self.assertEqual(cli.active_leases(cli.load_events(self.path)), {})

    def test_legacy_nonexpiring_lease_can_be_renewed(self) -> None:
        lease = cli.new_lease("legacy", "path", ["src/**"])
        lease["status"] = "active"
        cli.append_event(self.path, cli.make_event("lease.granted", "manager", "repo:test", {"lease": lease}))
        self.assertIn(lease["id"], cli.active_leases(cli.load_events(self.path)))
        renewed = cli.renew_lease(self.path, lease["id"], "legacy")
        self.assertIn("expires_at", renewed["lease"])

    def test_invalid_ttl_cannot_mutate_log(self) -> None:
        for ttl in (0, -1, 604801, True, 1.5, "30"):
            with self.assertRaisesRegex(RuntimeError, "ttl_seconds"):
                self.request(ttl_seconds=ttl)
        self.assertFalse(self.path.exists())

    def test_corrupt_log_cannot_be_appended_or_used_for_grant(self) -> None:
        self.path.parent.mkdir()
        for content in ('{"truncated":', '{"id":"missing-fields"}\n', '[]\n'):
            self.path.write_text(content)
            with self.assertRaisesRegex(RuntimeError, "invalid event log"):
                self.request()
            self.assertEqual(self.path.read_text(), content)
            with self.assertRaisesRegex(RuntimeError, "invalid event log"):
                cli.append_event(self.path, cli.make_event("agent.heartbeat", "actor", "repo:test"))
            self.assertEqual(self.path.read_text(), content)

    def test_malformed_expiry_fails_closed(self) -> None:
        lease = self.request()["lease"]
        events = cli.load_events(self.path)
        events[-1]["payload"]["lease"]["expires_at"] = "2026-09-26"
        self.path.write_text("".join(json.dumps(event) + "\n" for event in events))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "expires_at"):
            self.request(holder="claude")
        self.assertEqual(before, self.path.read_bytes())

    def test_invalid_reducer_payload_cannot_be_persisted(self) -> None:
        self.request()
        before = self.path.read_bytes()
        records = [("agent.heartbeat", "heartbeat", "agent"),
                   ("decision.requested", "decision", "id"),
                   ("contract.change.proposed", "contract_change", "id")]
        for event_type, field, identity in records:
            for value in (None, [], "invalid", 5, {identity: []}):
                with self.subTest(event_type=event_type, value=value):
                    event = cli.make_event(event_type, "actor", "repo:test", {field: value})
                    with self.assertRaisesRegex(RuntimeError, "invalid event log entry.*" + field):
                        cli.append_event(self.path, event)
                    self.assertEqual(self.path.read_bytes(), before)
        event = cli.make_event("decision.recorded", "actor", "repo:test", {"decision_id": []})
        with self.assertRaisesRegex(RuntimeError, "expected string decision_id"):
            cli.append_event(self.path, event)
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_invalid_reducer_payload_is_reported_with_line_number(self) -> None:
        self.request()
        event = cli.make_event("agent.heartbeat", "actor", "repo:test", {"heartbeat": []})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "line 3: expected object heartbeat"):
            cli.load_events(self.path)
        with self.assertRaisesRegex(RuntimeError, "line 3: expected object heartbeat"):
            self.request(holder="claude", patterns=["docs/**"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_missing_or_empty_reducer_records_still_load(self) -> None:
        for event_type, field in [("agent.heartbeat", "heartbeat"),
                                  ("decision.requested", "decision"),
                                  ("contract.change.proposed", "contract_change")]:
            for payload in ({}, {field: {}}):
                cli.append_event(self.path, cli.make_event(event_type, "legacy", "repo:test", payload))
        cli.append_event(self.path, cli.make_event("decision.recorded", "legacy", "repo:test"))
        events = cli.load_events(self.path)
        self.assertEqual(len(events), 7)
        self.assertEqual(cli.latest_heartbeats(events), {"legacy": {}})
        self.assertEqual(cli.open_decisions(events), {})
        self.assertEqual(cli.contract_changes(events), {})

    def test_nonfinite_incoming_numbers_cannot_be_persisted(self) -> None:
        self.request()
        before = self.path.read_bytes()
        for number in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(number=number):
                event = cli.make_event("agent.heartbeat", "actor", "repo:test",
                                       {"heartbeat": {"metric": number}})
                with self.assertRaisesRegex(RuntimeError, "invalid event log JSON at line 3"):
                    cli.append_event(self.path, event)
                self.assertEqual(self.path.read_bytes(), before)

    def test_existing_nonfinite_numbers_fail_closed(self) -> None:
        self.request()
        original = self.path.read_text()
        event = cli.make_event("agent.heartbeat", "actor", "repo:test", {"metric": "NUMBER"})
        for number in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(number=number):
                self.path.write_text(original + json.dumps(event).replace('"NUMBER"', number) + "\n")
                before = self.path.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "line 3: non-finite JSON numbers"):
                    cli.load_events(self.path)
                with self.assertRaisesRegex(RuntimeError, "line 3: non-finite JSON numbers"):
                    self.request(holder="claude", patterns=["docs/**"])
                self.assertEqual(self.path.read_bytes(), before)

    def test_nonfinite_commit_failure_preserves_log(self) -> None:
        self.request()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "cannot commit Manager event log"):
            with transaction(self.path) as current:
                current.append(cli.make_event("agent.heartbeat", "actor", "repo:test"))
                current.pending[-1]["payload"]["metric"] = float("nan")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".events.jsonl.*")), [])

    def test_json_recursion_errors_report_runtime_error_without_mutation(self) -> None:
        self.request()
        before = self.path.read_bytes()
        event = cli.make_event("agent.heartbeat", "actor", "repo:test")
        # JSON recursion limits differ between Python versions and interpreters.
        with mock.patch("coprogrammer.manager_store.json.dumps", side_effect=RecursionError("too deep")):
            with self.assertRaisesRegex(RuntimeError, "invalid event log JSON at line 3"):
                cli.append_event(self.path, event)
        self.assertEqual(self.path.read_bytes(), before)
        with mock.patch("coprogrammer.manager_store.json.loads", side_effect=RecursionError("too deep")):
            with self.assertRaisesRegex(RuntimeError, "invalid event log JSON at line 1"):
                cli.load_events(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_commit_failure_preserves_previous_log(self) -> None:
        self.request()
        before = self.path.read_bytes()
        with mock.patch("coprogrammer.manager_store.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaisesRegex(RuntimeError, "cannot commit"):
                self.request(holder="claude", patterns=["docs/**"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".events.jsonl.*")), [])

    def test_cli_renew_and_release(self) -> None:
        lease = self.request()["lease"]
        with contextlib.redirect_stdout(io.StringIO()):
            for action in ("renew", "release"):
                self.assertEqual(cli.main(["manager", "lease", action, "--cwd", str(self.root),
                                           "--id", lease["id"], "--actor", "codex"]), 0)

    def test_root_and_partial_globs_conflict_conservatively(self) -> None:
        self.assertTrue(cli.patterns_overlap("*.py", "*test*"))
        self.assertTrue(cli.patterns_overlap("src/foo*.py", "src/foobar*"))
        self.assertTrue(cli.patterns_overlap("src/[ab]*/x", "src/a*/x"))
        self.assertFalse(cli.patterns_overlap("docs/**", "src/**"))


class SharedWorktreeStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.worktree = self.root / "worker"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "initial", "--allow-empty")
        self.git("worktree", "add", "-qb", "worker", str(self.worktree))
        self.nested = self.worktree / "src" / "nested"
        self.nested.mkdir(parents=True)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def test_main_worktree_and_subdirectories_share_existing_default_log(self) -> None:
        expected = self.repo / ".coprogrammer" / "events.jsonl"
        cli.request_lease(expected, "codex", "path", ["src/**"])
        self.assertEqual(cli.event_log_path(self.repo), expected)
        self.assertEqual(cli.event_log_path(self.worktree), expected)
        self.assertEqual(cli.event_log_path(self.nested), expected)
        self.assertFalse(cli.request_lease(cli.event_log_path(self.nested), "claude", "path", ["src/**"])["granted"])
        self.assertEqual(len(cli.active_leases(cli.load_events(expected))), 1)

    def test_explicit_relative_and_absolute_state_paths_keep_their_semantics(self) -> None:
        self.assertEqual(cli.manager_dir(self.nested, ".coprogrammer"), self.nested / ".coprogrammer")
        self.assertEqual(cli.manager_dir(self.nested, "custom"), self.nested / "custom")
        self.assertEqual(cli.manager_dir(self.nested, str(self.root / "state")), self.root / "state")

    def test_competing_worktree_or_nested_log_requires_explicit_choice(self) -> None:
        for directory in (self.worktree, self.nested):
            log = directory / ".coprogrammer" / "events.jsonl"
            cli.request_lease(log, "old", "path", ["src/**"])
            with self.assertRaisesRegex(RuntimeError, "competing legacy Manager log"):
                cli.event_log_path(self.nested)
            self.assertEqual(cli.event_log_path(directory, ".coprogrammer"), log)
            log.unlink()


if __name__ == "__main__":
    unittest.main()
