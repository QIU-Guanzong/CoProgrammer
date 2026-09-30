from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import demo


class DemoTest(unittest.TestCase):
    def test_real_worktrees_complete_the_offline_workflow(self):
        report = demo.run_demo()
        self.assertEqual(json.loads(json.dumps(report)), report)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["cleanup"]["temporary_directory_removed"])
        steps = {step["id"]: step for step in report["steps"]}
        self.assertTrue(all(step["status"] == "passed" for step in steps.values()))
        self.assertEqual(steps["worktrees"]["evidence"]["git_worktree_count"], 3)
        self.assertEqual(steps["worktrees"]["evidence"]["branches"], ["demo/codex", "demo/claude"])
        self.assertTrue(steps["worktrees"]["evidence"]["shared_manager_log"])
        self.assertEqual(steps["dependencies"]["evidence"]["blocked_reasons"], ["unfinished_dependencies"])
        self.assertTrue(steps["dependencies"]["evidence"]["event_log_unchanged"])
        self.assertEqual(steps["conflict"]["evidence"]["blocked_reasons"], ["path_lease_conflict"])
        self.assertTrue(steps["guard"]["evidence"]["allowed"])
        self.assertIn("outside task scope", steps["guard"]["evidence"]["rejection"])
        self.assertEqual(steps["handoff"]["evidence"]["pending_after_read"], 1)
        self.assertTrue(steps["handoff"]["evidence"]["duplicate_retry"])
        self.assertEqual(steps["acknowledgement"]["evidence"]["pending_messages"], 0)
        self.assertTrue(steps["unblock"]["evidence"]["downstream_ready"])
        self.assertEqual(report["summary"]["completed_tasks"], 3)
        self.assertEqual(report["summary"]["active_leases"], 0)
        self.assertEqual(report["summary"]["pending_messages"], 0)
        self.assertEqual(report["summary"]["closed_sessions"], 2)

    def test_caller_git_environment_and_configuration_remain_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "gitconfig"
            content = b"[commit]\n\tgpgsign = true\n[user]\n\tname = Unrelated User\n"
            config.write_bytes(content)
            gitdir = root / "unrelated-git-directory"
            gitdir.mkdir()
            marker = gitdir / "marker"
            marker.write_bytes(b"preserve this directory")
            with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_DIR": str(gitdir),
                                        "GIT_WORK_TREE": str(root), "GIT_CONFIG_COUNT": "1",
                                        "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "Inherited"}):
                before = dict(os.environ)
                report = demo.run_demo()
                self.assertEqual(dict(os.environ), before)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(config.read_bytes(), content)
            self.assertEqual(marker.read_bytes(), b"preserve this directory")
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["gitconfig", "unrelated-git-directory"])

    def test_unexpected_scheduler_error_is_not_treated_as_expected_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(demo.sc, "claim", side_effect=RuntimeError("disk failed")):
                with self.assertRaisesRegex(RuntimeError, "disk failed"):
                    demo._run_scenario(Path(temporary).resolve())

    def test_missing_guard_denial_fails_instead_of_reporting_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(demo.sc, "guard", return_value={"allowed": True, "files": ["src/api.py"]}):
                with self.assertRaisesRegex(RuntimeError, "expected rejection.*outside task scope"):
                    demo._run_scenario(Path(temporary).resolve())

    def test_rejected_operation_with_side_effects_fails_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            path.write_text("original", encoding="utf-8")

            def broken():
                path.write_text("changed", encoding="utf-8")
                raise RuntimeError("unfinished dependencies")

            with self.assertRaisesRegex(RuntimeError, "rejected operation changed"):
                demo._denied(path, broken, "unfinished dependencies")

    def test_worker_failure_is_reported_and_temporary_files_are_removed(self):
        observed = []

        def fail(*args, **kwargs):
            root = kwargs["cwd"]
            observed.append(root)
            (root / "partial-result").write_text("partial", encoding="utf-8")
            return subprocess.CompletedProcess(args[0], 1, "", "disk failed")

        with patch.object(demo.subprocess, "run", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "Offline demo failed: disk failed"):
                demo.run_demo()
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists())

    def test_invalid_worker_output_and_timeout_fail_closed(self):
        for result in (subprocess.CompletedProcess([], 0, "not-json", ""),
                       subprocess.CompletedProcess([], 0, '{"status": "failed"}', "")):
            with self.subTest(result=result.stdout), patch.object(demo.subprocess, "run", return_value=result):
                with self.assertRaises(RuntimeError):
                    demo.run_demo()
        with patch.object(demo.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 60)):
            with self.assertRaisesRegex(RuntimeError, "Offline demo could not run"):
                demo.run_demo()


if __name__ == "__main__":
    unittest.main()
