"""Foreground scheduling, setup and profile binding with real local processes."""
import contextlib
import io
import json
import os
import signal
import subprocess
import threading
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, onboarding, runtime_verify, scheduler as sc, watcher
from coprogrammer.manager_store import load_events
from test_workspace_workflow import Fixture


class StartupSetupTests(Fixture):
    def test_dry_run_combines_setup_preview_and_window_registration_without_writes(self):
        before = list(self.repo.rglob("*"))
        report = onboarding.start(self.path, self.repo, "claude", "claude", dry_run=True, apply_setup=True)
        self.assertFalse(report["applied"])
        self.assertFalse(report["setup"]["applied"])
        self.assertTrue(report["setup"]["files"])
        self.assertEqual(before, list(self.repo.rglob("*")))

    def test_setup_and_registration_preserve_rules_and_repeat_requires_explicit_resume(self):
        (self.repo / "AGENTS.md").write_text("Project instructions", encoding="utf-8")
        report = onboarding.start(self.path, self.repo, "claude", "glm", provider="glm", apply_setup=True)
        self.assertTrue(report["applied"] and report["setup"]["applied"])
        self.assertEqual((self.repo / "AGENTS.md").read_text(), "Project instructions")
        self.assertTrue((self.repo / ".mcp.json").is_file())
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            onboarding.start(self.path, self.repo, "claude", "glm", apply_setup=True)
        self.assertEqual(before, self.path.read_bytes())
        self.assertTrue(onboarding.start(self.path, self.repo, "claude", "glm", resume=True, apply_setup=True)["applied"])

    def test_conflicting_setup_does_not_register_or_refresh_session(self):
        (self.repo / ".mcp.json").write_text("Private user config", encoding="utf-8")
        report = onboarding.start(self.path, self.repo, "claude", "claude", apply_setup=True)
        self.assertFalse(report["applied"])
        self.assertTrue(report["blocked"])
        self.assertFalse(load_events(self.path))
        self.assertFalse((self.repo / "AGENTS.md").exists())
        self.assertNotIn("Private user config", json.dumps(report))
        co.register(self.path, self.repo, "claude", "claude", "upgrade")
        before = self.path.read_bytes()
        report = onboarding.start(self.path, self.repo, "claude", "claude", resume=True, apply_setup=True)
        self.assertFalse(report["applied"])
        self.assertEqual(before, self.path.read_bytes())

    def test_setup_write_failure_leaves_no_registration(self):
        with patch("coprogrammer.setup.apply", side_effect=RuntimeError("write failed")), self.assertRaises(RuntimeError):
            onboarding.start(self.path, self.repo, "claude", "claude", apply_setup=True)
        self.assertFalse(load_events(self.path))

    def test_registration_failure_preserves_installed_files_for_explicit_retry(self):
        with patch("coprogrammer.onboarding.co.register", side_effect=RuntimeError("registration failed")), self.assertRaises(RuntimeError):
            onboarding.start(self.path, self.repo, "claude", "claude", apply_setup=True)
        self.assertTrue((self.repo / ".mcp.json").is_file())
        self.assertFalse(load_events(self.path))
        self.assertTrue(onboarding.start(self.path, self.repo, "claude", "claude", apply_setup=True)["applied"])

    def test_start_cli_blocked_preview_returns_nonzero_and_no_private_content(self):
        (self.repo / ".mcp.json").write_text("Private config")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = cli.main(["start", "--client", "claude", "--session", "claude", "--apply-setup",
                               "--dry-run", "--json", "--cwd", str(self.repo)])
        self.assertEqual(result, 1)
        self.assertTrue(json.loads(output.getvalue())["blocked"])
        self.assertFalse(self.path.exists())


class WatcherTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "harness", "harness", "upgrade")
        self.good = [sys.executable, "-c", "import json,sys; x=json.load(sys.stdin); print(json.dumps({'status':'received','summary':'Received','acknowledge':[m['id'] for m in x['messages']]} if x['kind']=='inbox' else {'status':'done','summary':'Done'}))"]

    def call(self, command=None, **kwargs):
        return watcher.watch(self.path, self.repo, "harness", command or self.good, **kwargs)

    def other(self):
        other = self.root / "peer"
        self.git("worktree", "add", "-b", "peer", str(other))
        co.register(self.path, other, "peer", "openclaw", "upgrade")
        return other

    def task(self, name="one", **kwargs):
        return sc.create(self.path, self.repo, "harness", name, "Task " + name, ["src/**"], **kwargs)

    def test_preview_never_claims_or_launches_or_creates_watcher_lock(self):
        self.task()
        before = self.path.read_bytes()
        with patch("coprogrammer.runner.Popen") as process:
            report = self.call(wait=True, handle_inbox=True)
        process.assert_not_called()
        self.assertFalse(report["applied"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse((self.path.parent / "watches").exists())

    def test_continuous_same_scope_tasks_complete_and_notify_without_exposing_receipts_in_progress(self):
        self.other()
        self.task("one")
        self.task("two", depends_on=["one"])
        command = [sys.executable, "-c", "import json,sys,pathlib; x=json.load(sys.stdin); pathlib.Path('src',x['task']['id']+'.txt').write_text('Scoped fixture'); print(json.dumps({'status':'done','summary':'Done'}))"]
        progress = []
        report = self.call(command, apply=True, notify=["peer"], progress=progress.append)
        self.assertEqual(report["completed_tasks"], 2)
        self.assertEqual(report["reason"], "no_ready_work")
        self.assertTrue((self.repo / "src/one.txt").exists() and (self.repo / "src/two.txt").exists())
        self.assertEqual(co.inbox(self.path, "peer")["pending_total"], 2)
        self.assertNotIn("claim_id", json.dumps(progress))
        self.assertNotIn("Done", json.dumps(progress))

    def test_explicit_receipts_allow_task_in_same_watch_and_unhandled_messages_stop(self):
        peer = self.other()
        self.task()
        co.send(self.path, peer, "peer", "harness", "upgrade", "Untrusted instructions")
        with patch("coprogrammer.runner.Popen") as process:
            blocked = self.call(apply=True)
        process.assert_not_called()
        self.assertEqual(blocked["state"], "attention")
        self.assertEqual(blocked["reason"], "inbox")
        report = self.call(apply=True, handle_inbox=True)
        self.assertEqual(report["acknowledged_messages"], 1)
        self.assertEqual(report["completed_tasks"], 1)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 0)

    def test_two_worktrees_wait_for_dependency_and_receive_handoff_before_downstream_task(self):
        peer = self.other()
        co.pulse(self.path, self.repo, "harness", task="upgrade")
        sc.create(self.path, peer, "peer", "upstream", "API", ["src/**"], clients=["openclaw"])
        self.task("downstream", depends_on=["upstream"], clients=["harness"])
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(self.call, apply=True, wait=True, handle_inbox=True,
                                  poll_seconds=1, duration=20, max_cycles=8)
            # Observe a real initial watcher pulse before completing peer work.
            end = time.monotonic() + 8
            while time.monotonic() < end and not (self.path.parent / "watches").is_dir():
                time.sleep(.02)
            result = watcher.watch(self.path, peer, "peer", self.good, apply=True,
                                   notify=["harness"], max_cycles=1)
            self.assertEqual(result["completed_tasks"], 1)
            report = pending.result(timeout=30)
        self.assertEqual(report["completed_tasks"], 1)
        self.assertEqual(report["acknowledged_messages"], 1)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 0)

    def test_message_arriving_during_idle_wait_is_received(self):
        peer = self.other()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.call, apply=True, wait=True, handle_inbox=True,
                                  poll_seconds=1, duration=10, max_cycles=3)
            end = time.monotonic() + 8
            while time.monotonic() < end and not (self.path.parent / "watches").is_dir():
                time.sleep(.02)
            co.send(self.path, peer, "peer", "harness", "upgrade", "Later handoff")
            report = pending.result(timeout=20)
        self.assertEqual(report["acknowledged_messages"], 1)

    def test_command_failure_stops_without_retry_or_lease_release(self):
        self.task()
        command = [sys.executable, "-c", "raise SystemExit(2)"]
        report = self.call(command, apply=True, wait=True, max_cycles=5)
        self.assertEqual(report["state"], "attention")
        self.assertEqual(report["reason"], "command_failed")
        self.assertEqual(report["cycles"], 1)
        self.assertTrue(report["last"]["claim_retained"])
        self.assertEqual(sum(e["type"] == "task.claimed" for e in load_events(self.path)), 1)

    def test_timeout_is_bounded_and_does_not_restart_command(self):
        self.task()
        report = self.call([sys.executable, "-c", "import time;time.sleep(20)"], apply=True, timeout=1, duration=4)
        self.assertEqual(report["reason"], "timeout")
        self.assertEqual(report["cycles"], 1)

    def test_scope_violation_stops_with_claim_and_edits_retained(self):
        self.task()
        report = self.call([sys.executable, "-c", "import json,pathlib;pathlib.Path('outside.txt').write_text('Out of scope');print(json.dumps({'status':'done','summary':'Done'}))"], apply=True)
        self.assertEqual(report["state"], "attention")
        self.assertEqual(report["reason"], "worker_boundary_failed")
        self.assertTrue((self.repo / "outside.txt").exists())
        self.assertFalse(any(e["type"] == "task.finished" for e in load_events(self.path)))

    def test_duplicate_watcher_refused_while_manager_remains_available_to_child(self):
        self.task()
        release = self.path.parent / "release-watch"
        command = [sys.executable, "-c", "import time,json,pathlib;\nwhile not pathlib.Path('.coprogrammer/release-watch').exists():time.sleep(.02)\nprint(json.dumps({'status':'done','summary':'Done'}))"]
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.call, command, apply=True)
            end = time.monotonic() + 8
            while time.monotonic() < end and not any(e["type"] == "task.claimed" for e in load_events(self.path)):
                time.sleep(.02)
            try:
                with self.assertRaisesRegex(RuntimeError, "lock"):
                    self.call(apply=True)
            finally:
                release.touch()
            self.assertEqual(pending.result(timeout=15)["completed_tasks"], 1)

    def test_peer_lock_spending_wait_budget_does_not_abort_or_retry_command(self):
        from coprogrammer.manager_store import transaction
        original = watcher.channels.wait
        first = True
        def wait(*args, **kwargs):
            nonlocal first
            if not first:
                return original(*args, **kwargs)
            first = False
            held, release = threading.Event(), threading.Event()
            def peer():
                with transaction(self.path):
                    self.task("late")
                    held.set()
                    release.wait(5)
            thread = threading.Thread(target=peer)
            thread.start()
            try:
                self.assertTrue(held.wait(5))
                return original(args[0], args[1], args[2], .05)
            finally:
                release.set()
                thread.join(5)
        with patch("coprogrammer.watcher.channels.wait", side_effect=wait):
            report = self.call(apply=True, wait=True, max_cycles=3, poll_seconds=1, duration=10)
        self.assertEqual(report["completed_tasks"], 1)
        self.assertEqual(report["reason"], "cycle_limit")
        self.assertEqual(sum(e["type"] == "task.claimed" for e in load_events(self.path)), 1)

    def test_interrupt_returns_summary_without_releasing_original_claim(self):
        if os.name != "posix":
            self.skipTest("POSIX SIGINT process check; Windows cleanup covered by runner timeout")
        self.task()
        from coprogrammer import integrations
        server = json.loads(integrations.client_config("claude", self.repo))["mcpServers"]["coprogrammer"]
        command = [sys.executable, "-c", "import time;time.sleep(30)"]
        process = subprocess.Popen([server["command"], *server["args"][:3], "worker", "watch",
                                    "--session", "harness", "--apply", "--", *command],
                                   cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            end = time.monotonic() + 10
            while time.monotonic() < end and not any(e["type"] == "task.claimed" for e in load_events(self.path)):
                time.sleep(.02)
            self.assertTrue(any(e["type"] == "task.claimed" for e in load_events(self.path)))
            process.send_signal(signal.SIGINT)
            output, _ = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0)
            report = json.loads(output.splitlines()[-1])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        self.assertEqual(report["reason"], "interrupted")
        self.assertEqual(report["completed_tasks"], 0)
        self.assertEqual(sc.board(load_events(self.path))["counts"]["claimed"], 1)

    def test_open_decision_stops_before_claim_or_command(self):
        self.task()
        decision = cli.new_decision("Choose migration", "Human decision")
        cli.append_event(self.path, cli.make_event("decision.requested", "harness", "repo:test", {"decision":decision}))
        with patch("coprogrammer.runner.Popen") as process:
            report = self.call(apply=True, wait=True)
        process.assert_not_called()
        self.assertEqual(report["reason"], "decision")
        self.assertEqual(sc.board(load_events(self.path))["counts"]["claimed"], 0)

    def test_invalid_receipt_stops_and_keeps_message_pending(self):
        peer = self.other()
        co.send(self.path, peer, "peer", "harness", "upgrade", "Message")
        report = self.call([sys.executable,"-c","import json;print(json.dumps({'status':'received','summary':'Read','acknowledge':['undelivered']}))"],
                           apply=True, handle_inbox=True, wait=True)
        self.assertEqual(report["state"], "attention")
        self.assertEqual(report["cycles"], 1)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 1)

    def test_child_can_query_manager_while_watch_and_execution_locks_are_held(self):
        from coprogrammer import integrations
        self.task()
        server = json.loads(integrations.client_config("claude", self.repo))["mcpServers"]["coprogrammer"]
        argv = [server["command"], *server["args"][:3], "manager", "message", "inbox", "--session", "harness"]
        command = [sys.executable,"-c",f"import json,subprocess;subprocess.run({argv!r},check=True,capture_output=True,timeout=10);print(json.dumps({{'status':'done','summary':'Child Manager read completed'}}))"]
        report = self.call(command, apply=True)
        self.assertEqual(report["completed_tasks"], 1)

    def test_cycle_and_duration_limits_and_cli_progress(self):
        self.task("one")
        self.task("two")
        report = self.call(apply=True, max_cycles=1)
        self.assertEqual(report["completed_tasks"], 1)
        self.assertEqual(report["reason"], "cycle_limit")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["worker", "watch", "--cwd", str(self.repo), "--session", "harness",
                             "--apply", "--max-cycles", "1", "--", *self.good])
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]["format"], "coprogrammer.watch-progress.v1")
        self.assertEqual(rows[-1]["format"], "coprogrammer.watch.v1")
        empty = self.call(apply=True, wait=True, duration=2, poll_seconds=1)
        self.assertEqual(empty["reason"], "duration_limit")

    def test_invalid_limits_do_not_launch(self):
        for kwargs in ({"max_cycles":0},{"max_cycles":101},{"duration":0},{"duration":601},
                       {"poll_seconds":0},{"poll_seconds":26},{"wait":1}):
            with self.subTest(kwargs=kwargs), patch("coprogrammer.runner.Popen") as process, self.assertRaises(RuntimeError):
                self.call(apply=True, **kwargs)
            process.assert_not_called()


