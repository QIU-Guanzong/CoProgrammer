"""Offline process tests; no model/account is used."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from coprogrammer import codex_harness, collaboration as co, runner, scheduler
from test_workspace_workflow import Fixture

@unittest.skipUnless(os.name == "posix", "POSIX executable/shebang process fixture")
class CodexHarnessTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path,self.repo,'codex','codex','upgrade')
        scheduler.create(self.path,self.repo,'codex','api','中文任务',['src/**'])
        self.native=self.root/'fake-codex'
        self.native.write_text('#!'+sys.executable+'\n'+'''import sys,json,pathlib
args=sys.argv[1:]; prompt=sys.stdin.buffer.read().decode('utf-8')
assert args[0]=='exec' and '--ephemeral' in args and '中文任务' in prompt
assert args[args.index('--sandbox')+1]=='workspace-write'
schema=json.loads(pathlib.Path(args[args.index('--output-schema')+1]).read_text())
assert schema['additionalProperties'] is False
pathlib.Path('src/main.py').write_text('VALUE = 2\\n')
pathlib.Path(args[args.index('--output-last-message')+1]).write_text(json.dumps({'status':'done','summary':'离线完成'}))
print('PRIVATE NATIVE OUTPUT',file=sys.stderr)
''',encoding='utf-8')
        self.native.chmod(0o755)
        self.argv=[sys.executable,'-m','coprogrammer.codex_harness','--execute','--executable',str(self.native),'--sandbox','workspace-write']
        env=patch.dict(os.environ,{'PYTHONPATH':str(Path(codex_harness.__file__).parents[1])})
        env.start(); self.addCleanup(env.stop)

    def test_native_process_completion_and_preview(self):
        before=self.path.read_bytes()
        result=runner.run(self.path,self.repo,'codex',self.argv)
        self.assertFalse(result['applied']); self.assertEqual(self.path.read_bytes(),before)
        result=runner.run(self.path,self.repo,'codex',self.argv,apply=True)
        self.assertEqual(result['state'],'done')
        self.assertEqual((self.repo/'src/main.py').read_text(),'VALUE = 2\n')
        self.assertNotIn('PRIVATE NATIVE OUTPUT',json.dumps(result))

    def test_missing_execute_or_executable_keeps_claim(self):
        absent=self.argv.copy(); absent[5]=str(self.root/'absent')
        for argv in ([sys.executable,'-m','coprogrammer.codex_harness'],absent):
            result=runner.run(self.path,self.repo,'codex',argv,apply=True)
            self.assertEqual(result['reason'],'command_failed'); self.assertTrue(result['claim_retained'])

    def test_invalid_and_failed_native_result_keep_claim(self):
        for code in ('raise SystemExit(2)', 'import sys,pathlib; pathlib.Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text("secret invalid result")'):
            self.native.write_text('#!'+sys.executable+'\n'+code+'\n')
            result=runner.run(self.path,self.repo,'codex',self.argv,apply=True)
            self.assertEqual(result['reason'],'command_failed'); self.assertTrue(result['claim_retained'])
            self.assertNotIn('secret',json.dumps(result))

    def test_inbox_refused_before_client_execution(self):
        with patch('coprogrammer.codex_harness.subprocess.run') as process:
            with self.assertRaisesRegex(RuntimeError,'inbox'):
                codex_harness.execute({'format':'coprogrammer.harness-task.v1','kind':'inbox'},'codex','read-only')
            process.assert_not_called()

    def test_empty_oversized_and_malformed_results_keep_claim(self):
        values = ['', 'x'*128001, '{}', '{"status":"done","summary":""}',
                  '{"status":"done","summary":"ok","summary":"duplicate"}',
                  '{"status":"done","summary":NaN}']
        for raw in values:
            with self.subTest(length=len(raw)):
                self.native.write_text('#!'+sys.executable+'\nimport sys,pathlib\npathlib.Path(sys.argv[sys.argv.index("--output-last-message")+1]).write_text('+repr(raw)+')\n')
                result=runner.run(self.path,self.repo,'codex',self.argv,apply=True)
                self.assertEqual(result['reason'],'command_failed')
                self.assertTrue(result['claim_retained'])

    def test_invalid_packets_do_not_launch(self):
        import subprocess
        packets=[{}, [], {'format':'coprogrammer.harness-task.v1','kind':'task','task':{}},
                 {'format':'coprogrammer.harness-task.v1','kind':'task','task':{'patterns':['../escape']}}]
        for packet in packets:
            with patch('coprogrammer.codex_harness.subprocess.run') as process:
                with self.assertRaises(RuntimeError):
                    codex_harness.execute(packet,'codex','read-only')
                process.assert_not_called()
        for raw in (b'{"task":{},"task":{}}',b'{"x":NaN}',b'\xff',b'x'*128001):
            result=subprocess.run([sys.executable,'-m','coprogrammer.codex_harness','--execute'],
                                  input=raw,cwd=self.repo,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stdout,b'')

    def test_default_read_only_and_blocked_reply(self):
        self.native.write_text('#!'+sys.executable+'\n'+'''import sys,json,pathlib
args=sys.argv[1:]
assert args[args.index('--sandbox')+1]=='read-only'
pathlib.Path(args[args.index('--output-last-message')+1]).write_text(json.dumps({'status':'blocked','summary':'Read-only fixture'}))
''')
        result=runner.run(self.path,self.repo,'codex',self.argv[:-2],apply=True)
        self.assertEqual(result['reason'],'harness_blocked')
        self.assertTrue(result['claim_retained'])
        self.assertEqual((self.repo/'src/main.py').read_text(),'VALUE = 1\n')

    def test_wrong_workspace_packet_does_not_launch(self):
        task=scheduler.claim(self.path,self.repo,'codex','api')
        packet={'format':'coprogrammer.harness-task.v1','kind':'task','task':task,
                'session':'codex','workspace':{'worktree':'/wrong','branch':'main','head':'wrong'}}
        with patch('coprogrammer.collaboration.workspace',return_value=co.workspace(self.repo)), patch('coprogrammer.codex_harness.subprocess.run') as process:
            with self.assertRaisesRegex(RuntimeError,'mismatched'):
                codex_harness.execute(packet,'codex','read-only')
            process.assert_not_called()

    def cleanup_case(self, interrupt):
        import signal
        import subprocess
        import time
        if os.name!='posix':
            self.skipTest('POSIX process group test')
        marker=self.root/'native-pids.json'
        self.native.write_text('#!'+sys.executable+'\n'+'''import os,sys,subprocess,time,json,pathlib
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
pathlib.Path('''+repr(str(marker))+''').write_text(json.dumps([os.getpid(),child.pid]))
time.sleep(60)
''')
        code='from pathlib import Path; from coprogrammer import runner; import sys\ntry:\n runner.run(Path(sys.argv[1]),Path(sys.argv[2]),"codex",'+repr(self.argv)+',apply=True,timeout='+('20' if interrupt else '1')+')\nexcept KeyboardInterrupt:\n sys.exit(130)\n'
        parent=subprocess.Popen([sys.executable,'-c',code,str(self.path),str(self.repo)],cwd=self.repo,
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+10
            while not marker.exists() and parent.poll() is None and time.monotonic()<deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(),'native fixture did not start')
            pids=json.loads(marker.read_text())
            if interrupt:
                parent.send_signal(signal.SIGINT)
            parent.wait(timeout=10)
            for pid in pids:
                state=Path('/proc')/str(pid)/'stat'
                self.assertTrue(not state.exists() or state.read_text().split()[2]=='Z',f'live fixture process {pid}')
            from coprogrammer.manager_store import load_events
            self.assertFalse(any(e['type']=='task.finished' for e in load_events(self.path)))
        finally:
            if parent.poll() is None:
                parent.send_signal(signal.SIGINT)
                parent.wait(timeout=10)

    def test_runner_timeout_stops_native_child_and_grandchild(self):
        self.cleanup_case(False)

    def test_runner_sigint_stops_native_child_and_grandchild(self):
        self.cleanup_case(True)

class PortableCodexHarnessTests(Fixture):
    """Platform-neutral argv/result tests; no shebang or shell execution."""
    def setUp(self):
        super().setUp()
        from coprogrammer import worker
        co.register(self.path,self.repo,'codex','codex','upgrade')
        scheduler.create(self.path,self.repo,'codex','api','Task',['src/**'])
        self.packet={'format':'coprogrammer.harness-task.v1','kind':'task',
                     'task':worker.step(self.path,self.repo,'codex',apply=True)['task'],
                     'session':'codex','workspace':co.workspace(self.repo)}

    def invoke(self, reply, returncode=0, sandbox='read-only'):
        import subprocess
        calls=[]
        def native(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(argv[0],'trusted-codex.exe')
            self.assertEqual(argv[1],'exec')
            self.assertEqual(argv[argv.index('--sandbox')+1],sandbox)
            self.assertNotIn('shell',kwargs)
            self.assertNotIn('env',kwargs)
            self.assertNotIn('start_new_session',kwargs)
            self.assertEqual(kwargs['stdout'],subprocess.DEVNULL)
            self.assertEqual(kwargs['stderr'],subprocess.DEVNULL)
            self.assertIsInstance(kwargs['input'],bytes)
            schema=Path(argv[argv.index('--output-schema')+1])
            self.assertFalse(json.loads(schema.read_text())['additionalProperties'])
            Path(argv[argv.index('--output-last-message')+1]).write_bytes(reply)
            return subprocess.CompletedProcess(argv,returncode)
        with patch('coprogrammer.collaboration.workspace',return_value=self.packet['workspace']), \
             patch('coprogrammer.codex_harness.subprocess.run',side_effect=native):
            try:
                return codex_harness.execute(self.packet,'trusted-codex.exe',sandbox)
            finally:
                self.assertEqual(len(calls),1)
                self.assertFalse(Path(calls[0][calls[0].index('--output-schema')+1]).exists())

    def test_read_only_structured_reply(self):
        self.assertEqual(self.invoke(b'{"status":"blocked","summary":"read only"}')['status'],'blocked')

    def test_workspace_write_structured_reply(self):
        self.assertEqual(self.invoke(b'{"status":"done","summary":"done"}',sandbox='workspace-write')['status'],'done')

    def test_failure_invalid_empty_and_oversized_reply(self):
        for raw in (b'',b'x'*128001,b'{}',b'{"status":"done","summary":""}',
                    b'{"status":"done","summary":"x","summary":"y"}',b'{"status":"done","summary":NaN}'):
            with self.subTest(length=len(raw)), self.assertRaises(RuntimeError):
                self.invoke(raw)
        with self.assertRaises(RuntimeError):
            self.invoke(b'{"status":"done","summary":"do not trust failed process"}',returncode=1)

    def test_invalid_packet_refused_before_native_call(self):
        self.packet['task']['patterns']=['../escape']
        calls=[]
        with patch('coprogrammer.collaboration.workspace',return_value=self.packet['workspace']), \
             patch('coprogrammer.codex_harness.subprocess.run',side_effect=lambda *a,**k:calls.append(1)):
            with self.assertRaises(RuntimeError):
                codex_harness.execute(self.packet,'trusted-codex.exe','read-only')
        self.assertEqual(calls,[])


class CodexExecutionDiagnosticsTests(Fixture):
    """Fixed operator evidence, never an actual model call or task receipt."""
    def setUp(self):
        super().setUp()
        from coprogrammer import worker
        co.register(self.path, self.repo, 'codex', 'codex', 'diagnostics')
        scheduler.create(self.path, self.repo, 'codex', 'api', 'PRIVATE_TASK_TITLE', ['src/**'])
        self.packet = {'format': 'coprogrammer.harness-task.v1', 'kind': 'task',
                       'session': 'codex', 'task': worker.step(self.path, self.repo, 'codex', apply=True)['task'],
                       'workspace': co.workspace(self.repo)}

    def execute_observed(self, native):
        snapshots = []
        with patch.object(co, 'workspace', return_value=self.packet['workspace']), \
                patch.object(codex_harness.subprocess, 'run', side_effect=native):
            try:
                result = codex_harness.execute(self.packet, 'trusted-codex.exe', 'read-only', observe=snapshots.append)
                return result, snapshots
            except RuntimeError as error:
                return error, snapshots

    def test_storage_failure_is_fixed_and_proves_no_native_call(self):
        snapshots = []
        with patch.object(co, 'workspace', return_value=self.packet['workspace']), \
                patch.object(codex_harness.tempfile, 'TemporaryDirectory', side_effect=PermissionError('PRIVATE_PATH')), \
                patch.object(codex_harness.subprocess, 'run') as native:
            with self.assertRaisesRegex(RuntimeError, 'local result storage') as caught:
                codex_harness.execute(self.packet, 'trusted-codex.exe', 'read-only', observe=snapshots.append)
            self.assertEqual(native.call_count, 0)
        self.assertNotIn('PRIVATE', str(caught.exception))
        self.assertEqual(snapshots[-1]['phase'], 'result_storage_io_failed')
        self.assertIs(snapshots[-1]['native_process_started'], False)

    def test_missing_result_is_distinct_from_native_unavailability(self):
        import subprocess
        error, snapshots = self.execute_observed(lambda argv, **kw: subprocess.CompletedProcess(argv, 0))
        self.assertIn('without a structured result', str(error))
        self.assertEqual(snapshots[-1]['phase'], 'result_missing')
        self.assertIs(snapshots[-1]['native_process_started'], True)
        self.assertEqual(snapshots[-1]['native_exit'], 0)
        self.assertEqual(snapshots[-1]['model_start'], 'unknown')

    def test_nonzero_exit_has_observed_native_status_without_private_text(self):
        import subprocess
        error, snapshots = self.execute_observed(lambda argv, **kw: subprocess.CompletedProcess(argv, 17))
        self.assertIn('CLI failed', str(error))
        self.assertEqual(snapshots[-1]['phase'], 'native_exit_nonzero')
        self.assertIs(snapshots[-1]['native_process_started'], True)
        self.assertEqual(snapshots[-1]['native_exit'], 17)
        self.assertNotIn('PRIVATE', json.dumps(snapshots))

    def test_run_oserror_does_not_invent_prelaunch_failure(self):
        def failed(*args, **kw):
            raise OSError(5, 'PRIVATE_PROCESS_IO')
        error, snapshots = self.execute_observed(failed)
        self.assertIn('startup is unknown', str(error))
        self.assertEqual(snapshots[-1]['phase'], 'native_launch_or_io_failed')
        self.assertEqual(snapshots[-1]['native_process_started'], 'unknown')
        self.assertIsNone(snapshots[-1]['native_exit'])
        self.assertNotIn('PRIVATE', str(error) + json.dumps(snapshots))

    def test_accepted_result_does_not_copy_summary_into_operator_evidence(self):
        import subprocess
        def native(argv, **kw):
            self.assertEqual(kw['stdout'], subprocess.DEVNULL)
            self.assertEqual(kw['stderr'], subprocess.DEVNULL)
            self.assertFalse('shell' in kw or 'env' in kw or 'start_new_session' in kw)
            Path(argv[argv.index('--output-last-message') + 1]).write_text(json.dumps({'status': 'done', 'summary': 'PRIVATE_MODEL_TEXT'}))
            return subprocess.CompletedProcess(argv, 0)
        result, snapshots = self.execute_observed(native)
        self.assertEqual(result['status'], 'done')
        self.assertEqual(snapshots[-1]['phase'], 'result_accepted')
        self.assertEqual(snapshots[-1]['claim_id'], self.packet['task']['claim_id'])
        self.assertEqual(snapshots[-1]['result_status'], 'done')
        self.assertEqual(snapshots[-1]['model_start'], 'unknown')
        self.assertNotIn('PRIVATE', json.dumps(snapshots))

    def invoke_cli(self, args, native, *, raw=None, read_error=None):
        import contextlib, io
        stdin = unittest.mock.Mock()
        stdin.buffer.read.return_value = json.dumps(self.packet).encode() if raw is None else raw
        stdin.buffer.read.side_effect = read_error
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['codex_harness', *args]), patch.object(sys, 'stdin', stdin), \
                patch.object(co, 'workspace', return_value=self.packet['workspace']), \
                patch.object(codex_harness.subprocess, 'run', side_effect=native), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = codex_harness.main()
            except SystemExit as error:
                code = error.code
        return code, output.getvalue(), errors.getvalue(), stdin

    def test_cli_receipt_is_opt_in_private_and_never_overwrites(self):
        import subprocess
        path = self.root / 'execution.json'
        calls = []
        def native(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 17)
        args = ['--execute', '--diagnostics', str(path), '--executable', 'trusted-codex.exe']
        code, out, errors, _ = self.invoke_cli(args, native)
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        record = json.loads(path.read_text())
        self.assertEqual(record['native_exit'], 17)
        self.assertEqual(record['phase'], 'native_exit_nonzero')
        self.assertNotIn('PRIVATE', path.read_text() + errors)
        if os.name == 'posix':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        before = path.read_bytes()
        code, _, _, stdin = self.invoke_cli(args, native)
        self.assertEqual(code, 2)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(calls), 1)
        self.assertEqual(stdin.buffer.read.call_count, 0)

    def test_diagnostics_cannot_change_check_into_execution(self):
        path = self.root / 'unused.json'
        calls = []
        code, out, _, stdin = self.invoke_cli(['--check', '--diagnostics', str(path)], lambda *a, **kw: calls.append(1))
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertFalse(path.exists())
        self.assertEqual(calls, [])
        self.assertEqual(stdin.buffer.read.call_count, 0)

    def test_parse_failures_save_terminal_stage_without_packet_text(self):
        for index, raw in enumerate((b'PRIVATE_PROMPT', b'\xff',
                                     b'{"secret":"PRIVATE","secret":1}', b'{"x":NaN}')):
            with self.subTest(index=index):
                path = self.root / f'parse-{index}.json'
                calls = []
                code, out, errors, _ = self.invoke_cli(
                    ['--execute', '--diagnostics', str(path)],
                    lambda *a, **kw: calls.append(1), raw=raw)
                self.assertEqual(code, 1)
                self.assertEqual(out, '')
                self.assertEqual(calls, [])
                record = json.loads(path.read_text())
                self.assertEqual(record['phase'], 'packet_parse_failed')
                self.assertIs(record['native_process_started'], False)
                self.assertNotIn('PRIVATE', path.read_text() + errors)

    def test_oversized_input_saves_terminal_stage_without_native(self):
        path = self.root / 'oversized.json'
        calls = []
        code, out, _, stdin = self.invoke_cli(
            ['--execute', '--diagnostics', str(path)], lambda *a, **kw: calls.append(1),
            raw=b'x' * (codex_harness.MAX_RESULT_BYTES + 1))
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertEqual(calls, [])
        stdin.buffer.read.assert_called_once_with(codex_harness.MAX_RESULT_BYTES + 1)
        self.assertEqual(json.loads(path.read_text())['phase'], 'packet_too_large')

    def test_input_io_error_is_fixed_with_or_without_diagnostics(self):
        import errno
        for diagnostics in (False, True):
            with self.subTest(diagnostics=diagnostics):
                path = self.root / 'input-io.json'
                args = ['--execute'] + (['--diagnostics', str(path)] if diagnostics else [])
                calls = []
                code, out, errors, _ = self.invoke_cli(
                    args, lambda *a, **kw: calls.append(1),
                    read_error=OSError(errno.EIO, 'PRIVATE_ERROR', '/PRIVATE_PATH'))
                self.assertEqual(code, 1)
                self.assertEqual(out, '')
                self.assertEqual(calls, [])
                self.assertNotIn('PRIVATE', errors)
                self.assertNotIn('Traceback', errors)
                self.assertIn('Task packet could not be read', errors)
                self.assertEqual(path.exists(), diagnostics)
                if diagnostics:
                    record = json.loads(path.read_text())
                    self.assertEqual(record['phase'], 'packet_read_failed')
                    self.assertEqual(record['os_error'], 'EIO')
                    self.assertIs(record['native_process_started'], False)
                    self.assertNotIn('PRIVATE', path.read_text())

    def test_packet_and_sandbox_rejection_do_not_leave_validating_checkpoint(self):
        for packet, sandbox, phase in (({}, 'read-only', 'packet_rejected'),
                ({'format': 'coprogrammer.harness-task.v1', 'kind': 'inbox'}, 'read-only', 'packet_rejected'),
                (self.packet, 'PRIVATE_SANDBOX', 'sandbox_rejected')):
            snapshots = []
            with self.subTest(phase=phase), patch.object(codex_harness.subprocess, 'run') as native:
                with self.assertRaises(RuntimeError):
                    codex_harness.execute(packet, 'unused', sandbox, observe=snapshots.append)
                native.assert_not_called()
            self.assertEqual(snapshots[-1]['phase'], phase)
            self.assertIs(snapshots[-1]['native_process_started'], False)
            self.assertNotIn('PRIVATE', json.dumps(snapshots))

    def test_process_io_codes_are_allowlisted_and_startup_stays_unknown(self):
        import errno
        for code, expected in ((errno.EACCES, 'EACCES'), (errno.ENOENT, 'ENOENT'),
                               (errno.EPIPE, 'EPIPE'), (987654, 'unknown'), (None, 'unknown')):
            with self.subTest(code=code):
                def native(*a, **kw):
                    raise OSError(code, 'PRIVATE_ERROR', '/PRIVATE_PATH')
                error, snapshots = self.execute_observed(native)
                self.assertIsInstance(error, RuntimeError)
                self.assertEqual(snapshots[-1]['os_error'], expected)
                self.assertEqual(snapshots[-1]['native_process_started'], 'unknown')
                self.assertEqual(snapshots[-1]['model_start'], 'unknown')
                self.assertNotIn('PRIVATE', str(error) + json.dumps(snapshots))

    def test_storage_io_code_retains_prelaunch_state(self):
        import errno
        with patch.object(codex_harness.tempfile, 'TemporaryDirectory',
                          side_effect=OSError(errno.ENOSPC, 'PRIVATE_ERROR', '/PRIVATE_PATH')):
            calls = []
            error, snapshots = self.execute_observed(lambda *a, **kw: calls.append(1))
        self.assertEqual(calls, [])
        self.assertEqual(snapshots[-1]['os_error'], 'ENOSPC')
        self.assertIs(snapshots[-1]['native_process_started'], False)
        self.assertNotIn('PRIVATE', str(error) + json.dumps(snapshots))

    def test_result_read_code_preserves_observed_native_exit(self):
        import errno, subprocess
        original_open = Path.open
        def opened(path, *args, **kwargs):
            if path.name == 'result.json':
                raise OSError(errno.EACCES, 'PRIVATE_ERROR', '/PRIVATE_PATH')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', opened):
            error, snapshots = self.execute_observed(lambda argv, **kw: subprocess.CompletedProcess(argv, 0))
        self.assertEqual(snapshots[-1]['phase'], 'result_unavailable')
        self.assertEqual(snapshots[-1]['os_error'], 'EACCES')
        self.assertIs(snapshots[-1]['native_process_started'], True)
        self.assertEqual(snapshots[-1]['native_exit'], 0)
        self.assertNotIn('PRIVATE', str(error) + json.dumps(snapshots))
