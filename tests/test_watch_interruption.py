"""Offline watch recovery evidence; synthetic processes and Manager state only."""
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import collaboration as co, manager_store, runner, scheduler, watcher
from test_workspace_workflow import Fixture


class WatchInterruptionTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, 'harness', 'harness', 'watch-recovery')
        self.command = [sys.executable, '-c',
                        "import json;print(json.dumps({'status':'done','summary':'Synthetic done'}))"]

    def call(self, **kwargs):
        return watcher.watch(self.path, self.repo, 'harness', self.command,
                             apply=True, max_cycles=3, **kwargs)

    def finish_interruption(self, committed):
        scheduler.create(self.path, self.repo, 'harness', 'one', 'Task', ['src/**'])
        original = manager_store.EventTransaction.commit
        attempts = []
        def interrupt(tx):
            if tx.path == self.path and any(e['type'] == 'task.finished' for e in tx.pending):
                attempts.append(1)
                if committed:
                    original(tx)
                raise KeyboardInterrupt('synthetic private exception')
            return original(tx)
        with patch.object(manager_store.EventTransaction, 'commit', interrupt):
            report = self.call()
        self.assertEqual(attempts, [1])
        self.assertEqual(report['reason'], 'interrupted')
        self.assertEqual(report['cycles'], 1)
        self.assertEqual(report['completed_tasks'], 0)
        self.assertEqual(report['last'].get('interruption_phase'), 'finalizing')
        self.assertEqual(report['last']['completion_status'], 'unknown')
        self.assertEqual(report['last']['cleanup_status'], 'confirmed')
        self.assertTrue(report['last']['launched'])
        events = manager_store.load_events(self.path)
        self.assertEqual(sum(e['type'] == 'task.finished' for e in events), int(committed))
        self.assertEqual(sum(e['type'] == 'task.claimed' for e in events), 1)
        for private in ('synthetic private exception', 'Synthetic done', 'claim_id'):
            self.assertNotIn(private, json.dumps(report['last']))

    def test_finish_not_committed_stays_unknown_without_replay(self):
        self.finish_interruption(False)

    def test_finish_committed_stays_unknown_without_replay(self):
        self.finish_interruption(True)

    def test_committed_ack_stays_unknown_and_does_not_increment_counter(self):
        peer = self.root / 'peer'
        self.git('worktree', 'add', '-b', 'peer', str(peer))
        co.register(self.path, peer, 'peer', 'harness', 'watch-recovery')
        co.send(self.path, peer, 'peer', 'harness', 'one', 'Synthetic private message')
        self.command = [sys.executable, '-c',
                        "import json,sys;p=json.load(sys.stdin);print(json.dumps({'status':'received','summary':'Read','acknowledge':[m['id'] for m in p['messages']]}))"]
        original = manager_store.EventTransaction.commit
        attempts = []
        def interrupt(tx):
            if tx.path == self.path and any(e['type'] == 'message.acknowledged' for e in tx.pending):
                attempts.append(1)
                original(tx)
                raise KeyboardInterrupt
            return original(tx)
        with patch.object(manager_store.EventTransaction, 'commit', interrupt):
            report = self.call(handle_inbox=True)
        self.assertEqual(attempts, [1])
        self.assertEqual(report['acknowledged_messages'], 0)
        self.assertEqual(report['last'].get('interruption_phase'), 'acknowledging')
        self.assertEqual(report['last']['receipt_status'], 'unknown')
        self.assertEqual(co.inbox(self.path, 'harness')['pending_total'], 0)
        self.assertNotIn('Synthetic private message', json.dumps(report['last']))

    def test_unknown_launch_and_cleanup_are_preserved_without_inference(self):
        preview = runner.run(self.path, self.repo, 'harness', self.command)
        interrupted = {'format': 'coprogrammer.runner.v1', 'applied': True,
                       'state': 'stopped', 'reason': 'interrupted',
                       'interruption_phase': 'launching', 'launched': None,
                       'cleanup_status': 'unknown', 'claim_retained': None,
                       'completion_status': 'not_attempted', 'receipt_status': 'not_attempted'}
        with patch.object(runner, 'run', side_effect=[preview, runner.RunInterrupted(interrupted)]) as run:
            report = self.call()
        self.assertEqual(run.call_count, 2)  # One preview and one applied boundary.
        self.assertEqual(report['last'], interrupted)
        self.assertEqual(report['completed_tasks'], 0)

    def test_plain_wait_interrupt_retains_last_boundary(self):
        with patch.object(watcher.channels, 'wait', side_effect=KeyboardInterrupt):
            report = self.call(wait=True)
        self.assertEqual(report['reason'], 'interrupted')
        self.assertEqual(report['last']['boundary']['state'], 'idle')
        self.assertFalse(report['last']['launched'])
        self.assertNotIn('interruption_phase', report['last'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX SIGINT; Windows native unverified')
    def test_cli_sigint_retains_current_run_and_original_exit_behavior(self):
        scheduler.create(self.path, self.repo, 'harness', 'one', 'Task', ['src/**'])
        marker = self.repo / '.coprogrammer/child.json'
        code = "import os,json,pathlib,time;pathlib.Path('.coprogrammer/child.json').write_text(json.dumps({'pid':os.getpid()}));time.sleep(30)"
        env = dict(os.environ, PYTHONPATH=str(Path(watcher.__file__).resolve().parents[1]))
        process = subprocess.Popen([sys.executable, '-m', 'coprogrammer', 'worker', 'watch',
                                    '--session', 'harness', '--apply', '--', sys.executable, '-c', code],
                                   cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), 'child never reached marker')
            process.send_signal(signal.SIGINT)
            output, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0)  # Existing watch CLI behavior.
            self.assertEqual(error, b'')
            report = json.loads(output.splitlines()[-1])
            self.assertEqual(report['last'].get('reason'), 'interrupted')
            self.assertTrue(report['last']['launched'])
            self.assertTrue(report['last']['claim_retained'])
            self.assertEqual(report['last']['cleanup_status'], 'confirmed')
            self.assertEqual(report['completed_tasks'], 0)
            events = manager_store.load_events(self.path)
            self.assertEqual(sum(e['type'] == 'task.claimed' for e in events), 1)
            self.assertFalse(any(e['type'] == 'task.finished' for e in events))
            child = json.loads(marker.read_text())['pid']
            state = Path('/proc') / str(child) / 'stat'
            if Path('/proc').exists():
                self.assertTrue(not state.exists() or state.read_text().split()[2] == 'Z')
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
