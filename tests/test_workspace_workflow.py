"""Real Git clones, content changes, command receipts and independent MCP clients."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, evidence, mcp_server, scheduler, workflow, workspace as ws
from test_collaboration_processes import Client


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        (self.repo / ".gitignore").write_text(".coprogrammer/\n__pycache__/\n")
        (self.repo / "src").mkdir()
        (self.repo / "src/main.py").write_text("VALUE = 1\n")
        self.commit()
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.path = cli.event_log_path(self.repo)
        self.receipt = self.repo / ".coprogrammer/checks/test.json"
        self.argv = [sys.executable, "-c", "pass"]

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, capture_output=True,
                              text=True, check=True, timeout=20).stdout.strip()

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "change")

    def write_record(self, record, path=None):
        record["integrity_sha256"] = ws.digest({k: v for k, v in record.items() if k != "integrity_sha256"})
        target = path or self.receipt
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record))

    def session(self, name="codex", client="codex", cwd=None):
        return co.register(self.path, cwd or self.repo, name, client, "upgrade")

    def task(self, task="api", clients=None, deps=None):
        return scheduler.create(self.path, self.repo, "codex", task, "Implement " + task,
                                ["src/**" if task == "api" else f"{task}/**"], deps, clients)


class WorkspaceTests(Fixture):
    def test_staged_unstaged_untracked_ignored_and_content_preserving_commit(self):
        before = ws.snapshot(self.repo)
        (self.repo / "src/main.py").write_text("VALUE = 2\n")
        changed = ws.snapshot(self.repo)
        self.assertNotEqual(before["content"], changed["content"])
        self.git("add", "src/main.py")
        self.assertEqual(changed["content"], ws.snapshot(self.repo)["content"])
        self.commit()
        self.assertEqual(changed["content"], ws.snapshot(self.repo)["content"])
        (self.repo / "新文件.md").write_text("新说明", encoding="utf-8")
        untracked = ws.snapshot(self.repo)
        self.assertIn("新文件.md", untracked["dirty"]["paths"])
        self.commit()
        self.assertEqual(untracked["content"], ws.snapshot(self.repo)["content"])
        (self.repo / ".coprogrammer").mkdir()
        (self.repo / ".coprogrammer/ignored.json").write_text("ignored")
        self.assertEqual(untracked["content"], ws.snapshot(self.repo)["content"])

    def test_deletion_commit_preserves_content_and_rename_tracks_both_paths(self):
        self.git("mv", "src/main.py", "src/new.py")
        self.assertEqual(ws.snapshot(self.repo)["dirty"]["paths"], ["src/main.py", "src/new.py"])
        (self.repo / "src/new.py").unlink()
        before_commit = ws.snapshot(self.repo)["content"]
        self.commit()
        self.assertEqual(before_commit, ws.snapshot(self.repo)["content"])

    def test_inherited_git_redirection_does_not_change_project(self):
        head = self.git("rev-parse", "HEAD")
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing"), "GIT_WORK_TREE": str(self.root)}):
            self.assertEqual(ws.snapshot(self.repo)["head"], head)

    def test_origins_remove_credentials_and_local_paths(self):
        self.assertEqual(ws.origin_identity("https://secret@github.com/org/repo.git?token=secret"), "github.com/org/repo")
        self.assertEqual(ws.origin_identity("git@github.com:org/repo.git"), "github.com/org/repo")
        self.assertIsNone(ws.origin_identity("file:///Users/private/project"))
        self.assertIsNone(ws.origin_identity("C:/private/project"))
        self.git("remote", "add", "origin", "https://secret@github.com/org/repo.git?token=secret")
        self.assertNotIn("secret", json.dumps(ws.snapshot(self.repo)))

    @unittest.skipIf(os.name == "nt", "Windows fixture does not require symlink privileges")
    def test_symlink_target_is_hashed_without_reading_external_file(self):
        outside = self.root / "external"
        outside.write_text("private")
        (self.repo / "link").symlink_to(outside)
        first = ws.snapshot(self.repo)["content"]
        outside.write_text("private changed")
        self.assertEqual(first, ws.snapshot(self.repo)["content"])
        self.assertNotIn("private", json.dumps(ws.snapshot(self.repo)))

    def test_limits_and_invalid_refs_fail_closed(self):
        with patch.object(ws, "MAX_FILE_BYTES", 1):
            with self.assertRaisesRegex(RuntimeError, "byte limit"):
                ws.snapshot(self.repo)
        for ref in ("--help", "HEAD\n", "missing", None):
            with self.subTest(ref=ref), self.assertRaises(RuntimeError):
                ws.snapshot(self.repo, ref)

    def test_gitlink_and_conflicted_index_are_refused(self):
        head = self.git("rev-parse", "HEAD")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},dependency")
        with self.assertRaisesRegex(RuntimeError, "submodules"):
            ws.snapshot(self.repo)
        self.git("update-index", "--force-remove", "dependency")
        row = self.git("ls-files", "--stage", "src/main.py").split("\t")[0].split()
        data = f"0 {'0' * 40}\tsrc/main.py\0" + f"100644 {row[1]} 1\tsrc/main.py\0"
        subprocess.run(["git", "update-index", "-z", "--index-info"], cwd=self.repo,
                       input=data.encode("utf-8"), check=True, capture_output=True)
        with self.assertRaisesRegex(RuntimeError, "conflicts"):
            ws.snapshot(self.repo)

    def test_concurrent_observation_change_is_rejected(self):
        original = ws._content
        calls = []

        def changing(cwd):
            calls.append(None)
            result = original(cwd)
            if len(calls) == 1:
                (self.repo / "src/main.py").write_text("VALUE = 20\n")
            return result

        with patch.object(ws, "_content", changing), self.assertRaisesRegex(RuntimeError, "changed during observation"):
            ws.snapshot(self.repo)

    def test_artifact_reader_rejects_duplicate_nonfinite_and_oversized_json(self):
        path = self.root / "invalid.json"
        for raw in ('{"x": 1, "x": 2}', '{"x": NaN}', '[]', 'invalid'):
            path.write_text(raw)
            with self.assertRaises(RuntimeError):
                ws.read_artifact(path)
        path.write_bytes(b" " * (ws.MAX_ARTIFACT_BYTES + 1))
        with self.assertRaises(RuntimeError):
            ws.read_artifact(path)


class EvidenceTests(Fixture):
    def test_success_reuses_content_after_commit_but_edits_and_command_change_invalidate(self):
        (self.repo / "src/main.py").write_text("VALUE = 2\n")
        evidence.run(self.repo, self.argv, "tests", self.receipt)
        self.assertTrue(evidence.verify(self.repo, self.receipt, self.argv)["fresh"])
        self.commit()
        self.assertTrue(evidence.verify(self.repo, self.receipt, self.argv)["fresh"])
        (self.repo / "README.md").write_text("new documentation")
        self.assertIn("content_changed", evidence.verify(self.repo, self.receipt)["reasons"])
        self.assertIn("command_changed", evidence.verify(self.repo, self.receipt, [sys.executable, "-c", "print(1)"])["reasons"])

    def test_failed_missing_and_timed_out_commands_never_verify_as_fresh(self):
        for argv, timeout in (([sys.executable, "-c", "raise SystemExit(4)"], 10),
                              ([str(self.root / "missing")], 10),
                              ([sys.executable, "-c", "import time; time.sleep(5)"], 1)):
            evidence.run(self.repo, argv, "tests", self.receipt, timeout)
            self.assertIn("check_failed", evidence.verify(self.repo, self.receipt)["reasons"])

    def test_successful_command_that_edits_inputs_is_not_stable(self):
        argv = [sys.executable, "-c", "from pathlib import Path; Path('src/main.py').write_text('changed')"]
        record = evidence.run(self.repo, argv, "tests", self.receipt)
        self.assertEqual(record["exit_code"], 0)
        self.assertFalse(record["stable"])
        self.assertIn("content_changed_during_check", evidence.verify(self.repo, self.receipt)["reasons"])

    def test_record_does_not_contain_argv_output_or_machine_paths(self):
        argv = [sys.executable, "-c", "pass # private-token-value"]
        record = evidence.run(self.repo, argv, "tests", self.receipt)
        raw = json.dumps(record)
        self.assertNotIn("private-token-value", raw)
        self.assertNotIn(str(self.repo), raw)
        self.assertNotIn(sys.executable, raw)

    def test_tampering_expiry_future_and_environment_are_detected(self):
        record = evidence.run(self.repo, self.argv, "tests", self.receipt)
        record["label"] = "forged"
        self.receipt.write_text(json.dumps(record))
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            evidence.verify(self.repo, self.receipt)
        for age, reason in ((-2, "record_from_future"), (90000, "record_expired")):
            timestamp = (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()
            record["started_at"] = record["finished_at"] = timestamp
            self.write_record(record)
            self.assertIn(reason, evidence.verify(self.repo, self.receipt)["reasons"])
        record["started_at"] = record["finished_at"] = datetime.now(timezone.utc).isoformat()
        record["environment"]["platform"] = "other-platform"
        self.write_record(record)
        self.assertIn("environment_changed", evidence.verify(self.repo, self.receipt)["reasons"])

    def test_output_must_be_ignored_or_external_and_cannot_clobber_existing_files(self):
        for output in (self.repo / "tracked.json", self.repo / "src/main.py"):
            with self.assertRaises(RuntimeError):
                evidence.run(self.repo, self.argv, "tests", output)
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text('{"config": true}')
        with self.assertRaisesRegex(RuntimeError, "overwrite"):
            evidence.run(self.repo, self.argv, "tests", self.receipt)
        self.assertEqual(self.receipt.read_text(), '{"config": true}')


class DispatchAndHandoffTests(Fixture):
    def test_dispatch_respects_clients_dependencies_occupancy_and_does_not_mutate(self):
        self.session()
        self.task(clients=["claude"])
        self.task("docs", clients=["codex"])
        self.task("later", deps=["docs"])
        before = self.path.read_bytes()
        report = workflow.dispatch(self.path, self.repo, "codex", limit=1)
        self.assertEqual(report["recommended_task"], "docs")
        self.assertEqual(report["counts"], {"eligible": 1, "excluded": 2})
        self.assertEqual(report["omitted"]["excluded"], 1)
        self.assertEqual(self.path.read_bytes(), before)
        claim = scheduler.claim(self.path, self.repo, "codex", "docs")
        report = workflow.dispatch(self.path, self.repo, "codex")
        self.assertIsNone(report["recommended_task"])
        self.assertIn("session_or_worktree_occupied", report["session_reasons"])
        self.assertNotIn(claim["claim_id"], json.dumps(report))

    def test_dispatch_stale_closed_detached_and_wrong_worktree(self):
        self.session()
        self.task()
        with patch.object(workflow, "datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(seconds=600)
            self.assertIn("session_stale", workflow.dispatch(self.path, self.repo, "codex")["session_reasons"])
        self.git("checkout", "--detach")
        self.assertIn("named_branch_required", workflow.dispatch(self.path, self.repo, "codex")["session_reasons"])
        self.git("checkout", "main")
        worker = self.root / "worker"
        self.git("worktree", "add", "-b", "worker", str(worker))
        self.assertIn("different_worktree", workflow.dispatch(self.path, worker, "codex")["session_reasons"])
        co.pulse(self.path, self.repo, "codex", "closed")
        self.assertIn("session_not_available", workflow.dispatch(self.path, self.repo, "codex")["session_reasons"])

    def test_inherited_git_redirection_cannot_move_manager_or_session(self):
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing"), "GIT_WORK_TREE": str(self.root)}):
            self.assertEqual(cli.event_log_path(self.repo), self.path)
            self.session()
            self.task()
            self.assertEqual(workflow.dispatch(self.path, self.repo, "codex")["recommended_task"], "api")

    def test_claimed_handoff_cannot_substitute_creator_checkout_or_changed_branch(self):
        self.session()
        self.task(clients=["claude"])
        worker = self.root / "worker"
        self.git("worktree", "add", "-b", "worker", str(worker))
        self.session("claude", "claude", worker)
        scheduler.claim(self.path, worker, "claude", "api")
        with self.assertRaisesRegex(RuntimeError, "owner"):
            workflow.handoff(self.path, self.repo, "codex", "api")
        self.git("checkout", "-b", "changed", cwd=worker)
        with self.assertRaisesRegex(RuntimeError, "branch"):
            workflow.handoff(self.path, worker, "claude", "api")

    def test_handoff_version_base_missing_ref_and_source_dirty_are_explicit(self):
        self.session()
        self.task()
        bundle = workflow.handoff(self.path, self.repo, "codex", "api", "origin/main")
        path = self.root / "handoff.json"
        bundle["workspace"]["tool_version"] = "0.2.0a2"
        self.write_record(bundle, path)
        self.assertIn("tool_version_mismatch", workflow.compare(self.repo, path)["reasons"])
        self.assertIn("base_unavailable", workflow.compare(self.repo, path, "missing")["reasons"])
        (self.repo / "new.txt").write_text("new")
        dirty_bundle = workflow.handoff(self.path, self.repo, "codex", "api")
        self.write_record(dirty_bundle, path)
        self.assertIn("source_uncommitted_changes", workflow.compare(self.repo, path)["reasons"])
        self.commit()
        self.write_record(bundle, path)
        self.assertIn("base_mismatch", workflow.compare(self.repo, path, "HEAD")["reasons"])

    def test_cli_records_explicit_argument_vector_and_returns_failed_status(self):
        argv = [sys.executable, "-m", "coprogrammer", "check", "run", "--cwd", str(self.repo),
                "--label", "tests", "--output", str(self.receipt), "--", sys.executable, "-c", "raise SystemExit(3)"]
        result = subprocess.run(argv, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["exit_code"], 3)

    def test_json_and_markdown_artifacts_are_utf8_under_legacy_pipe_encoding(self):
        (self.repo / "新文件.md").write_text("说明", encoding="utf-8")
        self.session()
        scheduler.create(self.path, self.repo, "codex", "api", "更新接口", ["src/**"])
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        for command in (["workspace", "snapshot"],
                        ["manager", "handoff", "--session", "codex", "--task", "api", "--format", "markdown"]):
            result = subprocess.run([sys.executable, "-m", "coprogrammer", *command, "--cwd", str(self.repo)],
                                    env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = result.stdout.decode("utf-8")
            if command[0] == "workspace":
                self.assertIn("新文件.md", json.loads(text)["dirty"]["paths"])
            else:
                self.assertIn("更新接口", text)

    def test_two_clone_handoff_matches_then_detects_drift_and_preserves_ownership(self):
        self.session()
        self.task()
        claim = scheduler.claim(self.path, self.repo, "codex", "api")
        evidence.run(self.repo, self.argv, "tests", self.receipt)
        bundle = workflow.handoff(self.path, self.repo, "codex", "api", "origin/main", [self.receipt])
        raw = json.dumps(bundle)
        self.assertNotIn(claim["claim_id"], raw)
        self.assertNotIn(claim["lease_id"], raw)
        self.assertNotIn(str(self.repo), raw)
        handoff = self.root / "handoff.json"
        handoff.write_text(raw)
        receiver = self.root / "receiver"
        self.git("clone", str(self.repo), str(receiver))
        result = workflow.compare(receiver, handoff)
        self.assertTrue(result["aligned"])
        self.assertTrue(result["ownership_reconciliation_required"])
        self.assertFalse(result["ownership_transferred"])
        self.assertTrue(result["receiver_checks_required"])
        self.assertFalse((receiver / ".coprogrammer/events.jsonl").exists())
        (receiver / "src/main.py").write_text("different")
        self.assertIn("content_mismatch", workflow.compare(receiver, handoff)["reasons"])
        self.assertIn("receiver_uncommitted_changes", workflow.compare(receiver, handoff)["reasons"])

    def test_handoff_unknown_tasks_unrelated_sessions_duplicate_checks_and_tampering(self):
        self.session()
        self.session("other", "claude")
        self.task()
        with self.assertRaisesRegex(RuntimeError, "creator"):
            workflow.handoff(self.path, self.repo, "other", "api")
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            workflow.handoff(self.path, self.repo, "codex", "missing")
        evidence.run(self.repo, self.argv, "tests", self.receipt)
        with self.assertRaisesRegex(RuntimeError, "unique"):
            workflow.handoff(self.path, self.repo, "codex", "api", checks=[self.receipt, self.receipt])
        bundle = workflow.handoff(self.path, self.repo, "codex", "api")
        bundle["task"]["title"] = "tampered"
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            workflow.validate_handoff(bundle)

    def test_cli_and_real_stdio_mcp_read_operations(self):
        self.session()
        self.task()
        evidence.run(self.repo, self.argv, "tests", self.receipt)
        client = Client(self.repo, "codex")
        self.addCleanup(client.close)
        client.initialize()
        snapshot = client.tool("workspace_snapshot", base="origin/main")
        self.assertEqual(snapshot["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(client.tool("task_dispatch", session="codex")["recommended_task"], "api")
        self.assertTrue(client.tool("check_verify", path=str(self.receipt), command=self.argv)["fresh"])
        bundle = client.tool("manager_handoff", session="codex", task_id="api", checks=[str(self.receipt)])
        path = self.root / "handoff.json"
        path.write_text(json.dumps(bundle))
        self.assertTrue(client.tool("handoff_check", path=str(path))["aligned"])
        self.assertIn("No claim", workflow.render_handoff(bundle))
        for name in ("workspace_snapshot", "task_dispatch", "check_verify", "manager_handoff", "handoff_check"):
            self.assertTrue(next(t for t in mcp_server.TOOLS if t["name"] == name)["annotations"]["readOnlyHint"])
        self.assertNotIn("check_run", mcp_server.TOOL_HANDLERS)
        result = subprocess.run([sys.executable, "-m", "coprogrammer", "check", "verify", "--cwd", str(self.repo),
                                 "--artifact", str(self.receipt), "--", *self.argv], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["expected_command_checked"])


if __name__ == "__main__":
    unittest.main()
