"""Offline interrupts with actual atomic mutations and owned child processes."""
import contextlib
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, manager_store, runner, scheduler
from test_workspace_workflow import Fixture


class RunnerInterruptTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "harness", "harness", "interrupt")
        scheduler.create(self.path, self.repo, "harness", "api", "API", ["src/**"])
        self.good = [sys.executable, "-c", "import json;print(json.dumps({'status':'done','summary':'Offline completion'}))"]

    def call_cli(self, command=None, *options):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["worker", "run", "--cwd", str(self.repo), "--session", "harness",
                             "--apply", *options, "--", *(command or self.good)])
        self.assertEqual(code, 130)
        report = json.loads(output.getvalue())
        self.assertEqual(report["state"], "stopped")
        self.assertEqual(report["reason"], "interrupted")
        self.assertNotIn("claim_id", output.getvalue())
        self.assertNotIn("Offline completion", output.getvalue())
        return report

    def peer(self):
        other = self.root / "other"
        self.git("worktree", "add", "-b", "other", str(other))
        co.register(self.path, other, "other", "harness", "interrupt")
        return other

    def assert_stopped(self, pid):
        state = Path("/proc") / str(pid) / "stat"
        deadline = time.monotonic() + 2
        while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z")

    @contextlib.contextmanager
    def interrupt_commit(self, event_type, after):
        original = manager_store.EventTransaction.commit
        calls = []
        def commit(tx):
            if tx.path == self.path and any(e["type"] == event_type for e in tx.pending):
                calls.append(1)
                if after:
                    original(tx)
                raise KeyboardInterrupt
            return original(tx)
        with patch.object(manager_store.EventTransaction, "commit", commit):
            yield
        self.assertEqual(len(calls), 1, "Interrupted mutation must not be replayed")

    def boundary_interrupt(self, after):
        with self.interrupt_commit("task.claimed", after), patch("coprogrammer.runner.Popen") as process:
            report = self.call_cli()
        process.assert_not_called()
        self.assertEqual(report["interruption_phase"], "boundary")
        self.assertFalse(report["launched"])
        self.assertIsNone(report["claim_retained"])
        self.assertEqual(report["completion_status"], "not_attempted")
        events = manager_store.load_events(self.path)
        self.assertEqual(sum(e["type"] == "task.claimed" for e in events), int(after))
        self.assertFalse(any(e["type"] in ("task.finished", "lease.released") for e in events))

    def test_boundary_before_commit_is_unknown_without_launch(self):
        self.boundary_interrupt(False)

    def test_boundary_after_commit_is_unknown_without_reclaim(self):
        self.boundary_interrupt(True)

    def finish_interrupt(self, after):
        self.peer()
        with self.interrupt_commit("task.finished", after):
            report = self.call_cli(None, "--notify", "other")
        self.assertEqual(report["interruption_phase"], "finalizing")
        self.assertTrue(report["launched"])
        self.assertEqual(report["exit_code"], 0)
        self.assertIsNone(report["claim_retained"])
        self.assertEqual(report["completion_status"], "unknown")
        events = manager_store.load_events(self.path)
        for event_type in ("task.finished", "lease.released", "message.sent"):
            self.assertEqual(sum(e["type"] == event_type for e in events), int(after))
        self.assertEqual(sum(e["type"] == "task.claimed" for e in events), 1)

    def test_finish_before_commit_retains_atomic_claim_without_false_success(self):
        self.finish_interrupt(False)

    def test_finish_after_commit_does_not_release_or_notify_twice(self):
        self.finish_interrupt(True)

    def receipt_interrupt(self, after):
        other = self.peer()
        for body in ("First private synthetic message", "Second private synthetic message"):
            co.send(self.path, other, "other", "harness", "interrupt", body)
        command = [sys.executable, "-c", "import json,sys;x=json.load(sys.stdin);print(json.dumps({'status':'received','summary':'Read messages','acknowledge':[m['id'] for m in x['messages']]}))"]
        with self.interrupt_commit("message.acknowledged", after):
            report = self.call_cli(command, "--handle-inbox")
        self.assertEqual(report["interruption_phase"], "acknowledging")
        self.assertEqual(report["receipt_status"], "unknown")
        self.assertEqual(report["completion_status"], "not_attempted")
        self.assertNotIn("acknowledged", report)
        self.assertFalse(report["claim_retained"])
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(co.inbox(self.path, "harness")["pending_total"], 0 if after else 2)
        events = manager_store.load_events(self.path)
        self.assertEqual(sum(e["type"] == "message.acknowledged" for e in events), 2 if after else 0)
        self.assertFalse(any(e["type"] == "task.finished" for e in events))

    def test_receipt_before_commit_acknowledges_none_atomically(self):
        self.receipt_interrupt(False)

    def test_receipt_after_commit_does_not_acknowledge_again_or_invent_count(self):
        self.receipt_interrupt(True)

    def test_python_api_still_raises_keyboard_interrupt(self):
        with patch("coprogrammer.worker.step", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt) as caught:
                runner.run(self.path, self.repo, "harness", self.good, apply=True)
        self.assertIsInstance(caught.exception, runner.RunInterrupted)
        self.assertEqual(caught.exception.report["interruption_phase"], "boundary")

    def test_interruption_before_boundary_does_not_invent_claim_facts(self):
        with patch("coprogrammer.runner.co.workspace", side_effect=KeyboardInterrupt), \
             patch("coprogrammer.runner.Popen") as process:
            report = self.call_cli()
        process.assert_not_called()
        self.assertEqual(report["interruption_phase"], "before_launch")
        self.assertIsNone(report["claim_retained"])
        self.assertFalse(any(e["type"] == "task.claimed" for e in manager_store.load_events(self.path)))

    def test_injected_popen_interrupt_reports_unknown_launch(self):
        with patch("coprogrammer.runner.Popen", side_effect=KeyboardInterrupt):
            report = self.call_cli()
        self.assertEqual(report["interruption_phase"], "launching")
        self.assertIsNone(report["launched"])
        self.assertIsNone(report["exit_code"])
        self.assertTrue(report["claim_retained"])

    @unittest.skipUnless(os.name == "posix", "POSIX default SIGINT and process tree fixture")
    def test_sigint_during_popen_handoff_defers_until_handle_can_be_cleaned(self):
        original = runner.Popen
        launched = []
        handler = signal.getsignal(signal.SIGINT)
        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            launched.append(process)
            os.kill(os.getpid(), signal.SIGINT)
            return process
        with patch("coprogrammer.runner.Popen", side_effect=launch):
            report = self.call_cli([sys.executable, "-c", "import time;time.sleep(60)"])
        self.assertEqual(report["interruption_phase"], "launching")
        self.assertTrue(report["launched"])
        self.assertIsNone(report["exit_code"])
        self.assertIsNotNone(launched[0].poll())
        self.assertEqual(report["cleanup_status"], "confirmed")
        self.assertIs(signal.getsignal(signal.SIGINT), handler)

    @unittest.skipUnless(os.name == "posix", "POSIX default SIGINT cleanup fixture")
    def test_sigint_during_cleanup_preserves_original_exit_and_finishes_cleanup(self):
        original = runner._stop
        handler = signal.getsignal(signal.SIGINT)
        stopped = []
        def stop(process):
            os.kill(os.getpid(), signal.SIGINT)
            os.kill(os.getpid(), signal.SIGINT)
            original(process)
            stopped.append(process)
        with patch("coprogrammer.runner._stop", side_effect=stop):
            report = self.call_cli()
        self.assertEqual(report["interruption_phase"], "cleanup")
        self.assertEqual(report["exit_code"], 0)
        self.assertTrue(report["claim_retained"])
        self.assertTrue(stopped)
        self.assertEqual(len(stopped), 1)
        self.assertTrue(all(p.poll() is not None for p in stopped))
        self.assertIs(signal.getsignal(signal.SIGINT), handler)
        self.assertFalse(any(e["type"] == "task.finished" for e in manager_store.load_events(self.path)))

    @unittest.skipUnless(os.name == "posix", "POSIX owned process cleanup entry fixture")
    def test_interrupt_at_cleanup_entry_still_stops_owned_process(self):
        original = runner._defer_sigint
        interrupted = False
        marker = self.root / "grandchild.pid"
        code = ("import pathlib,subprocess,sys,json;"
                "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
                f"pathlib.Path({str(marker)!r}).write_text(str(child.pid));"
                "print(json.dumps({'status':'done','summary':'Offline completion'}))")
        @contextlib.contextmanager
        def enter(observed):
            nonlocal interrupted
            if observed["phase"] == "cleanup" and not interrupted:
                interrupted = True
                raise KeyboardInterrupt
            with original(observed):
                yield
        try:
            with patch("coprogrammer.runner._defer_sigint", enter):
                report = self.call_cli([sys.executable, "-c", code])
            pid = int(marker.read_text())
            if sys.platform.startswith("linux"):
                self.assert_stopped(pid)
        finally:
            if marker.exists():
                try:
                    os.kill(int(marker.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.assertEqual(report["interruption_phase"], "cleanup")
        self.assertTrue(report["claim_retained"])
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["cleanup_status"], "confirmed")
        self.assertFalse(any(e["type"] == "task.finished" for e in manager_store.load_events(self.path)))

    def cleanup_error(self, persistent, error_type):
        original_popen, original_stop = runner.Popen, runner._stop
        launched, stops = [], []
        def launch(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            launched.append(process)
            process.communicate = lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt())
            return process
        def stop(process):
            stops.append(1)
            if persistent or len(stops) == 1:
                if error_type is subprocess.TimeoutExpired:
                    raise error_type(["private synthetic argv"], 10)
                raise error_type("private synthetic cleanup failure")
            original_stop(process)
        try:
            with patch("coprogrammer.runner.Popen", side_effect=launch), \
                 patch("coprogrammer.runner._stop", side_effect=stop):
                report = self.call_cli([sys.executable, "-c", "import time;time.sleep(60)"])
            self.assertEqual(report["interruption_phase"], "running")
            self.assertEqual(report["cleanup_status"], "unknown" if persistent else "confirmed")
            self.assertIsNone(report["exit_code"])
            self.assertTrue(report["claim_retained"])
            self.assertEqual(len(stops), 2, "Owned cleanup recovery must be bounded")
            self.assertNotIn("private synthetic", json.dumps(report))
        finally:
            for process in launched:
                original_stop(process)
                if process.stdin is not None:
                    process.stdin.close()

    def test_cleanup_error_does_not_replace_interruption_and_owned_cleanup_can_finish(self):
        for error in (OSError, subprocess.TimeoutExpired):
            with self.subTest(error=error.__name__):
                self.cleanup_error(False, error)

    def test_persistent_cleanup_error_reports_unknown_without_unbounded_retries(self):
        for error in (OSError, subprocess.TimeoutExpired):
            with self.subTest(error=error.__name__):
                self.cleanup_error(True, error)

    @unittest.skipUnless(os.name == "posix", "POSIX custom SIGINT handler fixture")
    def test_custom_sigint_handler_is_preserved(self):
        previous = signal.getsignal(signal.SIGINT)
        signals = []
        def custom(number, _frame):
            signals.append(number)
        original = runner.Popen
        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            os.kill(os.getpid(), signal.SIGINT)
            return process
        signal.signal(signal.SIGINT, custom)
        try:
            with patch("coprogrammer.runner.Popen", side_effect=launch):
                result = runner.run(self.path, self.repo, "harness", self.good, apply=True)
            self.assertEqual(result["state"], "done")
            self.assertEqual(signals, [signal.SIGINT])
            self.assertIs(signal.getsignal(signal.SIGINT), custom)
        finally:
            signal.signal(signal.SIGINT, previous)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc process tree observation")
    def test_real_cli_sigint_stops_child_grandchild_and_retains_edits_claim_and_lock(self):
        marker = self.root / "pids.json"
        code = ("import os,sys,pathlib,json,subprocess,time;"
                "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
                "pathlib.Path('src/partial.txt').write_text('Partial offline edit');"
                f"pathlib.Path({str(marker)!r}).write_text(json.dumps([os.getpid(),child.pid]));"
                "print('PRIVATE NATIVE OUTPUT',flush=True);time.sleep(60)")
        env = dict(os.environ, PYTHONPATH=str(Path(runner.__file__).parents[1]))
        process = subprocess.Popen([sys.executable, "-m", "coprogrammer", "worker", "run",
                                    "--cwd", str(self.repo), "--session", "harness", "--apply",
                                    "--", sys.executable, "-c", code], cwd=self.repo, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = []
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), "Offline child fixture did not start")
            pids = json.loads(marker.read_text())
            process.send_signal(signal.SIGINT)
            output, errors = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 130)
            report = json.loads(output)
            self.assertEqual(errors, b"")
            self.assertEqual(report["interruption_phase"], "running")
            self.assertTrue(report["launched"])
            self.assertTrue(report["claim_retained"])
            self.assertIsNone(report["exit_code"])
            self.assertNotIn(b"PRIVATE NATIVE OUTPUT", output)
            self.assertNotIn(b"claim_id", output)
            for pid in pids:
                self.assert_stopped(pid)
            self.assertEqual((self.repo / "src/partial.txt").read_text(), "Partial offline edit")
            events = manager_store.load_events(self.path)
            self.assertEqual(sum(e["type"] == "task.claimed" for e in events), 1)
            self.assertFalse(any(e["type"] in ("task.finished", "message.acknowledged", "lease.released") for e in events))
            self.assertEqual(report["cleanup_status"], "confirmed")
            # Acquire the same existing runner lock without launching/replaying
            # the side-effecting command or changing its retained claim.
            workspace = co.workspace(self.repo)
            name = hashlib.sha256(workspace["worktree"].encode()).hexdigest()
            with manager_store.transaction(self.path.parent / "runs" / f"{name}.jsonl", timeout=.25):
                pass
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
