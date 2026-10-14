"""Synthetic local version/help evidence, never a task or model invocation."""
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from coprogrammer import codex_harness, runner

HELP = b"""Execute offline
Usage: codex exec [OPTIONS] [PROMPT]

Options:
      --ephemeral
  -s, --sandbox <MODE>
      --output-schema <FILE>
  -o, --output-last-message <FILE>
  -h, --help
"""


class PortableNativeProbeTests(unittest.TestCase):
    def invoke(self, outputs, codes=(0, 0), arguments=None, cleanup_failure=False):
        calls, processes = [], []
        def launch(argv, **kwargs):
            index = len(calls)
            calls.append(argv)
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
            self.assertEqual(kwargs["start_new_session"], os.name == "posix")
            self.assertNotIn("shell", kwargs)
            self.assertNotIn("env", kwargs)
            kwargs["stdout"].write(outputs[index])
            process = Mock(returncode=codes[index], stdin=None)
            processes.append(process)
            return process
        stdin = Mock()
        stdin.buffer.read.side_effect = AssertionError("Probe cannot read task input")
        output, errors = io.StringIO(), io.StringIO()
        args = arguments or ["--check", "--probe-native"]
        with patch.object(sys, "argv", ["codex_harness", *args]), \
             patch.object(sys, "stdin", stdin), \
             patch("coprogrammer.codex_harness.shutil.which", return_value="/trusted/codex.exe"), \
             patch("coprogrammer.codex_harness.subprocess.Popen", side_effect=launch), \
             patch("coprogrammer.runner._stop", side_effect=OSError("PRIVATE CLEANUP") if cleanup_failure else None) as stop, \
             patch("coprogrammer.codex_harness.execute") as execute, \
             patch("coprogrammer.manager_store.transaction") as manager, \
             patch("coprogrammer.collaboration.workspace") as workspace, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = codex_harness.main()
            stdin.buffer.read.assert_not_called()
            execute.assert_not_called()
            manager.assert_not_called()
            workspace.assert_not_called()
            self.assertEqual(stop.call_count, 4 if cleanup_failure else 2)
        self.assertEqual(calls, [[str(Path('/trusted/codex.exe').absolute()), "--version"],
                                 [str(Path('/trusted/codex.exe').absolute()), "exec", "--help"]])
        for process in processes:
            process.communicate.assert_called_once_with(timeout=5)
        self.assertEqual(errors.getvalue(), "")
        return code, json.loads(output.getvalue())

    def test_explicit_cli_probe_reports_version_and_only_advertised_flags(self):
        code, report = self.invoke((b"codex-cli 0.123.0-alpha.7\n", HELP))
        self.assertEqual(code, 0)
        self.assertEqual(report["native_version"], "0.123.0-alpha.7")
        self.assertEqual(report["native_probe"]["status"], "advertised")
        self.assertEqual(report["native_probe"]["exec_help"]["missing_flags"], [])
        self.assertEqual(report["native_probe"]["exec_help"]["argument_values_and_execution"], "not_checked")
        self.assertEqual(report["native_configuration"], "not_checked")
        self.assertEqual(report["model_connection"], "not_checked")
        self.assertEqual(report["network_used"], "not_checked")

    def test_high_version_cannot_supply_missing_help_flags_or_footer_mentions(self):
        help_text = HELP.replace(b"      --output-schema <FILE>\n", b"")
        for footer in (b"Examples:\n      --output-schema is unsupported\n", b"\n      --output-schema is unsupported\n"):
            with self.subTest(footer=footer):
                code, report = self.invoke((b"codex-cli 999.0.0\n", help_text + footer))
                self.assertEqual(code, 1)
                self.assertEqual(report["native_probe"]["exec_help"]["status"], "missing")
                self.assertEqual(report["native_probe"]["exec_help"]["missing_flags"], ["--output-schema"])
                self.assertNotIn("unsupported", json.dumps(report))

    def test_unrecognized_version_is_not_echoed_or_used_to_infer_flags(self):
        code, report = self.invoke((b"private account/banner data\n", HELP))
        self.assertEqual(code, 1)
        self.assertEqual(report["native_version"], "unknown")
        self.assertEqual(report["native_probe"]["version"]["reason"], "unrecognized_version")
        self.assertEqual(report["native_probe"]["exec_help"]["status"], "advertised")
        self.assertNotIn("private", json.dumps(report))

    def test_empty_invalid_and_oversized_help_have_fixed_failed_or_unknown_evidence(self):
        cases = [(b"", "unrecognized_exec_help"), (b"\xff", "invalid_text"),
                 (b"x" * (codex_harness.MAX_RESULT_BYTES + 1), "reply_too_large"),
                 (HELP.replace(b"codex exec ", b"codex exec-help "), "unrecognized_exec_help"),
                 (b"Usage: codex exec [OPTIONS]\nMention --ephemeral --sandbox --output-schema --output-last-message", "unrecognized_exec_help")]
        for help_text, reason in cases:
            with self.subTest(reason=reason):
                code, report = self.invoke((b"codex-cli 0.123.0\n", help_text))
                self.assertEqual(code, 1)
                self.assertEqual(report["native_probe"]["exec_help"]["reason"], reason)
                self.assertEqual(report["native_probe"]["exec_help"]["exit_code"], 0)

    def test_nonzero_exit_ignores_even_plausible_version_and_help_without_retries(self):
        code, report = self.invoke((b"codex-cli 0.123.0\n", HELP), codes=(7, -15))
        self.assertEqual(code, 1)
        self.assertEqual(report["native_version"], "unknown")
        self.assertEqual(report["native_probe"]["version"]["exit_code"], 7)
        self.assertEqual(report["native_probe"]["exec_help"]["exit_code"], -15)
        self.assertEqual(report["native_probe"]["exec_help"]["reason"], "command_failed")

    def test_successful_sampling_with_cleanup_failure_is_not_advertised(self):
        code, report = self.invoke((b"codex-cli 0.123.0\n", HELP), cleanup_failure=True)
        self.assertEqual(code, 1)
        self.assertEqual(report["native_probe"]["status"], "incomplete")
        self.assertEqual(report["native_probe"]["version"]["reason"], "probe_io_or_cleanup_failed")
        self.assertEqual(report["native_probe"]["exec_help"]["exit_code"], 0)
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_interrupt_with_cleanup_error_has_no_private_context_and_does_not_start_help(self):
        for mode in ("api", "cli"):
            with self.subTest(mode=mode):
                process = Mock(returncode=0, stdin=None)
                process.communicate.side_effect = KeyboardInterrupt("PRIVATE INTERRUPT")
                out, err = io.StringIO(), io.StringIO()
                with patch("coprogrammer.codex_harness.shutil.which", return_value="/trusted/codex.exe"), \
                     patch("coprogrammer.codex_harness.subprocess.Popen", return_value=process) as launch, \
                     patch("coprogrammer.runner._stop", side_effect=OSError("PRIVATE CLEANUP")), \
                     patch.object(sys, "argv", ["codex_harness", "--check", "--probe-native"]), \
                     contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    if mode == "api":
                        with self.assertRaises(KeyboardInterrupt) as caught:
                            codex_harness.check("selected", probe_native=True)
                        self.assertEqual(caught.exception.args, ())
                        self.assertTrue(caught.exception.__suppress_context__)
                    else:
                        self.assertEqual(codex_harness.main(), 130)
                    self.assertEqual(launch.call_count, 1)
                self.assertEqual(out.getvalue(), "")
                self.assertNotIn("PRIVATE", err.getvalue())

    def test_missing_executable_probe_never_launches_and_usage_is_explicit(self):
        for args, expected in [(["--check", "--probe-native"], 1),
                               (["--probe-native"], 2), (["--execute", "--probe-native"], 2)]:
            with self.subTest(args=args), patch.object(sys, "argv", ["codex_harness", *args]), \
                 patch("coprogrammer.codex_harness.shutil.which", return_value=None), \
                 patch("coprogrammer.codex_harness.subprocess.Popen") as process, \
                 patch.object(sys, "stdin", Mock()) as stdin, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = codex_harness.main()
                except SystemExit as error:
                    code = error.code
                self.assertEqual(code, expected)
                process.assert_not_called()
                stdin.buffer.read.assert_not_called()