class NativeLauncherTests(Fixture):
    def test_launcher_ignoring_profile_stops_before_probe_without_printing_global_paths(self):
        for path in (None, str(self.root / "global.json")):
            with self.subTest(path=path), patch("coprogrammer.runtime_verify.shutil.which", return_value="managed-proxy"), \
                    patch("coprogrammer.runtime_verify._json_command", return_value={"ok":True,"data":{"valid":True,"path":path}}) as command:
                report = runtime_verify.verify(self.repo, "openclaw")
            self.assertEqual(command.call_count, 1)
            self.assertEqual(report["native_client"]["reason"], "isolated_profile_not_used")
            self.assertNotIn("global.json", json.dumps(report))

    def test_explicit_native_executable_checks_its_own_profile(self):
        def native(argv, cwd, timeout, env):
            self.assertEqual(argv[0], "/trusted/openclaw")
            if argv[1] == "config":
                return {"ok":True,"data":{"valid":True,"path":env["OPENCLAW_CONFIG_PATH"]}}
            return {"ok":True,"data":{"tools":["coprogrammer__worker_step","coprogrammer__worker_finish"],"diagnostics":[]}}
        with patch("coprogrammer.runtime_verify.shutil.which", return_value="/trusted/openclaw") as which, \
                patch("coprogrammer.runtime_verify._json_command", side_effect=native):
            report = runtime_verify.verify(self.repo, "openclaw", native_executable="/trusted/openclaw")
        which.assert_called_once_with("/trusted/openclaw")
        self.assertEqual(report["native_client"]["status"], "verified")

    def test_native_override_rejected_for_other_hosts_and_invalid_values(self):
        for client, value in (("claude","openclaw"),("openclaw",1),("openclaw",""),("openclaw","x\0y")):
            with self.subTest(client=client), self.assertRaises(RuntimeError):
                runtime_verify.verify(self.repo, client, native_executable=value)
