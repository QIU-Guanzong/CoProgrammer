"""Offline native transport fixtures; no account/model is invoked."""
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

from coprogrammer import claude_harness as adapter, collaboration as co, runner, scheduler, worker
from test_workspace_workflow import Fixture


def envelope(status="done", **extra):
    return {"type": "result", "subtype": "success", "is_error": False,
            "structured_output": {"status": status, "summary": "Offline result"}, **extra}


class PortableClaudeHarnessTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "claude", "claude", "task")
        scheduler.create(self.path, self.repo, "claude", "docs", "Task", ["src/**"])
        self.packet = {"format": "coprogrammer.harness-task.v1", "kind": "task", "session": "claude",
                       "task": worker.step(self.path, self.repo, "claude", apply=True)["task"],
                       "workspace": co.workspace(self.repo)}

    def invoke(self, raw, returncode=0, access="read-only"):
        calls = []
        def native(argv, **options):
            calls.append(argv)
            self.assertEqual(argv[0], "trusted-claude.exe")
            self.assertEqual(argv[1:5], ["-p", "--input-format", "text", "--output-format"])
            self.assertEqual(argv[argv.index("--output-format") + 1], "json")
            self.assertEqual(argv[argv.index("--tools") + 1], adapter.ACCESS_TOOLS[access])
            self.assertEqual(json.loads(argv[argv.index("--mcp-config") + 1]), {"mcpServers": {}})
            self.assertIn("--strict-mcp-config", argv)
            self.assertIn("--no-session-persistence", argv)
            self.assertNotIn("--allowedTools", argv)
            self.assertNotIn("--permission-mode", argv)
            self.assertNotIn("--model", argv)
            self.assertFalse(json.loads(argv[argv.index("--json-schema") + 1])["additionalProperties"])
            self.assertFalse("shell" in options, "Native argv must not use a shell")
            self.assertFalse("env" in options, "Native environment must remain inherited")
            self.assertFalse("start_new_session" in options, "Native client must inherit the runner process group")
            self.assertEqual(options["stderr"], subprocess.DEVNULL)
            self.assertIsInstance(options["input"], bytes)
            options["stdout"].write(raw)
            return subprocess.CompletedProcess(argv, returncode)
        with patch.object(co, "workspace", return_value=self.packet["workspace"]), \
                patch.object(adapter.subprocess, "run", side_effect=native):
            try:
                return adapter.execute(self.packet, "trusted-claude.exe", access)
            finally:
                self.assertEqual(len(calls), 1)

    def test_done_blocked_and_sensitive_outer_metadata(self):
        for status in ("done", "blocked"):
            raw = json.dumps(envelope(status, session_id="PRIVATE_SESSION", result="PRIVATE_TEXT",
                                      usage={"secret": "PRIVATE_METADATA"})).encode()
            result = self.invoke(raw)
            self.assertEqual(result["status"], status)
            self.assertEqual(set(result), {"status", "summary"})
            self.assertNotIn("PRIVATE", json.dumps(result))

    def test_null_optional_permission_denials_and_errors_preserve_success(self):
        result = self.invoke(json.dumps(envelope(permission_denials=None, errors=None)).encode())
        self.assertEqual(result, {"status": "done", "summary": "Offline result"})

    def test_explicit_write_tools_and_denials(self):
        self.assertEqual(self.invoke(json.dumps(envelope()).encode(), access="workspace-write")["status"], "done")
        result = self.invoke(json.dumps(envelope(permission_denials=[{"input": "PRIVATE_TOOL"}])).encode())
        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_native_failure_never_accepts_plausible_result(self):
        with self.assertRaisesRegex(RuntimeError, "Claude CLI failed"):
            self.invoke(json.dumps(envelope()).encode(), returncode=7)

    def test_invalid_envelopes_and_structured_results(self):
        invalid = [[], {}, envelope(is_error=True), envelope(is_error=0), envelope(type="assistant"),
                   envelope(subtype="error_max_turns"), envelope(structured_output=None),
                   envelope(structured_output={"status": "done", "summary": ""}),
                   envelope(structured_output={"status": "done", "summary": "x", "extra": 1}),
                   envelope(structured_output={"status": "received", "summary": "x"}),
                   envelope(structured_output={"status": "done", "summary": "x" * 16001}),
                   envelope(permission_denials="PRIVATE"), envelope(errors=["PRIVATE"])]
        for value in invalid:
            with self.subTest(value=type(value).__name__), self.assertRaisesRegex(RuntimeError, "invalid structured"):
                self.invoke(json.dumps(value).encode())

    def test_duplicate_nonfinite_utf8_trailing_and_oversized_output(self):
        invalid = [b'\xff', b'{} extra', b'x' * 128001,
                   b'{"type":"result","type":"result"}',
                   json.dumps(envelope(extra=float("nan"))).encode()]
        for raw in invalid:
            with self.subTest(length=len(raw)), self.assertRaises(RuntimeError):
                self.invoke(raw)

    def test_invalid_packet_inbox_or_worktree_does_not_launch(self):
        values = [{}, [], {"format": "coprogrammer.harness-task.v1", "kind": "inbox"},
                  {**self.packet, "task": {}}, {**self.packet, "workspace": {}},
                  {**self.packet, "task": {**self.packet["task"], "patterns": ["../escape"]}}]
        with patch.object(co, "workspace", return_value=self.packet["workspace"]), \
                patch.object(adapter.subprocess, "run") as native:
            for packet in values:
                with self.subTest(packet=type(packet).__name__), self.assertRaises(RuntimeError):
                    adapter.execute(packet, "claude")
            self.assertEqual(native.call_count, 0, "Invalid packets must not invoke the native client")

    def test_discovery_and_cli_modes_never_read_task_or_launch(self):
        with patch.object(adapter.shutil, "which", return_value="/trusted/claude"), \
                patch.object(adapter.subprocess, "run") as native, patch.object(adapter.sys, "stdin") as stdin:
            self.assertEqual(adapter.check("claude")["executable"]["status"], "available")
            with patch.object(sys, "argv", ["claude-harness", "--check"]), patch.object(sys, "stdout", io.StringIO()):
                self.assertEqual(adapter.main(), 0)
            for argv in ([], ["--check", "--execute"], ["--access", "workspace-write"]):
                with patch.object(sys, "argv", ["claude-harness", *argv]), patch.object(sys, "stderr", io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        adapter.main()
                    self.assertEqual(error.exception.code, 2)
            self.assertEqual(native.call_count, 0, "Discovery must not invoke the native client")
            stdin.buffer.read.assert_not_called()

    def test_missing_client_discovery_and_execution(self):
        with patch.object(adapter.shutil, "which", return_value=None):
            self.assertEqual(adapter.check("absent")["executable"]["status"], "unavailable")
        with patch.object(co, "workspace", return_value=self.packet["workspace"]), \
                patch.object(adapter.subprocess, "run", side_effect=FileNotFoundError("PRIVATE")):
            with self.assertRaisesRegex(RuntimeError, "structured result unavailable"):
                adapter.execute(self.packet, "absent")


CLAUDE_PROBE_HELP = """Usage: claude [options] [command] [prompt]
Options:
  --json-schema <schema>
  --tools <tools>
  --output-format <format>
  --strict-mcp-config
  --mcp-config <config>
  --disallowedTools <tools>
  --no-session-persistence
  --max-turns <turns>
"""


class PortableClaudeNativeProbeTests(unittest.TestCase):
    def invoke(self, auth_text='{"loggedIn":true}', auth_exit=0, *,
               version_text="2.1.299 (Claude Code)\n", help_text=CLAUDE_PROBE_HELP,
               found="/trusted/claude.exe", arguments=None, interrupt_at=None):
        from coprogrammer import manager_store

        calls = []
        replies = [(0, version_text), (0, help_text), (auth_exit, auth_text)]

        def probe(argv, **options):
            index = len(calls)
            calls.append(argv)
            self.assertEqual(argv, [[found, "--version"], [found, "--help"],
                                    [found, "auth", "status"]][index])
            self.assertEqual(set(options), {"accepted_exit_codes"} if index == 2 else set())
            if index == 2:
                self.assertEqual(options["accepted_exit_codes"], (0, 1))
            if index == interrupt_at:
                raise KeyboardInterrupt("PRIVATE_INTERRUPT")
            code, text = replies[index]
            return {"status": "sampled" if text is not None else "failed", "exit_code": code}, text

        out, err = io.StringIO(), io.StringIO()
        args = ["--check", "--probe-native"] if arguments is None else arguments
        with patch.object(adapter.shutil, "which", return_value=found), \
                patch.object(adapter, "_probe_command", side_effect=probe), \
                patch.object(adapter, "execute", side_effect=AssertionError("Probe cannot execute a task")) as execute, \
                patch.object(adapter.subprocess, "run", side_effect=AssertionError("Probe helper must stay mocked")) as run, \
                patch.object(adapter.subprocess, "Popen", side_effect=AssertionError("Probe helper must stay mocked")) as launch, \
                patch.object(manager_store, "transaction", side_effect=AssertionError("Probe cannot change Manager")) as manager, \
                patch.object(manager_store, "load_events", side_effect=AssertionError("Probe cannot read Manager")) as events, \
                patch.object(co, "workspace", side_effect=AssertionError("Probe cannot read workspace")) as workspace, \
                patch.object(sys, "argv", ["claude-harness", *args]), \
                patch.object(sys, "stdin") as stdin, \
                patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            stdin.buffer.read.side_effect = AssertionError("Probe cannot read a task packet")
            try:
                code = adapter.main()
            except SystemExit as error:
                code = error.code
            for mocked in (execute, run, launch, manager, events, workspace, stdin.buffer.read):
                self.assertEqual(mocked.call_count, 0, "Local probe must use only its declared helper calls")
        report = json.loads(out.getvalue()) if out.getvalue() else None
        return code, report, calls, err.getvalue()

    def test_plain_check_reads_no_task_manager_or_native_status(self):
        code, report, calls, errors = self.invoke(arguments=["--check"])
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(errors, "")
        self.assertEqual(report["native_probe"]["status"], "not_requested")
        self.assertEqual(report["native_configuration"], "not_checked")
        self.assertEqual(report["model_connection"], "not_checked")
        self.assertFalse(report["network_used"])

    def test_local_ready_filters_sensitive_extra_account_fields(self):
        account = {"loggedIn": True, "email": "PRIVATE_EMAIL", "orgId": "PRIVATE_ORG",
                   "apiKey": "PRIVATE_KEY", "account": {"details": "PRIVATE_ACCOUNT"}}
        code, report, calls, errors = self.invoke(json.dumps(account), 0)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(errors, "")
        self.assertEqual(report["native_version"], "2.1.299")
        self.assertEqual(report["native_probe"]["status"], "local_ready")
        self.assertEqual(report["native_probe"]["auth"]["authorization"], "logged_in")
        self.assertEqual(report["native_probe"]["auth"]["exit_code"], 0)
        self.assertFalse(report["native_probe"]["model_request_submitted"])
        self.assertEqual(report["model_connection"], "not_checked")
        public = json.dumps(report)
        self.assertNotIn("PRIVATE", public)
        for field in ("email", "orgId", "apiKey", "account"):
            self.assertFalse(field in report["native_probe"]["auth"], "Account metadata must be discarded")

    def test_exit_one_logged_out_is_readable_but_not_ready(self):
        code, report, calls, errors = self.invoke('{"loggedIn":false,"account":"PRIVATE_ACCOUNT"}', 1)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(errors, "")
        self.assertEqual(report["native_probe"]["status"], "not_ready")
        self.assertEqual(report["native_probe"]["auth"]["status"], "reported")
        self.assertEqual(report["native_probe"]["auth"]["authorization"], "logged_out")
        self.assertEqual(report["native_probe"]["auth"]["exit_code"], 1)
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_invalid_duplicate_inconsistent_and_unknown_auth_fail_closed(self):
        cases = [(0, "PRIVATE_INVALID_JSON"), (1, "PRIVATE_INVALID_JSON"),
                 (0, '{"loggedIn":true,"loggedIn":false,"account":"PRIVATE"}'),
                 (1, '{"loggedIn":false,"loggedIn":false,"account":"PRIVATE"}'),
                 (0, '{"loggedIn":false}'), (1, '{"loggedIn":true}'),
                 (0, '{}'), (1, '{}'), (0, '[]'), (1, 'null'),
                 (0, '{"loggedIn":1}'), (1, '{"loggedIn":0}'),
                 (0, '{"loggedIn":"true"}'), (1, '{"loggedIn":null}'),
                 (0, '{"loggedIn":true,"account":NaN}'),
                 (1, '{"loggedIn":false,"account":Infinity}'),
                 (0, '{"loggedIn":true} PRIVATE_TRAILING'), (1, None)]
        for index, (exit_code, raw) in enumerate(cases):
            with self.subTest(case=index, exit_code=exit_code):
                code, report, calls, errors = self.invoke(raw, exit_code)
                self.assertEqual(code, 1)
                self.assertEqual(len(calls), 3)
                self.assertEqual(errors, "")
                self.assertEqual(report["native_probe"]["status"], "not_ready")
                self.assertEqual(report["native_probe"]["auth"]["authorization"], "unknown")
                self.assertNotIn("PRIVATE", json.dumps(report))

    def test_unrecognized_version_or_missing_help_flags_cannot_be_ready(self):
        cases = [("PRIVATE_VERSION_BANNER", CLAUDE_PROBE_HELP),
                 ("999.0.0 (Claude Code)\n", CLAUDE_PROBE_HELP.replace("  --json-schema <schema>\n", ""))]
        for index, (version, help_text) in enumerate(cases):
            with self.subTest(case=index):
                code, report, calls, errors = self.invoke(version_text=version, help_text=help_text)
                self.assertEqual(code, 1)
                self.assertEqual(len(calls), 3)
                self.assertEqual(errors, "")
                self.assertEqual(report["native_probe"]["status"], "not_ready")
                self.assertNotIn("PRIVATE", json.dumps(report))

    def test_missing_selected_path_never_probes(self):
        code, report, calls, errors = self.invoke(found=None)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        self.assertEqual(errors, "")
        self.assertEqual(report["native_probe"]["status"], "unavailable")

    def test_probe_flag_requires_check_before_any_native_call(self):
        for args in (["--probe-native"], ["--execute", "--probe-native"],
                     ["--check", "--execute", "--probe-native"]):
            with self.subTest(arguments=args):
                code, report, calls, errors = self.invoke(arguments=args)
                self.assertEqual(code, 2)
                self.assertIsNone(report)
                self.assertEqual(calls, [])
                self.assertNotIn("PRIVATE", errors)

    def test_interrupt_at_each_stage_returns_130_without_later_calls_or_private_text(self):
        for index in range(3):
            with self.subTest(stage=index):
                code, report, calls, errors = self.invoke(interrupt_at=index)
                self.assertEqual(code, 130)
                self.assertIsNone(report)
                self.assertEqual(len(calls), index + 1)
                self.assertIn("interrupted", errors)
                self.assertNotIn("PRIVATE", errors)


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux synthetic local probe; no native model client")
class ClaudeProbeHelperProcessTests(unittest.TestCase):
    def test_exit_one_stdout_is_sampled_only_with_explicit_accepted_code(self):
        argv = [sys.executable, "-c",
                'import json,sys;print(json.dumps({"loggedIn":False}));'
                'print("PRIVATE_STDERR",file=sys.stderr);raise SystemExit(1)']
        result, text = adapter._probe_command(argv, accepted_exit_codes=(0, 1))
        self.assertEqual(result, {"status": "sampled", "exit_code": 1})
        self.assertEqual(json.loads(text), {"loggedIn": False})
        result, text = adapter._probe_command(argv)
        self.assertEqual(result, {"status": "failed", "exit_code": 1, "reason": "command_failed"})
        self.assertIsNone(text)


@unittest.skipUnless(os.name == "posix", "POSIX executable/shebang fixture; no real model")
class ClaudeNativeProcessTests(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "claude", "claude", "task")
        scheduler.create(self.path, self.repo, "claude", "docs", "Offline task", ["src/**"])
        self.native = self.root / "fake-claude"
        self.native.write_text("#!" + sys.executable + "\n" + '''import json,pathlib,sys
prompt=sys.stdin.buffer.read().decode()
assert 'claimed' in prompt
assert '--strict-mcp-config' in sys.argv
assert sys.argv[sys.argv.index('--tools')+1]=='Read,Glob,Grep,Edit,Write'
pathlib.Path('src/main.py').write_text('VALUE = 2\\n')
print(json.dumps({'type':'result','subtype':'success','is_error':False,'structured_output':{'status':'done','summary':'Offline fixture'},'session_id':'PRIVATE_NATIVE'}))
print('PRIVATE_STDERR',file=sys.stderr)
''')
        self.native.chmod(0o755)
        self.argv = [sys.executable, "-m", "coprogrammer.claude_harness", "--execute", "--executable",
                     str(self.native), "--access", "workspace-write"]
        env = patch.dict(os.environ, {"PYTHONPATH": str(Path(adapter.__file__).resolve().parents[1])})
        env.start()
        self.addCleanup(env.stop)

    def test_preview_then_one_real_synthetic_process_completion(self):
        before = self.path.read_bytes()
        report = runner.run(self.path, self.repo, "claude", self.argv)
        self.assertFalse(report["applied"])
        self.assertEqual(self.path.read_bytes(), before)
        report = runner.run(self.path, self.repo, "claude", self.argv, apply=True)
        self.assertEqual(report["state"], "done")
        self.assertEqual((self.repo / "src/main.py").read_text(), "VALUE = 2\n")
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_error_envelope_retains_claim_and_partial_edits(self):
        self.native.write_text("#!" + sys.executable + "\n" + '''import json,pathlib
pathlib.Path('src/main.py').write_text('VALUE = 3\\n')
print(json.dumps({'type':'result','subtype':'success','is_error':True,'structured_output':{'status':'done','summary':'PRIVATE'}}))
''')
        report = runner.run(self.path, self.repo, "claude", self.argv, apply=True)
        self.assertEqual(report["reason"], "command_failed")
        self.assertTrue(report["claim_retained"])
        self.assertEqual((self.repo / "src/main.py").read_text(), "VALUE = 3\n")
        self.assertNotIn("PRIVATE", json.dumps(report))

    @staticmethod
    def _fixture_alive(pid):
        try:
            state = (Path("/proc") / str(pid) / "stat").read_text()
        except FileNotFoundError:
            return False
        return state.rsplit(")", 1)[1].split()[0] not in ("Z", "X")

    def _cleanup_case(self, interrupt):
        from coprogrammer.manager_store import load_events

        marker = self.root / "claude-native-pids.json"
        self.native.write_text("#!" + sys.executable + "\n" + '''import json,os,pathlib,subprocess,sys,time
prompt=sys.stdin.buffer.read().decode('utf-8')
packet=json.loads(prompt.splitlines()[-1])
assert packet['kind']=='task' and packet['task']['status']=='claimed'
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
pathlib.Path('src/main.py').write_text('VALUE = 4\\n')
marker=pathlib.Path(''' + repr(str(marker)) + ''')
temporary=marker.with_suffix('.tmp')
temporary.write_text(json.dumps([os.getpid(),child.pid]))
temporary.replace(marker)
print('PRIVATE_NATIVE_OUTPUT',flush=True)
print('PRIVATE_NATIVE_ERROR',file=sys.stderr,flush=True)
time.sleep(60)
''', encoding="utf-8")
        timeout = "20" if interrupt else "2"
        parent = subprocess.Popen(
            [sys.executable, "-m", "coprogrammer", "worker", "run", "--cwd", str(self.repo),
             "--session", "claude", "--apply", "--timeout-seconds", timeout, "--", *self.argv],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = []
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), "Offline Claude fixture did not start")
            pids = json.loads(marker.read_text())
            if interrupt:
                parent.send_signal(signal.SIGINT)
            output, errors = parent.communicate(timeout=15)
            self.assertEqual(parent.returncode, 130 if interrupt else 1)
            self.assertEqual(errors, b"")
            report = json.loads(output)
            self.assertEqual(report["reason"], "interrupted" if interrupt else "timeout")
            self.assertTrue(report["launched"])
            self.assertTrue(report["claim_retained"])
            self.assertIsNone(report["exit_code"])
            self.assertNotIn(b"PRIVATE", output)
            if interrupt:
                self.assertEqual(report["interruption_phase"], "running")
                self.assertEqual(report["completion_status"], "not_attempted")
                self.assertEqual(report["cleanup_status"], "confirmed")
            deadline = time.monotonic() + 2
            while any(self._fixture_alive(pid) for pid in pids) and time.monotonic() < deadline:
                time.sleep(.02)
            for pid in pids:
                self.assertFalse(self._fixture_alive(pid), f"Live offline Claude fixture process {pid}")
            self.assertEqual((self.repo / "src/main.py").read_text(), "VALUE = 4\n")
            events = load_events(self.path)
            self.assertEqual(sum(event["type"] == "task.claimed" for event in events), 1)
            self.assertFalse(any(event["type"] in ("task.finished", "message.acknowledged", "lease.released")
                                 for event in events))
            task = next(task for task in scheduler.board(events)["tasks"] if task["id"] == "docs")
            self.assertEqual(task["status"], "claimed")
            self.assertEqual(task["session"], "claude")
        finally:
            if parent.poll() is None:
                parent.send_signal(signal.SIGINT)
                try:
                    parent.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    parent.kill()
                    parent.communicate(timeout=5)
            # Failure cleanup stays limited to PIDs written by this synthetic
            # executable. Never inspect or stop an unrelated native client.
            for pid in pids:
                if self._fixture_alive(pid):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc owned descendant observation")
    def test_runner_timeout_stops_native_child_and_grandchild_and_retains_claim_edits(self):
        self._cleanup_case(False)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux SIGINT owned descendant observation")
    def test_runner_sigint_stops_native_child_and_grandchild_and_retains_claim_edits(self):
        self._cleanup_case(True)


if __name__ == "__main__":
    unittest.main()