@unittest.skipUnless(os.name == "posix", "POSIX native executable/shebang fixtures")
class ActualNativeProbeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.native = self.root / "fake-codex"
        self.calls = self.root / "calls.jsonl"

    def write_native(self, body):
        self.native.write_text("#!" + sys.executable + "\n" + body, encoding="utf-8")
        self.native.chmod(0o755)

    def test_real_probe_calls_only_version_and_help_once_without_task_input(self):
        self.write_native("import sys,pathlib,json\nargs=sys.argv[1:]\n"
                          f"with pathlib.Path({str(self.calls)!r}).open('a') as f:f.write(json.dumps(args)+'\\n')\n"
                          "assert sys.stdin.buffer.read()==b''\n"
                          "if args==['--version']:print('codex-cli 0.123.0')\n"
                          f"elif args==['exec','--help']:sys.stdout.buffer.write({HELP!r})\n"
                          "else:raise SystemExit(9)\n"
                          "print('PRIVATE NATIVE STDERR',file=sys.stderr)\n")
        before = signal.getsignal(signal.SIGINT)
        report = codex_harness.check(str(self.native), probe_native=True)
        self.assertEqual(report["native_probe"]["status"], "advertised")
        self.assertEqual([json.loads(line) for line in self.calls.read_text().splitlines()],
                         [["--version"], ["exec", "--help"]])
        self.assertNotIn("PRIVATE NATIVE", json.dumps(report))
        self.assertIs(signal.getsignal(signal.SIGINT), before)

    def test_executable_disappearing_after_discovery_returns_fixed_failure(self):
        with patch("coprogrammer.codex_harness.shutil.which", return_value=str(self.native)):
            report = codex_harness.check("selected-native", probe_native=True)
        self.assertEqual(report["native_probe"]["version"]["reason"], "command_unavailable")
        self.assertEqual(report["native_probe"]["exec_help"]["reason"], "command_unavailable")
        self.assertIsNone(report["native_probe"]["version"]["exit_code"])

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc owned descendant observation")
    def test_timeout_stops_probe_child_and_grandchild_and_keeps_null_original_exit(self):
        marker = self.root / "pids.json"
        self.write_native("import sys,os,json,pathlib,subprocess,time\n"
                          f"if sys.argv[1:]==['exec','--help']:sys.stdout.buffer.write({HELP!r});raise SystemExit\n"
                          "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                          f"pathlib.Path({str(marker)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n"
                          "time.sleep(60)\n")
        pids = []
        try:
            with patch.object(codex_harness, "PROBE_TIMEOUT_SECONDS", 1):
                report = codex_harness.check(str(self.native), probe_native=True)
            pids = json.loads(marker.read_text())
            version = report["native_probe"]["version"]
            self.assertEqual(version["reason"], "timeout")
            self.assertIsNone(version["exit_code"])
            self.assertEqual(report["native_probe"]["exec_help"]["status"], "advertised")
            self.assert_stopped(pids)
        finally:
            self.stop_fixture(pids)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux SIGINT owned descendant observation")
    def test_sigint_stops_owned_probe_tree_before_exit_without_starting_help(self):
        marker = self.root / "pids.json"
        self.write_native("import sys,os,json,pathlib,subprocess,time\n"
                          "assert sys.argv[1:]==['--version']\n"
                          "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                          f"pathlib.Path({str(marker)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n"
                          "time.sleep(60)\n")
        env = dict(os.environ, PYTHONPATH=str(Path(codex_harness.__file__).parents[1]))
        code = "from coprogrammer.codex_harness import check;import sys\ntry:check(sys.argv[1],probe_native=True)\nexcept KeyboardInterrupt:sys.exit(130)\n"
        parent = subprocess.Popen([sys.executable, "-c", code, str(self.native)], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = []
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists())
            pids = json.loads(marker.read_text())
            parent.send_signal(signal.SIGINT)
            output, errors = parent.communicate(timeout=15)
            self.assertEqual(parent.returncode, 130)
            self.assertEqual(output, b"")
            self.assertEqual(errors, b"")
            self.assert_stopped(pids)
        finally:
            if parent.poll() is None:
                parent.kill(); parent.wait(timeout=5)
            self.stop_fixture(pids)

    def assert_stopped(self, pids):
        for pid in pids:
            state = Path('/proc') / str(pid) / 'stat'
            def alive():
                try:
                    return state.read_text().split()[2] != 'Z'
                except FileNotFoundError:
                    return False
            deadline = time.monotonic() + 2
            while alive() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertFalse(alive())

    def stop_fixture(self, pids):
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
