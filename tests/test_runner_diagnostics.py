"""Real offline process outcomes with retained claims and partial edits."""
import os
import signal
import sys
import json
import unittest

from coprogrammer import collaboration as co, runner, scheduler, watcher
from coprogrammer.manager_store import load_events
from test_workspace_workflow import Fixture


class RunnerDiagnosticsTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "harness", "harness", "diagnostics")
        scheduler.create(self.path, self.repo, "harness", "api", "API", ["src/**"])

    def run_code(self, code, **options):
        return runner.run(self.path, self.repo, "harness", [sys.executable, "-c", code],
                          apply=True, **options)

    def assert_unfinished(self):
        events = load_events(self.path)
        self.assertEqual(sum(e["type"] == "task.claimed" for e in events), 1)
        self.assertFalse(any(e["type"] == "task.finished" for e in events))

    def test_missing_executable_was_not_launched_and_retains_claim(self):
        result = runner.run(self.path, self.repo, "harness", [str(self.root / "absent")], apply=True)
        self.assertEqual(result["reason"], "command_unavailable")
        self.assertFalse(result["launched"])
        self.assertIsNone(result["exit_code"])
        self.assertTrue(result["claim_retained"])
        self.assertTrue(result["next_step"])
        self.assert_unfinished()

    def inbox_failure(self, owned):
        if owned:
            scheduler.claim(self.path, self.repo, "harness", "api")
        peer = self.root / "peer"
        self.git("worktree", "add", "-b", "peer", str(peer))
        co.register(self.path, peer, "peer", "harness", "diagnostics")
        co.send(self.path, peer, "peer", "harness", "api", "Synthetic inbox item")
        result = runner.run(self.path, self.repo, "harness", [str(self.root / "absent")],
                            apply=True, handle_inbox=True)
        self.assertEqual(result["reason"], "command_unavailable")
        self.assertFalse(result["launched"])
        self.assertIsNone(result["exit_code"])
        self.assertIs(result["claim_retained"], owned)
        events = load_events(self.path)
        self.assertEqual(sum(e["type"] == "task.claimed" for e in events), int(owned))
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 1)
        self.assertFalse(any(e["type"] in ("task.finished", "lease.released", "message.acknowledged") for e in events))

    def test_failed_inbox_with_no_claim_does_not_invent_retained_claim(self):
        self.inbox_failure(False)

    def test_failed_inbox_with_owned_claim_retains_original_ownership(self):
        self.inbox_failure(True)

    def test_exit_and_reply_failures_keep_code_edits_and_same_claim_for_explicit_success(self):
        cases = [("import pathlib;pathlib.Path('src/main.py').write_text('VALUE = 2\\n');raise SystemExit(7)", "command_failed", 7),
                 ("print('private raw diagnostic')", "invalid_reply", 0),
                 ("print('x'*130000)", "reply_too_large", 0)]
        claim = None
        for code, reason, exit_code in cases:
            with self.subTest(reason=reason):
                result = self.run_code(code)
                self.assertEqual(result["reason"], reason)
                self.assertTrue(result["launched"])
                self.assertEqual(result["exit_code"], exit_code)
                self.assertTrue(result["claim_retained"])
                self.assertTrue(result["next_step"])
                current = result["boundary"]["task"]["claim_id"]
                claim = current if claim is None else claim
                self.assertEqual(current, claim)
                self.assertNotIn("private raw diagnostic", json.dumps(result))
                self.assert_unfinished()
        self.assertEqual((self.repo / "src/main.py").read_text(), "VALUE = 2\n")
        # This is a separate explicit invocation after fixture inspection,
        # not an automatic retry of the failed side-effecting command.
        done = self.run_code("import json;print(json.dumps({'status':'done','summary':'Inspected fixture'}))")
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["exit_code"], 0)
        self.assertEqual(done["boundary"]["task"]["claim_id"], claim)
        self.assertEqual(sum(e["type"] == "task.claimed" for e in load_events(self.path)), 1)

    def test_timeout_does_not_report_cleanup_kill_as_original_exit(self):
        result = self.run_code("import pathlib,time;pathlib.Path('src/partial.txt').write_text('Partial fixture');time.sleep(20)", timeout=1)
        self.assertEqual(result["reason"], "timeout")
        self.assertTrue(result["launched"])
        self.assertIsNone(result["exit_code"])
        self.assertTrue(result["claim_retained"])
        self.assertEqual((self.repo / "src/partial.txt").read_text(), "Partial fixture")
        self.assert_unfinished()

    def test_watcher_exposes_exit_code_and_never_repeats_failed_side_effect(self):
        code = "import pathlib;p=pathlib.Path('src/run-count.txt');p.write_text(str(int(p.read_text())+1) if p.exists() else '1');raise SystemExit(9)"
        result = watcher.watch(self.path, self.repo, "harness", [sys.executable, "-c", code],
                               apply=True, wait=True, max_cycles=5)
        self.assertEqual(result["reason"], "command_failed")
        self.assertEqual(result["cycles"], 1)
        self.assertEqual(result["last"]["exit_code"], 9)
        self.assertTrue(result["last"]["claim_retained"])
        self.assertEqual((self.repo / "src/run-count.txt").read_text(), "1")
        self.assert_unfinished()

    @unittest.skipUnless(os.name == "posix", "POSIX negative signal return code")
    def test_signal_exit_is_preserved_before_cleanup(self):
        result = self.run_code("import os,signal;os.kill(os.getpid(),signal.SIGTERM)")
        self.assertEqual(result["reason"], "command_failed")
        self.assertEqual(result["exit_code"], -signal.SIGTERM)
        self.assert_unfinished()
