"""Durable CLI inspection and explicit restarts; no real models or accounts."""
import contextlib
import io
import json
import sys
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, manager_store, scheduler
from test_workspace_workflow import Fixture


class WatchRecoveryTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, 'harness', 'harness', 'recovery')
        self.counter = self.repo / '.coprogrammer/calls'
        self.command = [sys.executable, '-c',
                        "import pathlib,json,sys;p=pathlib.Path('.coprogrammer/calls');p.parent.mkdir(exist_ok=True);"
                        "p.write_text(str(int(p.read_text())+1) if p.exists() else '1');x=json.load(sys.stdin);"
                        "print(json.dumps({'status':'done','summary':'Synthetic completion'} if x['kind']=='task' else "
                        "{'status':'received','summary':'Synthetic receipt','acknowledge':[m['id'] for m in x['messages']]}))"]

    def invoke(self, args, *, lines=False):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = cli.main(args)
        raw = output.getvalue()
        return status, (json.loads(raw.splitlines()[-1] if lines else raw) if raw else None), errors.getvalue()

    def watch(self, inbox=False):
        return self.invoke(['worker', 'watch', '--cwd', str(self.repo), '--session', 'harness', '--apply',
                            *(['--handle-inbox'] if inbox else []), '--', *self.command], lines=True)

    def scenario(self, inbox, committed):
        event_type = 'message.acknowledged' if inbox else 'task.finished'
        if inbox:
            peer = self.root / 'peer'
            self.git('worktree', 'add', '-b', 'peer', str(peer))
            co.register(self.path, peer, 'peer', 'harness', 'recovery')
            co.send(self.path, peer, 'peer', 'harness', 'one', 'Synthetic private message')
        else:
            scheduler.create(self.path, self.repo, 'harness', 'one', 'Task', ['src/**'])
        original = manager_store.EventTransaction.commit
        attempts = []
        def interrupt(tx):
            if tx.path == self.path and any(e['type'] == event_type for e in tx.pending):
                attempts.append(1)
                if committed:
                    original(tx)
                raise KeyboardInterrupt
            return original(tx)
        with patch.object(manager_store.EventTransaction, 'commit', interrupt):
            code, report, errors = self.watch(inbox)
        self.assertEqual((code, errors, attempts), (0, '', [1]))
        self.assertEqual(report['reason'], 'interrupted')
        self.assertEqual(report['last']['receipt_status' if inbox else 'completion_status'], 'unknown')
        self.assertEqual(report['acknowledged_messages' if inbox else 'completed_tasks'], 0)
        self.assertEqual(self.counter.read_text(), '1')
        before = self.path.read_bytes()
        code, status, errors = self.invoke(['status', '--cwd', str(self.repo), '--session', 'harness', '--json'])
        self.assertEqual((code, errors), (0, ''))
        counts = status['briefing']['counts']
        self.assertEqual(counts['pending_messages'] if inbox else counts['done'],
                         int(not committed) if inbox else int(committed))
        _, boundary, _ = self.invoke(['worker', 'step', '--cwd', str(self.repo), '--session', 'harness'])
        self.assertNotIn(boundary['state'], ('working', 'inbox') if committed else ())
        if not committed:
            self.assertEqual(boundary['state'], 'inbox' if inbox else 'working')
        self.assertEqual(self.path.read_bytes(), before, 'Inspection must not mutate Manager state')
        # A fresh explicit session resume is not a command replay.
        code, _, _ = self.invoke(['start', '--cwd', str(self.repo), '--client', 'harness',
                                  '--session', 'harness', '--resume', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(self.counter.read_text(), '1')
        # Three user-requested startups: committed work/receipts must not rerun.
        # An uncommitted claim/receipt is retried only by this explicit invocation.
        for _ in range(3):
            self.watch(inbox)
        self.assertEqual(self.counter.read_text(), '1' if committed else '2')
        events = manager_store.load_events(self.path)
        self.assertEqual(sum(e['type'] == event_type for e in events), 1)
        if not inbox:
            self.assertEqual(sum(e['type'] == 'task.claimed' for e in events), 1)

    def test_finish_before_commit_inspection_and_explicit_restart(self):
        self.scenario(False, False)

    def test_finish_after_commit_inspection_and_repeated_startup(self):
        self.scenario(False, True)

    def test_ack_before_commit_inspection_and_explicit_restart(self):
        self.scenario(True, False)

    def test_ack_after_commit_inspection_and_repeated_startup(self):
        self.scenario(True, True)

    def self_notify(self, action):
        scheduler.create(self.path, self.repo, 'harness', 'one', 'Task', ['src/**'])
        before = self.path.read_bytes()
        for apply in (False, True):
            with self.subTest(apply=apply):
                status, _, error = self.invoke(['worker', action, '--cwd', str(self.repo), '--session', 'harness',
                                               '--notify', 'harness', *(['--apply'] if apply else []),
                                               '--', *self.command], lines=action == 'watch')
                self.assertEqual(status, 2)
                self.assertIn('notify must address another session', error)
                self.assertFalse(self.counter.exists(), 'Invalid request launched a side effect')
                self.assertEqual(self.path.read_bytes(), before)

    def test_run_self_notification_rejected_before_claim_or_process(self):
        self.self_notify('run')

    def test_watch_self_notification_rejected_before_claim_or_process(self):
        self.self_notify('watch')
