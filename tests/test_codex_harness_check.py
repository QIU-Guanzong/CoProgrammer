"""First-use diagnostics use only local discovery, never a native/model call."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from coprogrammer import codex_harness


class CodexHarnessCheckTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.marker = self.root / "must-not-launch"
        self.native = self.root / "native-codex.exe"
        self.native.write_text(f"from pathlib import Path; Path({str(self.marker)!r}).touch()\n")
        self.native.chmod(0o755)

    def invoke(self, *args):
        stdin = Mock()
        stdin.buffer.read.side_effect = AssertionError("Check must not read a task")
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["codex_harness", *args]), \
             patch.object(sys, "stdin", stdin), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), \
             patch("coprogrammer.codex_harness.subprocess.run") as process, \
             patch("coprogrammer.codex_harness.tempfile.TemporaryDirectory") as temporary, \
             patch("coprogrammer.collaboration.workspace") as workspace, \
             patch("coprogrammer.manager_store.transaction") as manager:
            try:
                code = codex_harness.main()
            except SystemExit as error:
                code = error.code
            stdin.buffer.read.assert_not_called()
            process.assert_not_called()
            temporary.assert_not_called()
            workspace.assert_not_called()
            manager.assert_not_called()
        self.assertFalse(self.marker.exists())
        return code, output.getvalue(), errors.getvalue()

    def test_explicit_path_and_path_lookup_report_availability_without_launch(self):
        with patch.dict(os.environ, {"PATH": str(self.root)}):
            for selected in (str(self.native), self.native.name):
                with self.subTest(selected=selected):
                    code, raw, errors = self.invoke("--check", "--executable", selected)
                    report = json.loads(raw)
                    self.assertEqual(code, 0)
                    self.assertEqual(errors, "")
                    self.assertEqual(report["executable"]["status"], "available")
                    self.assertEqual(report["executable"]["resolved"], str(self.native))
                    self.assertEqual(report["task_sandbox"], "read-only")
                    self.assertTrue(report["task_supported"])
                    self.assertFalse(report["inbox_supported"])
                    self.assertFalse(report["network_used"])
                    for field in ("native_version", "native_configuration", "model_connection"):
                        self.assertEqual(report[field], "not_checked")

    def test_missing_directory_and_nonexecutable_paths_report_next_step(self):
        cases = [self.root / "missing-codex", self.root]
        if os.name == "posix":
            plain = self.root / "not-executable"
            plain.write_text("Fixture data")
            plain.chmod(0o644)
            cases.append(plain)
        for selected in cases:
            with self.subTest(selected=selected):
                code, raw, _ = self.invoke("--check", "--executable", str(selected))
                report = json.loads(raw)
                self.assertEqual(code, 1)
                self.assertEqual(report["executable"]["status"], "unavailable")
                self.assertIsNone(report["executable"]["resolved"])
                self.assertIn("--executable", report["next_step"])

    def test_default_selection_and_explicit_sandbox_are_diagnostic_only(self):
        with patch("coprogrammer.codex_harness.shutil.which", return_value=str(self.native)) as lookup:
            code, raw, _ = self.invoke("--check", "--sandbox", "workspace-write")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(raw)["task_sandbox"], "workspace-write")
        lookup.assert_called_once_with("codex")

    def test_check_and_execute_are_exclusive_and_execution_remains_explicit(self):
        for args in (("--check", "--execute"), ()):
            with self.subTest(args=args):
                code, output, errors = self.invoke(*args)
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("--execute", errors)
