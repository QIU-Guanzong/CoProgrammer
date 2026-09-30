from __future__ import annotations

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, scheduler as sc


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "events.jsonl"
        self.a = self.window("a", "Codex")
        self.b = self.window("b", "Claude Code")

    def window(self, name, client, cwd=None):
        cwd = cwd or self.root / name
        cwd.mkdir(exist_ok=True)
        co.register(self.path, cwd, name, client, "development", provider="chosen-provider")
        return cwd

    def create(self, task="one", patterns=None, **kwargs):
        return sc.create(self.path, self.a, "a", task, f"Implement {task}", patterns or [f"{task}/**"], **kwargs)

    def task_board(self):
        return sc.board(cli.load_events(self.path))

    def assert_unchanged(self, function, pattern=None):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, pattern or ".+"):
            function()
        self.assertEqual(before, self.path.read_bytes())

    def test_claim_finish_and_dependency_unblock(self):
        self.create()
        self.create("two", depends_on=["one"])
        before = self.path.read_bytes()
        board = self.task_board()
        self.assertEqual(board["tasks"][1]["blocked_reasons"], ["unfinished_dependencies"])
        self.assertEqual(before, self.path.read_bytes())
        self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b", "two"), "dependencies")
        first = sc.claim(self.path, self.b, "b")
        self.assertEqual(first["id"], "one")
        self.assertEqual(cli.active_leases(cli.load_events(self.path))[first["lease_id"]]["holder"], "b")
        done = sc.finish(self.path, self.b, "b", "one", first["claim_id"], "Implementation and tests complete")
        self.assertEqual(done["status"], "done")
        self.assertFalse(cli.active_leases(cli.load_events(self.path)))
        self.assertEqual(sc.claim(self.path, self.b, "b")["id"], "two")

    def test_client_routing_skips_oldest_incompatible_work(self):
        first = self.create(clients=["  cOdEx "])
        self.assertEqual(first["clients"], ["codex"])
        self.create("two", clients=["claude code"])
        self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b", "one"), "client")
        self.assertEqual(sc.claim(self.path, self.b, "b")["id"], "two")
        self.assertEqual(sc.claim(self.path, self.a, "a")["id"], "one")

    def test_concurrent_claim_has_exactly_one_winner_and_no_partial_events(self):
        self.create()
        windows = [(f"worker{i}", self.window(f"worker{i}", "codex")) for i in range(8)]
        before = len(cli.load_events(self.path))
        def take(pair):
            name, cwd = pair
            try:
                return sc.claim(self.path, cwd, name)
            except RuntimeError:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(take, windows))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(cli.load_events(self.path)) - before, 3)
        self.assertEqual(len(cli.active_leases(cli.load_events(self.path))), 1)

    def test_same_worktree_is_exclusive_even_for_disjoint_scopes(self):
        self.create()
        self.create("two")
        self.window("same", "deepseek", self.a)
        sc.claim(self.path, self.a, "a", "one")
        self.assert_unchanged(lambda: sc.claim(self.path, self.a, "same", "two"), "worktree")
        self.assert_unchanged(lambda: sc.claim(self.path, self.a, "a", "two"), "worktree")
        self.assertEqual(sc.claim(self.path, self.b, "b", "two")["status"], "claimed")

    def test_shared_path_scope_conflicts_across_worktrees_and_same_holder(self):
        self.create(patterns=["src/**"])
        self.create("two", patterns=["SRC/API.py"])
        held = sc.claim(self.path, self.a, "a", "one")
        self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b", "two"), "lease conflict")
        self.assertIn("path_lease_conflict", self.task_board()["tasks"][1]["blocked_reasons"])
        sc.release(self.path, self.a, "a", "one", held["claim_id"], "Handing back")
        cli.request_lease(self.path, "b", "path", ["src/**"])
        self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b", "two"), "lease conflict")

    def test_release_requeues_and_invalidates_token(self):
        self.create()
        original = sc.claim(self.path, self.a, "a")
        result = sc.release(self.path, self.a, "a", "one", original["claim_id"], "Retry with another window")
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["claim_id"], "")
        self.assertFalse(cli.active_leases(cli.load_events(self.path)))
        replacement = sc.claim(self.path, self.b, "b")
        self.assertNotEqual(replacement["claim_id"], original["claim_id"])
        self.assert_unchanged(lambda: sc.finish(self.path, self.a, "a", "one", original["claim_id"], "Late"), "token")

    def test_expiry_requires_creator_reclaim_and_old_token_stays_fenced(self):
        self.create()
        original = sc.claim(self.path, self.b, "b", ttl_seconds=1)
        self.assert_unchanged(lambda: sc.reclaim(self.path, self.a, "a", "one", "Still active"), "active lease")
        advanced = datetime.now(timezone.utc) + timedelta(seconds=3)
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return advanced if tz else advanced.replace(tzinfo=None)
        with patch.object(cli, "datetime", Later), patch.object(sc, "datetime", Later):
            self.assertEqual(self.task_board()["tasks"][0]["lease_status"], "expired_or_missing")
            self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b"), "worktree")
            self.assert_unchanged(lambda: sc.finish(self.path, self.b, "b", "one", original["claim_id"], "Late"), "expired")
            self.assert_unchanged(lambda: sc.reclaim(self.path, self.b, "b", "one", "Not creator"), "creator")
            requeued = sc.reclaim(self.path, self.a, "a", "one", "Verified old window stopped")
            self.assertEqual(requeued["status"], "queued")
            replacement = sc.claim(self.path, self.a, "a")
            self.assertNotEqual(original["claim_id"], replacement["claim_id"])
            self.assert_unchanged(lambda: sc.guard(self.path, self.b, "b", "one", original["claim_id"]), "token")
            self.assertEqual(self.task_board()["counts"]["claimed"], 1)

    def test_missing_lease_is_reclaimable_without_silent_reassignment(self):
        self.create()
        held = sc.claim(self.path, self.b, "b")
        cli.release_lease(self.path, held["lease_id"], "b")
        self.assert_unchanged(lambda: sc.renew(self.path, self.b, "b", "one", held["claim_id"]), "expired or missing")
        sc.reclaim(self.path, self.a, "a", "one", "Lease was released; checked prior worker")
        self.assertTrue(self.task_board()["tasks"][0]["ready"])

    def test_renew_preserves_token_and_extends_owned_lease(self):
        self.create()
        held = sc.claim(self.path, self.a, "a", ttl_seconds=60)
        old = cli.active_leases(cli.load_events(self.path))[held["lease_id"]]["expires_at"]
        renewed = sc.renew(self.path, self.a, "a", "one", held["claim_id"], ttl_seconds=300)
        new = cli.active_leases(cli.load_events(self.path))[held["lease_id"]]["expires_at"]
        self.assertGreater(co.timestamp(new), co.timestamp(old))
        self.assertEqual(renewed["claim_id"], held["claim_id"])
        self.assertEqual(self.task_board()["counts"]["claimed"], 1)

    def test_guard_checks_scope_relative_paths_and_is_read_only(self):
        self.create(patterns=["src/**"])
        held = sc.claim(self.path, self.a, "a")
        before = self.path.read_bytes()
        result = sc.guard(self.path, self.a, "a", "one", held["claim_id"], ["src/api.py"])
        self.assertTrue(result["allowed"])
        self.assertEqual(result["files"], ["src/api.py"])
        self.assertEqual(before, self.path.read_bytes())
        for files in (["docs/a.md"], ["../src/a.py"], ["/src/a.py"], ["src/**"], ["src\\api.py"], "src/a.py"):
            self.assert_unchanged(lambda: sc.guard(self.path, self.a, "a", "one", held["claim_id"], files))
        self.assert_unchanged(lambda: sc.guard(self.path, self.b, "a", "one", held["claim_id"]), "worktree")

    @unittest.skipIf(os.name == "nt", "Windows does not allow literal backslashes in filenames")
    def test_guard_rejects_git_root_filename_with_literal_backslash(self):
        cli.run_git(["init", "-b", "guard-test"], self.a)
        literal = self.a / "src\\outside.py"
        literal.write_text("# Root file, not a file under src/\n", encoding="utf-8")
        cli.run_git(["add", "--", literal.name], self.a)
        self.assertEqual(cli.run_git(["ls-files", "-z"], self.a), literal.name + "\0")
        self.assertFalse((self.a / "src").exists())
        self.create(patterns=["src/**"])
        held = sc.claim(self.path, self.a, "a")
        self.assert_unchanged(
            lambda: sc.guard(self.path, self.a, "a", "one", held["claim_id"], [literal.name]),
            "forward-slash")

    def test_guard_rejects_symlink_scope_escape(self):
        self.create(patterns=["src/**"])
        (self.a / "src").mkdir()
        (self.a / "private").mkdir()
        try:
            (self.a / "src" / "alias").symlink_to(self.a / "private", target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation unavailable")
        held = sc.claim(self.path, self.a, "a")
        self.assert_unchanged(lambda: sc.guard(self.path, self.a, "a", "one", held["claim_id"], ["src/alias/key"]), "resolves outside task scope")

    def test_branch_binding_blocks_guard_renew_finish_and_release(self):
        self.create()
        held = sc.claim(self.path, self.a, "a")
        actual = co.workspace(self.a)
        with patch.object(co, "workspace", return_value={**actual, "branch": "other"}):
            for function in (
                lambda: sc.guard(self.path, self.a, "a", "one", held["claim_id"]),
                lambda: sc.renew(self.path, self.a, "a", "one", held["claim_id"]),
                lambda: sc.finish(self.path, self.a, "a", "one", held["claim_id"], "Done"),
                lambda: sc.release(self.path, self.a, "a", "one", held["claim_id"], "Return"),
            ):
                self.assert_unchanged(function, "branch")

    def test_detached_head_cannot_claim_or_use_existing_claim(self):
        self.create()
        actual = co.workspace(self.a)
        detached = {**actual, "branch": "HEAD", "head": "detached-commit"}
        with patch.object(co, "workspace", return_value=detached):
            self.assert_unchanged(lambda: sc.claim(self.path, self.a, "a"), "detached HEAD")
        held = sc.claim(self.path, self.a, "a")
        with patch.object(co, "workspace", return_value=detached):
            for function in (
                lambda: sc.guard(self.path, self.a, "a", "one", held["claim_id"]),
                lambda: sc.renew(self.path, self.a, "a", "one", held["claim_id"]),
                lambda: sc.finish(self.path, self.a, "a", "one", held["claim_id"], "Done"),
                lambda: sc.release(self.path, self.a, "a", "one", held["claim_id"], "Return"),
            ):
                self.assert_unchanged(function, "detached HEAD")
        # Restoring the original branch restores the existing claim; failed
        # detached attempts do not alter the token or consume the lease.
        self.assertTrue(sc.guard(self.path, self.a, "a", "one", held["claim_id"])["allowed"])

    def test_detached_claim_history_is_rejected(self):
        self.create()
        sc.claim(self.path, self.a, "a")
        events = cli.load_events(self.path)
        events[-1]["payload"]["task"]["branch"] = "HEAD"
        self.path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        self.assert_unchanged(lambda: self.create("two"), "detached HEAD")

    def test_session_must_be_fresh_and_available(self):
        self.create()
        co.pulse(self.path, self.b, "b", "blocked")
        self.assert_unchanged(lambda: sc.claim(self.path, self.b, "b"), "fresh working or idle")
        co.pulse(self.path, self.b, "b", "idle")
        held = sc.claim(self.path, self.b, "b")
        with patch.object(co, "freshness", return_value="stale"):
            self.assert_unchanged(lambda: sc.guard(self.path, self.b, "b", "one", held["claim_id"]), "fresh working or idle")

    def test_dependency_ids_immutable_and_malformed_requests_have_no_writes(self):
        self.create()
        operations = (
            lambda: self.create(),
            lambda: self.create("missing", depends_on=["future"]),
            lambda: self.create("self", depends_on=["self"]),
            lambda: self.create("bad-client", clients=["codex", "CoDeX"]),
            lambda: self.create("bad-pattern", patterns=["../src/**"]),
            lambda: self.create("bad/id"),
            lambda: sc.create(self.path, self.b, "a", "wrong-tree", "Wrong tree", ["src/**"]),
            lambda: sc.claim(self.path, self.a, "a", ttl_seconds=True),
            lambda: sc.claim(self.path, self.a, "a", "unknown"),
            lambda: sc.claim(self.path, self.a, "a", None),
            lambda: sc.claim(self.path, self.a, "a", []),
        )
        for function in operations:
            self.assert_unchanged(function)

    def test_forged_token_actor_and_empty_summary_rejected(self):
        self.create()
        held = sc.claim(self.path, self.a, "a")
        for function in (
            lambda: sc.finish(self.path, self.a, "a", "one", "claim_fake", "Done"),
            lambda: sc.finish(self.path, self.b, "b", "one", held["claim_id"], "Done"),
            lambda: sc.finish(self.path, self.a, "a", "one", held["claim_id"], ""),
        ):
            self.assert_unchanged(function)

    def test_failed_nested_lease_release_rolls_back_task_finish(self):
        self.create()
        held = sc.claim(self.path, self.a, "a")
        with patch.object(cli, "release_lease", side_effect=RuntimeError("disk failed")):
            self.assert_unchanged(lambda: sc.finish(self.path, self.a, "a", "one", held["claim_id"], "Done"), "disk failed")
        self.assertEqual(self.task_board()["tasks"][0]["status"], "claimed")

    def test_malformed_event_and_semantic_history_fail_closed(self):
        self.create()
        original = self.path.read_bytes()
        events = cli.load_events(self.path)
        forged = json.loads(json.dumps(events[-1]))
        forged["id"] = "evt_forged"
        forged["payload"]["task"]["title"] = "Another creation of the same ID"
        self.path.write_bytes(original + (json.dumps(forged) + "\n").encode())
        self.assert_unchanged(lambda: self.create("two"), "duplicate")
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            self.task_board()
        self.path.write_bytes(original)
        malformed = cli.make_event("task.created", "a", "task:x", {"task": []})
        self.path.write_bytes(original + (json.dumps(malformed) + "\n").encode())
        self.assert_unchanged(lambda: self.create("two"), "invalid task record")

    def test_nested_operations_see_pending_tasks_and_claims(self):
        from coprogrammer.manager_store import transaction
        with transaction(self.path):
            self.create()
            self.create("two", depends_on=["one"])
            held = sc.claim(self.path, self.a, "a")
            sc.finish(self.path, self.a, "a", "one", held["claim_id"], "Done")
            self.assertEqual(sc.claim(self.path, self.b, "b")["id"], "two")
        self.assertEqual(self.task_board()["counts"], {"queued": 0, "claimed": 1, "done": 1})


if __name__ == "__main__":
    unittest.main()
