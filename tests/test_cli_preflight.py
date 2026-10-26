"""CLI snapshot boundaries; Git inspection and runtime locking are permitted."""
import contextlib
import io
import json
import sys

from coprogrammer import cli, collaboration as co, manager_store, scheduler
from test_workspace_workflow import Fixture


class CliPreflightTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, 'harness', 'harness', 'preflight')
        scheduler.create(self.path, self.repo, 'harness', 'one', 'Task', ['src/**'])
        self.marker = self.repo / '.coprogrammer/launched'
        self.command = [sys.executable, '-c',
                        "import pathlib,json;p=pathlib.Path('.coprogrammer/launched');"
                        "p.write_text('launched');print(json.dumps({'status':'done','summary':'Synthetic done'}))"]

    def snapshot(self):
        files = {p.relative_to(self.repo).as_posix(): p.read_bytes() for p in self.repo.rglob('*')
                 if p.is_file() and p.relative_to(self.repo).parts[0] not in ('.git', '.coprogrammer')}
        return self.path.read_bytes(), files

    def invoke(self, args, lines=False):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            try:
                code = cli.main(args)
            except SystemExit as exc:
                code = exc.code
        raw = output.getvalue()
        return code, (json.loads(raw.splitlines()[-1] if lines else raw) if raw else None), error.getvalue()

    def peer(self):
        peer = self.root / 'peer'
        self.git('worktree', 'add', '-b', 'peer', str(peer))
        co.register(self.path, peer, 'peer', 'harness', 'preflight')
        return peer

    def closed_target(self, action):
        co.pulse(self.path, self.peer(), 'peer', status='closed')
        before = self.snapshot()
        for apply in (False, True):
            with self.subTest(apply=apply):
                code, _, error = self.invoke(['worker', action, '--cwd', str(self.repo), '--session', 'harness',
                                              '--notify', 'peer', *(['--apply'] if apply else []),
                                              '--', *self.command], lines=action == 'watch')
                self.assertFalse(self.marker.exists(), 'Closed recipient request launched the harness')
                self.assertEqual((code, self.snapshot()), (2, before))
                self.assertIn('session is closed: peer', error)

    def test_run_closed_target_rejected_before_claim_or_process(self):
        self.closed_target('run')

    def test_watch_closed_target_rejected_before_claim_or_process(self):
        self.closed_target('watch')

    def test_missing_or_invalid_static_inputs_leave_event_and_project_bytes(self):
        before = self.snapshot()
        cases = [('missing-command', [], [], 'harness'),
                 ('timeout', ['--timeout-seconds', '0'], self.command, 'harness'),
                 ('duplicate-recipient', ['--notify', 'peer', '--notify', 'peer'], self.command, 'harness'),
                 ('invalid-recipient', ['--notify', 'bad/id'], self.command, 'harness'),
                 ('unknown-recipient', ['--notify', 'absent'], self.command, 'harness'),
                 ('unknown-session', [], self.command, 'absent')]
        for action in ('run', 'watch'):
            for apply in (False, True):
                for label, options, command, session in cases:
                    with self.subTest(action=action, apply=apply, case=label):
                        code, _, _ = self.invoke(['worker', action, '--cwd', str(self.repo), '--session', session,
                                                  *options, *(['--apply'] if apply else []), '--', *command],
                                                 lines=action == 'watch')
                        self.assertEqual(code, 2)
                        self.assertEqual(self.snapshot(), before)
                        self.assertFalse(self.marker.exists())

    def test_status_setup_preview_and_invalid_resume_preserve_content(self):
        before = self.snapshot()
        cases = [(['status', '--session', 'harness', '--json'], 0),
                 (['status', '--session', 'absent', '--json'], 2),
                 (['start', '--client', 'codex', '--session', 'new', '--apply-setup', '--dry-run', '--json'], 0),
                 (['start', '--client', 'harness', '--session', 'absent', '--resume', '--apply-setup', '--dry-run', '--json'], 2),
                 (['start', '--client', 'harness', '--session', 'harness', '--apply-setup', '--json'], 2),
                 (['worker', 'step', '--session', 'harness', '--id', 'absent', '--apply'], 2)]
        for args, expected in cases:
            with self.subTest(args=args):
                code, _, _ = self.invoke([*args, '--cwd', str(self.repo)])
                self.assertEqual(code, expected)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.marker.exists())

    def test_blocked_peer_still_receives_explicit_completion_notification(self):
        co.pulse(self.path, self.peer(), 'peer', status='blocked')
        before = self.snapshot()
        args = ['worker', 'run', '--cwd', str(self.repo), '--session', 'harness', '--notify', 'peer']
        code, report, _ = self.invoke([*args, '--', *self.command])
        self.assertEqual(code, 0)
        self.assertFalse(report['applied'])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.marker.exists())
        code, report, _ = self.invoke([*args, '--apply', '--', *self.command])
        self.assertEqual((code, report['state']), (0, 'done'))
        messages = co.inbox(self.path, 'peer')['messages']
        self.assertEqual(len(messages), 1)
        self.assertIsNone(messages[0]['acknowledged_at'])

    def test_unavailable_executable_retains_claim_for_explicit_retry(self):
        args = ['worker', 'run', '--cwd', str(self.repo), '--session', 'harness', '--apply',
                '--', str(self.root / 'missing-executable')]
        claims = []
        for _ in range(2):
            code, report, _ = self.invoke(args)
            self.assertEqual((code, report['reason']), (1, 'command_unavailable'))
            self.assertFalse(report['launched'])
            self.assertTrue(report['claim_retained'])
            claims.append(report['boundary']['task']['claim_id'])
        self.assertEqual(claims[0], claims[1])
        self.assertEqual(sum(e['type'] == 'task.claimed' for e in manager_store.load_events(self.path)), 1)
        self.assertFalse(self.marker.exists())
