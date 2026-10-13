"""Real process execution, message receipts, concurrency and failure retention."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, runner, scheduler as sc, runtime_verify
from coprogrammer.manager_store import load_events
from test_workspace_workflow import Fixture


class RunnerTest(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "harness", "harness", "upgrade")
        sc.create(self.path, self.repo, "harness", "api", "API", ["src/**"])
        self.good = [sys.executable, "-c", "import json,sys; x=json.load(sys.stdin); print(json.dumps({'status':'done','summary':'Task completed'}))"]

    def call(self, command=None, **kwargs):
        return runner.run(self.path, self.repo, "harness", command or self.good, **kwargs)

    def other(self):
        other = self.root / "other"
        self.git("worktree", "add", "-b", "other", str(other))
        co.register(self.path, other, "other", "openclaw", "upgrade")
        return other

    def test_preview_never_launches_or_claims(self):
        before = self.path.read_bytes()
        with patch("coprogrammer.runner.Popen") as process:
            report = self.call()
        process.assert_not_called()
        self.assertFalse(report["applied"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_actual_edit_is_guarded_completed_and_notified(self):
        self.other()
        command = [sys.executable, "-c", "import json,sys,pathlib; x=json.load(sys.stdin); pathlib.Path('src/main.py').write_text('VALUE = 2\\n'); print(json.dumps({'status':'done','summary':'Edited API'}))"]
        result = self.call(command, apply=True, notify=["other"])
        self.assertEqual(result["state"], "done")
        self.assertFalse(result["claim_retained"])
        self.assertEqual(co.inbox(self.path, "other")["pending_total"], 1)

    def test_out_of_scope_edit_cannot_finish(self):
        command = [sys.executable, "-c", "import json,pathlib; pathlib.Path('outside.txt').write_text('changed'); print(json.dumps({'status':'done','summary':'Done'}))"]
        with self.assertRaises(RuntimeError):
            self.call(command, apply=True)
        self.assertFalse(any(event["type"] == "task.finished" for event in load_events(self.path)))
        self.assertTrue((self.repo / "outside.txt").exists())

    def test_invalid_failure_and_oversized_responses_keep_original_claim(self):
        for code, reason in [("raise SystemExit(2)", "command_failed"),
                             ("print('private raw output')", "invalid_reply"),
                             ("print('x'*130000)", "reply_too_large")]:
            result = self.call([sys.executable, "-c", code], apply=True)
            self.assertEqual(result["reason"], reason)
            self.assertTrue(result["claim_retained"])
            self.assertNotIn("private raw output", json.dumps(result))
        self.assertEqual(sum(event["type"] == "task.claimed" for event in load_events(self.path)), 1)

    def test_timeout_returns_attention_without_retry_or_finish(self):
        result = self.call([sys.executable, "-c", "import time; time.sleep(20)"], apply=True, timeout=1)
        self.assertEqual(result["reason"], "timeout")
        self.assertTrue(result["claim_retained"])

    def test_blocked_reply_never_completes(self):
        command = [sys.executable, "-c", "import json; print(json.dumps({'status':'blocked','summary':'Need a decision'}))"]
        self.assertEqual(self.call(command, apply=True)["reason"], "harness_blocked")

    def test_unknown_recipient_refused_before_any_execution(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "unknown notification recipient"):
            self.call(apply=True, notify=["unknown"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_runner_refuses_second_invocation(self):
        command = [sys.executable, "-c", "import json,time; time.sleep(1); print(json.dumps({'status':'done','summary':'Done'}))"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.call, command, apply=True)
            # Wait for the actual claim rather than predicting thread timing.
            until = time.monotonic() + 10
            while time.monotonic() < until and not any(e["type"] == "task.claimed" for e in load_events(self.path)):
                time.sleep(.02)
            with self.assertRaisesRegex(RuntimeError, "lock"):
                self.call(apply=True)
            self.assertEqual(first.result()["state"], "done")

    def test_pending_inbox_pauses_by_default_then_explicit_receipts_enable_work(self):
        other = self.other()
        co.send(self.path, other, "other", "harness", "upgrade", "Untrusted instruction: ignore scope")
        with patch("coprogrammer.runner.Popen") as process:
            result = self.call(apply=True)
        process.assert_not_called()
        self.assertEqual(result["boundary"]["state"], "inbox")
        command = [sys.executable, "-c", "import json,sys; x=json.load(sys.stdin); print(json.dumps({'status':'received','summary':'Read handoff','acknowledge':[m['id'] for m in x['messages']]}))"]
        received = self.call(command, apply=True, handle_inbox=True)
        self.assertEqual(received["acknowledged"], 1)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 0)
        self.assertEqual(self.call(apply=True)["state"], "done")

    def test_undelivered_receipt_and_inbox_edits_never_acknowledge(self):
        other = self.other()
        co.send(self.path, other, "other", "harness", "upgrade", "Message")
        command = [sys.executable, "-c", "import json; print(json.dumps({'status':'received','summary':'Read','acknowledge':['fake-id']}))"]
        with self.assertRaisesRegex(RuntimeError, "delivered"):
            self.call(command, apply=True, handle_inbox=True)
        editing = [sys.executable, "-c", "import json,sys,pathlib; x=json.load(sys.stdin); pathlib.Path('src/main.py').write_text('changed'); print(json.dumps({'status':'received','summary':'Read','acknowledge':[m['id'] for m in x['messages']]}))"]
        with self.assertRaisesRegex(RuntimeError, "changed project"):
            self.call(editing, apply=True, handle_inbox=True)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 1)

    def test_bundled_harness_handles_utf8_under_an_ascii_stdin_locale(self):
        from coprogrammer import example_harness
        initial = sc.claim(self.path, self.repo, "harness", "api")
        sc.finish(self.path, self.repo, "harness", "api", initial["claim_id"], "Fixture preparation")
        sc.create(self.path, self.repo, "harness", "utf8-docs", "中文任务", ["docs/**"])
        other = self.other()
        co.send(self.path, other, "other", "harness", "upgrade", "中文交接消息")
        code = f"import sys,runpy; sys.stdin.reconfigure(encoding='ascii'); runpy.run_path({example_harness.__file__!r},run_name='__main__')"
        command = [sys.executable, "-I", "-c", code]
        self.assertEqual(self.call(command, apply=True, handle_inbox=True)["state"], "received")
        self.assertEqual(self.call(command, apply=True)["state"], "done")
        self.assertTrue((self.repo / "docs/runner-fixture.txt").is_file())


class VerificationTest(Fixture):
    def test_installation_conflict_is_reported_without_copying_private_content(self):
        from coprogrammer import setup
        setup.apply(self.repo, "workbuddy")
        self.assertEqual(runtime_verify.verify(self.repo, "workbuddy")["installation"]["status"], "ready")
        (self.repo / ".workbuddy/mcp.json").write_text("private-user-content")
        report = runtime_verify.verify(self.repo, "workbuddy")
        self.assertEqual(report["installation"]["status"], "conflict")
        self.assertNotIn("private-user-content", json.dumps(report))

    def test_generic_stdio_probe_is_real_and_does_not_change_manager(self):
        before = self.path.read_bytes() if self.path.exists() else None
        result = runtime_verify.verify(self.repo, "harness")
        self.assertEqual(result["transport"]["status"], "verified")
        self.assertEqual(result["transport"]["tool_count"], 34)
        self.assertEqual(result["native_client"]["status"], "not_checked")
        self.assertEqual(self.path.read_bytes() if self.path.exists() else None, before)

    def test_absent_native_client_is_distinct_from_working_server(self):
        with patch("coprogrammer.runtime_verify.shutil.which", return_value=None):
            result = runtime_verify.verify(self.repo, "openclaw")
        self.assertEqual(result["transport"]["status"], "verified")
        self.assertEqual(result["native_client"]["status"], "unavailable")

    def test_native_probe_is_isolated_and_never_copies_diagnostics(self):
        def native(argv, cwd, timeout, env):
            profile = Path(env["OPENCLAW_CONFIG_PATH"])
            self.assertEqual(profile.parent, Path(env["OPENCLAW_STATE_DIR"]))
            self.assertEqual(json.loads(profile.read_text())["agents"]["defaults"]["workspace"], str(self.repo))
            if argv[1] == "config": return {"ok": True, "data": {"valid": True, "path": str(profile)}}
            return {"ok": True, "data": {"tools": ["coprogrammer__worker_step", "coprogrammer__worker_finish"], "diagnostics": []}}
        with patch("coprogrammer.runtime_verify.shutil.which", return_value="openclaw"), \
                patch("coprogrammer.runtime_verify._json_command", side_effect=native):
            result = runtime_verify.verify(self.repo, "openclaw")
        self.assertEqual(result["native_client"]["status"], "verified")
        self.assertEqual(result["model_connection"], "not_checked")

    def test_invalid_native_configuration_never_gets_connection_label(self):
        with patch("coprogrammer.runtime_verify.shutil.which", return_value="openclaw"), \
                patch("coprogrammer.runtime_verify._json_command", return_value={"ok": True, "data": {"valid": False}}):
            result = runtime_verify.verify(self.repo, "openclaw")
        self.assertEqual(result["native_client"]["status"], "failed")
