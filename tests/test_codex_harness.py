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
