from __future__ import annotations

import contextlib
import hashlib
import io
import json
import stat
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coprogrammer import integrations, knowledge, setup
from coprogrammer.cli import main


class ManagedSetupUpgradeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="setup upgrade ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.skill = "coprogrammer-active-sync"
        self.relative = f".agents/skills/{self.skill}/SKILL.md"
        self.original_read = knowledge.read_document

    def changed_catalog(self, *ids):
        def read(name):
            text = self.original_read(name)
            return text + "\nUpdated generated guidance.\n" if name in ids else text
        return patch.object(knowledge, "read_document", side_effect=read)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_recorded_upgrade_requires_explicit_apply_and_preserves_instructions(self):
        setup.apply(self.root, "codex")
        instructions = self.root / "AGENTS.md"
        instructions.write_text("Our project rules", encoding="utf-8")
        before = self.snapshot()
        mtimes = {name: (self.root / name).stat().st_mtime_ns for name in before}
        with self.changed_catalog(f"skills/{self.skill}", "templates/COORDINATION", "templates/AGENTS"):
            normal = setup.preview(self.root, "codex")
            self.assertFalse(normal["can_apply"])
            plan = setup.preview(self.root, "codex", upgrade=True, include_content=True)
            self.assertTrue(plan["can_apply"])
            rows = {row["path"]: row for row in plan["files"]}
            self.assertEqual(rows[self.relative]["status"], "update")
            self.assertTrue(rows[self.relative]["managed"])
            self.assertEqual(rows["AGENTS.md"]["status"], "preserve")
            self.assertNotIn("Our project rules", json.dumps(plan))
            self.assertEqual(before, self.snapshot())
            self.assertEqual(mtimes, {name: (self.root / name).stat().st_mtime_ns for name in before})
            result = setup.apply(self.root, "codex", upgrade=True)
            self.assertTrue(result["applied"])
            self.assertEqual(next(row["status"] for row in result["files"]
                                  if row["path"] == self.relative), "updated")
            self.assertTrue(all(row["status"] in ("unchanged", "preserve")
                                for row in setup.apply(self.root, "codex", upgrade=True)["files"]))
        self.assertEqual(instructions.read_text(), "Our project rules")

    def test_receipt_contains_only_hashes_and_excludes_project_instructions(self):
        result = setup.apply(self.root, "claude")
        receipt = json.loads((self.root / setup.MANIFEST_PATH).read_bytes())
        self.assertEqual(receipt["format"], setup.MANIFEST_FORMAT)
        self.assertNotIn("AGENTS.md", receipt["files"])
        self.assertNotIn("CLAUDE.md", receipt["files"])
        for row in result["files"]:
            if row["kind"] != "instructions":
                self.assertEqual(receipt["files"][row["path"]],
                                 {"kind": row["kind"], "sha256": row["sha256"]})
        self.assertNotIn("content", receipt)

    def test_customized_file_blocks_whole_upgrade_without_leaking_its_content(self):
        setup.apply(self.root, "codex")
        target = self.root / ".codex/config.toml"
        target.write_text("private credential marker", encoding="utf-8")
        before = self.snapshot()
        with self.changed_catalog(f"skills/{self.skill}"):
            result = setup.apply(self.root, "codex", upgrade=True, include_content=True)
        self.assertFalse(result["applied"])
        self.assertEqual(result["conflicts"], [".codex/config.toml"])
        self.assertNotIn("private credential marker", json.dumps(result))
        self.assertEqual(before, self.snapshot())

    def test_old_install_without_receipt_can_adopt_only_identical_files(self):
        setup.apply(self.root, "codex")
        receipt = self.root / setup.MANIFEST_PATH
        receipt.unlink()
        before = self.snapshot()
        with self.changed_catalog(f"skills/{self.skill}"):
            self.assertFalse(setup.apply(self.root, "codex", upgrade=True)["applied"])
        self.assertFalse(receipt.exists())
        self.assertEqual(before, self.snapshot())
        self.assertTrue(setup.apply(self.root, "codex", upgrade=True)["applied"])
        with self.changed_catalog(f"skills/{self.skill}"):
            self.assertTrue(setup.apply(self.root, "codex", upgrade=True)["applied"])

    def test_mcp_refresh_uses_new_interpreter_without_changing_other_servers(self):
        setup.apply(self.root, "claude", edition="mcp")
        original = integrations.sys.executable
        with patch.object(integrations.sys, "executable", original + "-moved"):
            result = setup.apply(self.root, "claude", edition="mcp", upgrade=True)
            self.assertTrue(result["applied"])
            config = json.loads((self.root / ".mcp.json").read_bytes())
            self.assertEqual(config["mcpServers"]["coprogrammer"]["command"], original + "-moved")
        config["mcpServers"]["other"] = {"command": "custom-server"}
        (self.root / ".mcp.json").write_text(json.dumps(config))
        before = self.snapshot()
        self.assertFalse(setup.apply(self.root, "claude", edition="mcp", upgrade=True)["applied"])
        self.assertEqual(before, self.snapshot())

    def test_subset_upgrade_preserves_unselected_and_other_client_ownership(self):
        setup.apply(self.root, "codex")
        setup.apply(self.root, "claude")
        other = "coprogrammer-task-brief"
        with self.changed_catalog(f"skills/{self.skill}", f"skills/{other}"):
            result = setup.apply(self.root, "codex", [self.skill], include_mcp=False, upgrade=True)
            self.assertTrue(result["applied"])
            self.assertEqual((self.root / f".agents/skills/{other}/SKILL.md").read_text(encoding="utf-8"),
                             self.original_read(f"skills/{other}"))
            receipt = json.loads((self.root / setup.MANIFEST_PATH).read_bytes())["files"]
            self.assertIn(f".claude/skills/{self.skill}/SKILL.md", receipt)
            self.assertIn(f".agents/skills/{other}/SKILL.md", receipt)
            # Copilot shares Codex Skills; it can refresh the remaining Skill.
            self.assertTrue(setup.apply(self.root, "copilot", include_mcp=False, upgrade=True)["applied"])
            self.assertTrue(setup.apply(self.root, "claude", upgrade=True)["applied"])

    def test_invalid_receipts_fail_closed_and_are_not_echoed(self):
        setup.apply(self.root, "codex")
        path = self.root / setup.MANIFEST_PATH
        original = json.loads(path.read_bytes())
        invalid = [b"private marker", b"\xff", b"[]", b"{}", b"[" * 1100,
                   b"x" * (setup.MAX_EXISTING_BYTES + 1)]
        for bad_path, bad_entry in (("../outside", {"kind": "mcp", "sha256": "0" * 64}),
                                     (self.relative, {"kind": "instructions", "sha256": "0" * 64}),
                                     (self.relative, {"kind": "skill", "sha256": "bad"})):
            bad = {**original, "files": {bad_path: bad_entry}}
            invalid.append(json.dumps(bad).encode())
        for raw in invalid:
            with self.subTest(length=len(raw)):
                path.write_bytes(raw)
                before = self.snapshot()
                result = setup.apply(self.root, "codex", upgrade=True, include_content=True)
                self.assertFalse(result["applied"])
                self.assertIn(setup.MANIFEST_PATH, result["conflicts"])
                self.assertNotIn("private marker", json.dumps(result))
                self.assertEqual(before, self.snapshot())

    def test_linked_receipt_and_parent_do_not_modify_external_state(self):
        for relative in (setup.MANIFEST_PATH, ".coprogrammer"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as dest:
                root = Path(dest).resolve()
                external = Path(tmp).resolve()
                if relative == setup.MANIFEST_PATH:
                    target = external / "receipt.json"
                    target.write_text("External receipt")
                    (root / ".coprogrammer").mkdir()
                else:
                    target = external
                try:
                    (root / relative).symlink_to(target, target_is_directory=target.is_dir())
                except OSError:
                    self.skipTest("symlink creation unavailable")
                before = {p.name: p.read_bytes() for p in external.iterdir() if p.is_file()}
                result = setup.apply(root, "codex", upgrade=True)
                self.assertFalse(result["applied"])
                self.assertFalse((root / "AGENTS.md").exists())
                self.assertEqual(before, {p.name: p.read_bytes() for p in external.iterdir() if p.is_file()})

    def test_reparse_receipt_is_blocked_without_following_it(self):
        setup.apply(self.root, "codex")
        path = self.root / setup.MANIFEST_PATH
        original = Path.lstat
        def lstat(target, *args, **kwargs):
            if target == path:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return original(target, *args, **kwargs)
        with patch.object(Path, "lstat", lstat):
            result = setup.apply(self.root, "codex", upgrade=True)
        self.assertIn(setup.MANIFEST_PATH, result["conflicts"])

    def test_late_receipt_failure_restores_updates_and_removes_new_files(self):
        setup.apply(self.root, "codex")
        target = self.root / ".codex/config.toml"
        target.unlink()
        before = self.snapshot()
        original = setup._replace
        def replace(root, relative, *args):
            if relative == setup.MANIFEST_PATH:
                raise OSError("simulated receipt replacement failure")
            return original(root, relative, *args)
        with self.changed_catalog(f"skills/{self.skill}", "templates/COORDINATION"), \
                patch.object(setup, "_replace", side_effect=replace), \
                self.assertRaisesRegex(RuntimeError, "rolled back"):
            setup.apply(self.root, "codex", upgrade=True)
        self.assertEqual(before, self.snapshot())

    def test_change_after_plan_is_preserved_and_previous_updates_are_restored(self):
        setup.apply(self.root, "codex")
        before = self.snapshot()
        original = setup._replace
        def replace(root, relative, *args):
            if relative == self.relative:
                (root / relative).write_text("Concurrent edit", encoding="utf-8")
            return original(root, relative, *args)
        with self.changed_catalog(f"skills/{self.skill}", "templates/COORDINATION"), \
                patch.object(setup, "_replace", side_effect=replace), \
                self.assertRaisesRegex(RuntimeError, "rolled back"):
            setup.apply(self.root, "codex", upgrade=True)
        before[self.relative] = b"Concurrent edit"
        self.assertEqual(before, self.snapshot())

    def test_rollback_does_not_erase_concurrent_edit_to_already_updated_file(self):
        setup.apply(self.root, "codex")
        original = setup._replace
        def replace(root, relative, *args):
            if relative == setup.MANIFEST_PATH:
                (root / self.relative).write_text("Concurrent edit", encoding="utf-8")
                raise OSError("simulated failure")
            return original(root, relative, *args)
        with self.changed_catalog(f"skills/{self.skill}"), \
                patch.object(setup, "_replace", side_effect=replace), \
                self.assertRaisesRegex(RuntimeError, "rolled back"):
            setup.apply(self.root, "codex", upgrade=True)
        self.assertEqual((self.root / self.relative).read_text(), "Concurrent edit")

    def test_cooperating_concurrent_upgrades_have_one_consistent_receipt(self):
        setup.apply(self.root, "codex")
        with self.changed_catalog(f"skills/{self.skill}"), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: setup.apply(self.root, "codex", upgrade=True), range(2)))
            self.assertTrue(all(result["applied"] for result in results))
            statuses = [next(row["status"] for row in result["files"]
                             if row["path"] == self.relative) for result in results]
            self.assertCountEqual(statuses, ["updated", "unchanged"])
        receipt = json.loads((self.root / setup.MANIFEST_PATH).read_bytes())["files"]
        for relative, row in receipt.items():
            self.assertEqual(hashlib.sha256((self.root / relative).read_bytes()).hexdigest(), row["sha256"])

    def test_linked_worktrees_keep_independent_setup_receipts_under_shared_lock(self):
        from coprogrammer.cli import event_log_path
        def git(*args):
            result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        git("init")
        git("-c", "user.name=Setup Test", "-c", "user.email=setup@example.invalid",
            "commit", "--allow-empty", "-m", "fixture")
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp).resolve() / "linked"
            git("worktree", "add", "--detach", str(worktree), "HEAD")
            self.assertEqual(event_log_path(self.root), event_log_path(worktree))
            self.assertTrue(setup.apply(self.root, "claude")["applied"])
            self.assertTrue(setup.apply(worktree, "claude")["applied"])
            original = (self.root / setup.MANIFEST_PATH).read_bytes()
            main_config = (self.root / ".mcp.json").read_bytes()
            with patch.object(integrations.sys, "executable", integrations.sys.executable + "-moved"):
                self.assertTrue(setup.apply(worktree, "claude", upgrade=True)["applied"])
            self.assertEqual(original, (self.root / setup.MANIFEST_PATH).read_bytes())
            self.assertEqual(main_config, (self.root / ".mcp.json").read_bytes())
            self.assertNotEqual(main_config, (worktree / ".mcp.json").read_bytes())

    def test_upgrade_cli_is_read_only_until_apply_and_conflicts_return_one(self):
        setup.apply(self.root, "codex")
        def run(*flags):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["setup", "--client", "codex", "--cwd", str(self.root), "--upgrade", *flags])
            return code, json.loads(output.getvalue())
        before = self.snapshot()
        with self.changed_catalog(f"skills/{self.skill}"):
            code, report = run()
            self.assertEqual(code, 0)
            self.assertFalse(report["applied"])
            self.assertTrue(report["upgrade"])
            self.assertEqual(before, self.snapshot())
            code, report = run("--apply")
            self.assertEqual(code, 0)
            self.assertTrue(report["applied"])
            (self.root / self.relative).write_text("Customized")
            code, report = run("--apply")
            self.assertEqual(code, 1)
            self.assertFalse(report["applied"])


if __name__ == "__main__":
    unittest.main()
