"""Opt-in retry protection with synthetic subprocesses; no model accounts."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, runner, scheduler as sc, worker
from coprogrammer.manager_store import load_events
from test_workspace_workflow import Fixture


class RetryGuardTests(Fixture):
    def setUp(self):
        super().setUp()
        self.session()
        self.task()
        self.count = self.root / 'calls'
        self.marker = self.root / 'started'
        self.content = self.repo / 'src/main.py'
        self.run_log = self.path.parent / 'runs' / (hashlib.sha256(str(self.repo).encode()).hexdigest() + '.jsonl')

    def command(self, mode='fail'):
        code = '''import json,sys,os,time
from pathlib import Path
json.load(sys.stdin)
p=Path(sys.argv[1]); n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n))
Path('src/main.py').write_text('synthetic-'+str(n))
Path(sys.argv[2]).write_text(str(os.getpid()))
if sys.argv[3]=='wait': time.sleep(60)
if sys.argv[3]=='fail': raise SystemExit(1)
print(json.dumps({'status':'done','summary':'Synthetic done'}))
'''
        return [sys.executable, '-c', code, str(self.count), str(self.marker), mode]

    def call(self, mode='fail', **kwargs):
        return runner.run(self.path, self.repo, 'codex', self.command(mode), apply=True,
                          protect_retry=True, **kwargs)

    def task_view(self):
        return sc.board(load_events(self.path))['tasks'][0]

    def test_unchanged_retry_completes_with_same_claim(self):
        failed = self.call()
        claim = self.task_view()['claim_id']
        self.assertEqual(failed['reason'], 'command_failed')
        self.assertTrue(failed['claim_retained'])
        records = load_events(self.run_log)
        self.assertEqual([e['type'] for e in records], ['retry.started', 'retry.finished'])
        for event in records:
            self.assertEqual(set(event['payload']), {'session', 'claim_id', 'content_sha256'})
        self.assertNotIn('synthetic-', self.run_log.read_text())
        self.assertEqual(self.call('done')['state'], 'done')
        self.assertEqual(self.task_view()['claim_id'], claim)
        self.assertEqual(self.count.read_text(), '2')

    def test_external_edit_blocks_repeated_attempts_without_rebaselining(self):
        self.call()
        before = self.run_log.read_bytes()
        self.content.write_text('PRIVATE_NEW_RESULT')
        for _ in range(2):
            report = self.call('done')
            self.assertEqual(report['reason'], 'retry_content_changed')
            self.assertFalse(report['launched'])
            self.assertTrue(report['claim_retained'])
            self.assertEqual(self.run_log.read_bytes(), before)
            self.assertEqual(self.content.read_text(), 'PRIVATE_NEW_RESULT')
            self.assertNotIn('PRIVATE_NEW_RESULT', json.dumps(report))
        self.assertEqual(self.count.read_text(), '1')

    def test_external_addition_blocks_before_launch(self):
        self.call()
        added = self.repo / 'src/new.txt'
        added.write_text('PRIVATE_NEW_FILE')
        self.assertEqual(self.call('done')['reason'], 'retry_content_changed')
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(added.read_text(), 'PRIVATE_NEW_FILE')

    def test_external_deletion_blocks_before_launch(self):
        self.call()
        self.content.unlink()
        self.assertEqual(self.call('done')['reason'], 'retry_content_changed')
        self.assertEqual(self.count.read_text(), '1')
        self.assertFalse(self.content.exists())

    def test_ignored_untracked_changes_are_outside_retry_protection(self):
        from coprogrammer import retry_guard, workspace as ws
        ignored = self.repo / 'src/output.cache'
        with (self.repo / '.gitignore').open('a') as stream:
            stream.write('src/*.cache\n')
        self.commit()
        command = self.command()
        command[2] = command[2].replace(
            "Path(sys.argv[2]).write_text(str(os.getpid()))",
            "Path('src/output.cache').write_text('synthetic-cache-'+str(n))\n"
            "Path(sys.argv[2]).write_text(str(os.getpid()))")
        for change in ('modify', 'delete', 'add'):
            with self.subTest(change=change):
                if change == 'add' and ignored.exists():
                    ignored.unlink()
                if change != 'add':
                    ignored.write_text('synthetic-initial-cache')
                self.call()  # End baseline excludes this untracked ignored file.
                before = retry_guard._digest(self.repo)
                if change == 'delete':
                    ignored.unlink()
                else:
                    ignored.write_text('SYNTHETIC_EXTERNAL_CACHE')
                self.assertEqual(retry_guard._digest(self.repo), before)
                count = int(self.count.read_text())
                with patch.object(ws, '_content', wraps=ws._content) as observe:
                    result = runner.run(self.path, self.repo, 'codex', command,
                                        apply=True, protect_retry=True)
                self.assertEqual(result['reason'], 'command_failed')
                self.assertTrue(result['launched'])
                self.assertEqual(int(self.count.read_text()), count + 1)
                self.assertEqual(ignored.read_text(), 'synthetic-cache-'+str(count + 1))
                self.assertEqual(observe.call_count, 6)  # Two passes at start, prelaunch and end.
                self.assertNotIn('SYNTHETIC_EXTERNAL_CACHE', self.run_log.read_text())

    def test_tracked_file_matching_ignore_rule_is_still_protected(self):
        # Git excludes untracked ignored files, not tracked files with that name.
        exclude = self.repo / '.git/info/exclude'
        with exclude.open('a') as stream:
            stream.write('\nsrc/main.py\n')
        self.assertEqual(self.git('check-ignore', '--no-index', 'src/main.py'), 'src/main.py')
        self.call()
        self.content.write_text('SYNTHETIC_TRACKED_CHANGE')
        before = self.run_log.read_bytes()
        self.assertEqual(self.call()['reason'], 'retry_content_changed')
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'SYNTHETIC_TRACKED_CHANGE')
        self.assertEqual(self.run_log.read_bytes(), before)

    def test_cli_preview_then_external_edit_is_rechecked_on_apply(self):
        self.call()
        before = self.run_log.read_bytes()
        env = {**os.environ, 'PYTHONPATH': str(Path(runner.__file__).parents[1])}
        prefix = [sys.executable, '-m', 'coprogrammer', 'worker', 'run',
                  '--session', 'codex', '--protect-retry']
        preview = subprocess.run(prefix + ['--', *self.command('done')],
                                 cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(json.loads(preview.stdout)['applied'])
        self.assertEqual(self.run_log.read_bytes(), before)
        self.content.write_text('SYNTHETIC_AFTER_PREVIEW')
        applied = subprocess.run(prefix + ['--apply', '--', *self.command('done')],
                                 cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(applied.returncode, 1, applied.stderr)
        report = json.loads(applied.stdout)
        self.assertEqual(report['reason'], 'retry_content_changed')
        self.assertFalse(report['launched'])
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'SYNTHETIC_AFTER_PREVIEW')
        self.assertEqual(self.run_log.read_bytes(), before)

    def test_change_between_snapshot_passes_stops_before_launch(self):
        from coprogrammer import workspace as ws
        self.call()
        before = self.run_log.read_bytes()
        content = ws._content
        observations = []
        def change_after_first_pass(cwd):
            result = content(cwd)
            observations.append(result)
            if len(observations) == 1:
                self.content.write_text('SYNTHETIC_DURING_OBSERVATION')
            return result
        with patch.object(ws, '_content', side_effect=change_after_first_pass):
            with self.assertRaisesRegex(RuntimeError, 'stable project content'):
                self.call()
        self.assertEqual(len(observations), 2)
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'SYNTHETIC_DURING_OBSERVATION')
        self.assertEqual(self.run_log.read_bytes(), before)

    def test_external_edit_after_check_is_not_an_atomic_write_guard(self):
        from coprogrammer import retry_guard
        self.call()
        claim = self.task_view()['claim_id']
        popen = runner.Popen
        before_launch = []
        def edit_then_launch(*args, **kwargs):
            # Deterministic external-editor interleaving; no timing/sleep race.
            self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')
            self.content.write_text('SYNTHETIC_AFTER_CHECK')
            before_launch.append(1)
            return popen(*args, **kwargs)
        with patch.object(runner, 'Popen', side_effect=edit_then_launch):
            report = self.call()
        self.assertEqual(before_launch, [1])
        self.assertEqual(report['reason'], 'command_failed')
        self.assertEqual(self.count.read_text(), '2')
        self.assertEqual(self.content.read_text(), 'synthetic-2')
        self.assertEqual(self.task_view()['claim_id'], claim)
        self.assertEqual(load_events(self.run_log)[-1]['payload']['content_sha256'],
                         retry_guard._digest(self.repo))

    def test_content_preserving_commit_does_not_block_retry(self):
        self.call()
        self.commit()
        self.assertEqual(self.call('done')['state'], 'done')
        self.assertEqual(self.count.read_text(), '2')

    def test_prelaunch_edit_during_start_record_commit_is_preserved(self):
        from coprogrammer import manager_store
        self.call()
        claim = self.task_view()['claim_id']
        original = load_events(self.run_log)
        replace = manager_store._replace_event_log
        writes = []
        def persist_then_edit(source, target):
            result = replace(source, target)
            if target == self.run_log:
                writes.append(1)
                if len(writes) == 1:
                    self.content.write_text('SYNTHETIC_DURING_COMMIT')
            return result
        with patch.object(manager_store, '_replace_event_log', side_effect=persist_then_edit):
            result = self.call('done')
        self.assertEqual(result.get('reason'), 'retry_prelaunch_content_changed')
        self.assertFalse(result['launched'])
        self.assertTrue(result['claim_retained'])
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'SYNTHETIC_DURING_COMMIT')
        self.assertEqual(self.task_view()['claim_id'], claim)
        self.assertEqual(load_events(self.run_log)[:-1], original)
        self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')
        self.assertNotIn('SYNTHETIC_DURING_COMMIT', json.dumps(result))
        self.assertEqual(self.call()['reason'], 'retry_attempt_incomplete')
        self.assertEqual(self.count.read_text(), '1')

    def test_prelaunch_edit_during_output_setup_is_preserved(self):
        self.call()
        temporary = runner.tempfile.TemporaryFile
        opened = []
        def open_then_edit(*args, **kwargs):
            output = temporary(*args, **kwargs)
            opened.append(output)
            self.content.write_text('SYNTHETIC_DURING_OUTPUT_SETUP')
            return output
        with patch.object(runner.tempfile, 'TemporaryFile', side_effect=open_then_edit):
            result = self.call('done')
        self.assertEqual(result.get('reason'), 'retry_prelaunch_content_changed')
        self.assertFalse(result['launched'])
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'SYNTHETIC_DURING_OUTPUT_SETUP')
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].closed)
        self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')

    def test_prelaunch_snapshot_error_keeps_incomplete_record_without_child(self):
        from coprogrammer import retry_guard
        self.call()
        digest = retry_guard._digest
        snapshots = []
        def fail_before_launch(cwd):
            snapshots.append(1)
            if len(snapshots) == 2:
                raise RuntimeError('synthetic prelaunch observation failure')
            return digest(cwd)
        with patch.object(retry_guard, '_digest', side_effect=fail_before_launch):
            with self.assertRaisesRegex(RuntimeError, 'synthetic prelaunch'):
                self.call()
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'synthetic-1')
        self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')
        self.assertEqual(self.call()['reason'], 'retry_attempt_incomplete')

    def test_legacy_run_never_calls_prelaunch_content_check(self):
        from coprogrammer import retry_guard
        with patch.object(retry_guard, 'check_launch', side_effect=AssertionError('guard must stay opt-in')):
            result = runner.run(self.path, self.repo, 'codex', self.command('done'), apply=True)
        self.assertEqual(result['state'], 'done')
        self.assertEqual(self.count.read_text(), '1')
        self.assertFalse(self.run_log.exists())

    def test_existing_unprotected_claim_has_no_invented_baseline(self):
        runner.run(self.path, self.repo, 'codex', self.command(), apply=True)
        self.content.write_text('PRIVATE_NEW_RESULT')
        self.assertEqual(self.call()['reason'], 'retry_baseline_missing')
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'PRIVATE_NEW_RESULT')

    def test_preview_has_no_execution_or_retry_log(self):
        before = self.path.read_bytes()
        preview = runner.run(self.path, self.repo, 'codex', self.command(), protect_retry=True)
        self.assertFalse(preview['applied'])
        self.assertFalse(self.count.exists())
        self.assertFalse(self.run_log.exists())
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_explicit_retry_is_unchanged(self):
        for index in range(2):
            if index:
                self.content.write_text('newer-user-result')
            result = runner.run(self.path, self.repo, 'codex', self.command(), apply=True)
            self.assertEqual(result['reason'], 'command_failed')
        self.assertEqual(self.count.read_text(), '2')
        self.assertEqual(self.content.read_text(), 'synthetic-2')
        self.assertFalse(self.run_log.exists())

    def test_completed_task_and_notification_retries_remain_idempotent(self):
        peer = self.root / 'peer'
        self.git('worktree', 'add', '-b', 'peer', str(peer))
        co.register(self.path, peer, 'peer', 'harness', 'synthetic')
        self.assertEqual(self.call('done', notify=['peer'])['state'], 'done')
        task = self.task_view()
        self.content.write_text('newer-user-result')
        self.assertFalse(self.call('done')['launched'])
        done = worker.finish(self.path, self.repo, 'codex', 'api', task['claim_id'], 'Synthetic done', ['peer'])
        self.assertTrue(done['duplicate'])
        self.assertEqual(co.inbox(self.path, 'peer')['pending_total'], 1)
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'newer-user-result')

    def test_expired_claim_is_fenced_before_retry_check(self):
        self.call()
        original = self.task_view()
        sc.renew(self.path, self.repo, 'codex', 'api', original['claim_id'], ttl_seconds=1)
        later = datetime.now(timezone.utc) + timedelta(seconds=3)
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return later if tz else later.replace(tzinfo=None)
        before = self.run_log.read_bytes()
        with patch.object(cli, 'datetime', Later), patch.object(sc, 'datetime', Later), patch.object(co, 'datetime', Later):
            with self.assertRaisesRegex(RuntimeError, 'expired'):
                self.call()
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.run_log.read_bytes(), before)

    def test_bad_or_missing_local_record_does_not_authorize_retry(self):
        self.call()
        original = self.run_log.read_bytes()
        records = [json.loads(line) for line in original.splitlines()]
        records[-1]['payload']['content_sha256'] = 'PRIVATE_INVALID_DIGEST'
        self.run_log.write_text(''.join(json.dumps(e)+'\n' for e in records))
        with self.assertRaisesRegex(RuntimeError, 'invalid local record'):
            self.call()
        self.run_log.unlink()
        self.assertEqual(self.call()['reason'], 'retry_baseline_missing')
        self.assertEqual(self.count.read_text(), '1')

    def test_end_snapshot_failure_leaves_incomplete_marker(self):
        from coprogrammer import retry_guard
        real_digest = retry_guard._digest
        calls = []
        def digest(cwd):
            calls.append(1)
            if len(calls) == 3:
                raise RuntimeError('synthetic end observation failure')
            return real_digest(cwd)
        with patch.object(retry_guard, '_digest', side_effect=digest):
            with self.assertRaisesRegex(RuntimeError, 'synthetic end'):
                self.call()
        self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')
        self.assertEqual(self.call()['reason'], 'retry_attempt_incomplete')
        self.assertEqual(self.count.read_text(), '1')

    def test_start_record_write_failure_prevents_execution(self):
        from coprogrammer import manager_store
        replace = manager_store._replace_event_log
        def fail_run_record(source, target):
            if target == self.run_log:
                raise OSError('synthetic record I/O failure')
            return replace(source, target)
        with patch.object(manager_store, '_replace_event_log', side_effect=fail_run_record):
            with self.assertRaisesRegex(RuntimeError, 'cannot commit'):
                self.call()
        self.assertFalse(self.count.exists())
        self.assertFalse(self.run_log.exists())
        self.assertEqual(self.call()['reason'], 'retry_baseline_missing')

    def test_end_record_write_failure_keeps_durable_incomplete_marker(self):
        from coprogrammer import manager_store
        replace = manager_store._replace_event_log
        writes = []
        def fail_end_record(source, target):
            if target == self.run_log:
                writes.append(1)
                if len(writes) == 2:
                    raise OSError('synthetic end record I/O failure')
            return replace(source, target)
        with patch.object(manager_store, '_replace_event_log', side_effect=fail_end_record):
            with self.assertRaisesRegex(RuntimeError, 'cannot commit'):
                self.call()
        self.assertEqual(load_events(self.run_log)[-1]['type'], 'retry.started')
        self.assertEqual(self.call()['reason'], 'retry_attempt_incomplete')
        self.assertEqual(self.count.read_text(), '1')

    def test_unignored_run_state_is_refused_before_execution(self):
        (self.repo / '.gitignore').write_text('__pycache__/\n')
        self.git('add', '.gitignore')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-m', 'synthetic state exclusion removed')
        # The worker guard normally rejects unignored state as out of scope;
        # bypass only that file enumeration to exercise the retry-state check.
        sc.release(self.path, self.repo, 'codex', 'api',
                   sc.claim(self.path, self.repo, 'codex', 'api')['claim_id'], 'Synthetic reset')
        with patch('coprogrammer.worker.working_files', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'Git-ignored'):
                self.call()
        self.assertFalse(self.count.exists())

    def test_cli_option_is_task_only_and_preview_does_not_execute(self):
        # Use the real CLI in a fresh process; no native client is involved.
        env = {**os.environ, 'PYTHONPATH': str(Path(runner.__file__).parents[1])}
        prefix = [sys.executable, '-m', 'coprogrammer', 'worker', 'run', '--session', 'codex']
        preview = subprocess.run(prefix + ['--protect-retry', '--', *self.command()], cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(json.loads(preview.stdout)['applied'])
        self.assertFalse(self.count.exists())
        invocation = prefix + ['--apply', '--protect-retry', '--', *self.command()]
        first = subprocess.run(invocation, cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(first.returncode, 1)
        self.assertEqual(json.loads(first.stdout)['reason'], 'command_failed')
        self.content.write_text('newer-user-result')
        second = subprocess.run(invocation, cwd=self.repo, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(second.returncode, 1)
        self.assertEqual(json.loads(second.stdout)['reason'], 'retry_content_changed')
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'newer-user-result')
        with self.assertRaisesRegex(RuntimeError, 'task-only'):
            self.call(handle_inbox=True)
        with self.assertRaisesRegex(RuntimeError, 'boolean'):
            runner.run(self.path, self.repo, 'codex', self.command(), protect_retry=1)

    def test_cancelled_attempt_cannot_silently_rebaseline(self):
        if os.name != 'posix':
            self.skipTest('POSIX SIGINT process fixture')
        code = '''import json,sys
from pathlib import Path
from coprogrammer import runner
try:
 runner.run(Path(sys.argv[1]),Path(sys.argv[2]),'codex',json.loads(sys.argv[3]),apply=True,protect_retry=True,timeout=20)
except runner.RunInterrupted:
 sys.exit(130)
'''
        process = subprocess.Popen([sys.executable, '-c', code, str(self.path), str(self.repo), json.dumps(self.command('wait'))],
                                   env={**os.environ, 'PYTHONPATH': str(Path(runner.__file__).parents[1])},
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not self.marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(self.marker.exists())
            process.send_signal(signal.SIGINT)
            self.assertEqual(process.wait(timeout=10), 130)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=10)
        child = Path('/proc') / self.marker.read_text() / 'stat'
        self.assertTrue(not child.exists() or child.read_text().split()[2] == 'Z')
        self.content.write_text('newer-user-result')
        self.assertEqual(self.call()['reason'], 'retry_attempt_incomplete')
        self.assertEqual(self.count.read_text(), '1')
        self.assertEqual(self.content.read_text(), 'newer-user-result')
