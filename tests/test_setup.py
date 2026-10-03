from __future__ import annotations

import contextlib
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

from coprogrammer import knowledge, setup
from coprogrammer.cli import main


class ProjectSetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project setup ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_preview_is_read_only_and_contains_exact_generated_content(self):
        preview = setup.preview(self.root, "codex", include_content=True)
        self.assertFalse(preview["applied"])
        self.assertTrue(preview["can_apply"])
        self.assertEqual(list(self.root.iterdir()), [])
        rows = {row["path"]: row for row in preview["files"]}
        self.assertIn(".codex/config.toml", rows)
        self.assertEqual(rows["AGENTS.md"]["content"], knowledge.read_document("templates/AGENTS"))
        self.assertEqual(preview["connection"], "not_checked")

    def test_client_layouts_and_missing_only_repeat_are_consistent(self):
        for client, (directory, config, instructions) in setup.CLIENT_LAYOUTS.items():
            with self.subTest(client=client), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                first = setup.apply(root, client)
                self.assertTrue(first["applied"])
                self.assertTrue((root / config).is_file())
                if instructions:
                    self.assertTrue((root / instructions).is_file())
                skills = [d for d in knowledge.documents() if d["kind"] == "skill"]
                for skill in skills:
                    self.assertEqual((root / directory / skill["name"] / "SKILL.md").read_bytes().decode("utf-8"),
                                     knowledge.read_document(skill["id"]))
                before = {row["path"]: (root / row["path"]).stat().st_mtime_ns for row in first["files"]}
                second = setup.apply(root, client)
                self.assertTrue(all(row["status"] == "unchanged" for row in second["files"]))
                self.assertEqual(before, {name: (root / name).stat().st_mtime_ns for name in before})

    def test_existing_instructions_are_preserved_without_exposing_content(self):
        secret = "Private project instruction marker, not generated output"
        (self.root / "AGENTS.md").write_text(secret, encoding="utf-8")
        report = setup.apply(self.root, "claude", include_mcp=False, include_content=True)
        self.assertTrue(report["applied"])
        self.assertEqual((self.root / "AGENTS.md").read_text(), secret)
        self.assertNotIn(secret, json.dumps(report))
        row = next(r for r in report["files"] if r["path"] == "AGENTS.md")
        self.assertEqual(row["status"], "preserve")
        self.assertTrue(report["warnings"])

    def test_existing_mcp_conflict_keeps_every_target_unchanged(self):
        content = '{"mcpServers":{"private":{"env":{"TOKEN":"secret-marker"}}}}'
        (self.root / ".mcp.json").write_text(content, encoding="utf-8")
        before = list(self.root.rglob("*"))
        report = setup.apply(self.root, "claude", include_content=True)
        self.assertFalse(report["applied"])
        self.assertFalse(report["can_apply"])
        self.assertEqual(report["conflicts"], [".mcp.json"])
        self.assertEqual(list(self.root.rglob("*")), before)
        self.assertEqual((self.root / ".mcp.json").read_text(), content)
        self.assertNotIn("secret-marker", json.dumps(report))
        self.assertTrue(setup.apply(self.root, "claude", include_mcp=False)["applied"])

    def test_jsonc_and_changed_skill_are_not_rewritten(self):
        path = self.root / ".vscode/mcp.json"
        path.parent.mkdir()
        content = '// comment\n{"servers":{}}\n'
        path.write_text(content, encoding="utf-8")
        self.assertFalse(setup.apply(self.root, "copilot")["applied"])
        self.assertEqual(path.read_text(), content)
        setup.apply(self.root, "copilot", include_mcp=False)
        skill = next(self.root.glob(".agents/skills/*/SKILL.md"))
        skill.write_text("User customized skill", encoding="utf-8")
        self.assertFalse(setup.apply(self.root, "copilot", include_mcp=False)["applied"])
        self.assertEqual(skill.read_text(), "User customized skill")

    def test_selection_and_duplicate_directory_warning(self):
        name = "coprogrammer-active-sync"
        alternate = self.root / ".claude/skills" / name / "SKILL.md"
        alternate.parent.mkdir(parents=True)
        alternate.write_text("Existing skill", encoding="utf-8")
        report = setup.preview(self.root, "codex", [name], include_mcp=False)
        self.assertEqual(len([r for r in report["files"] if r["kind"] == "skill"]), 1)
        self.assertTrue(any(".claude/skills" in warning for warning in report["warnings"]))
        for names in ([name, name], ["../../escape"], "all"):
            with self.assertRaises(RuntimeError):
                setup.preview(self.root, "codex", names)

    def test_symlinked_target_and_parent_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp).resolve()
            target = external / "instructions.md"
            target.write_text("Preserve external instructions", encoding="utf-8")
            try:
                (self.root / "AGENTS.md").symlink_to(target)
                (self.root / ".agents").symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            report = setup.apply(self.root, "codex")
            self.assertFalse(report["can_apply"])
            self.assertIn("AGENTS.md", report["conflicts"])
            self.assertEqual(target.read_text(), "Preserve external instructions")
            self.assertFalse((external / "skills").exists())
            self.assertFalse((self.root / "docs").exists())

    def test_concurrent_installers_create_one_consistent_file_set(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: setup.apply(self.root, "claude"), range(2)))
        self.assertTrue(all(result["applied"] for result in results))
        self.assertTrue(setup.preview(self.root, "claude")["can_apply"])
        self.assertTrue(all(r["status"] == "unchanged" for r in setup.preview(self.root, "claude")["files"]))

    def test_locked_manager_file_does_not_require_resolving_its_contents(self):
        lock = self.root / ".coprogrammer/events.jsonl.lock"
        lock.parent.mkdir()
        lock.touch()
        original = Path.resolve

        def resolve(path, *args, **kwargs):
            if path == lock:
                raise PermissionError("Windows cannot open another owner's locked file")
            return original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            self.assertTrue(setup.apply(self.root, "claude")["applied"])
        self.assertEqual(lock.read_bytes(), b"")

    def test_windows_reparse_parent_is_blocked_without_resolving(self):
        parent = self.root / ".agents"
        parent.mkdir()
        original = Path.lstat

        def lstat(path, *args, **kwargs):
            if path == parent:
                return SimpleNamespace(st_mode=stat.S_IFDIR,
                                       st_file_attributes=0x400)
            return original(path, *args, **kwargs)

        with patch.object(Path, "lstat", lstat):
            report = setup.apply(self.root, "codex")
        self.assertFalse(report["can_apply"])
        self.assertTrue(any(name.startswith(".agents/") for name in report["conflicts"]))
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_manager_log_and_lock_links_cannot_create_external_files(self):
        state = self.root / ".coprogrammer"
        state.mkdir()
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp).resolve() / "external-events.jsonl"
            external.write_text("")
            for name in ("events.jsonl", "events.jsonl.lock"):
                with self.subTest(name=name):
                    link = state / name
                    try:
                        link.symlink_to(external)
                    except OSError:
                        self.skipTest("symlink creation unavailable")
                    with self.assertRaisesRegex(RuntimeError, "unsafe linked setup path"):
                        setup.apply(self.root, "claude")
                    self.assertFalse((external.parent / (external.name + ".lock")).exists())
                    self.assertEqual(external.read_bytes(), b"")
                    self.assertFalse((self.root / "AGENTS.md").exists())
                    link.unlink()

    def test_manager_log_non_regular_file_is_rejected_before_setup(self):
        (self.root / ".coprogrammer/events.jsonl").mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, "not a regular file"):
            setup.apply(self.root, "codex")
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_failed_late_write_rolls_back_created_files(self):
        original = Path.open
        def fail(target, mode="r", *args, **kwargs):
            if target.name == ".mcp.json" and mode == "xb":
                raise OSError("simulated write failure")
            return original(target, mode, *args, **kwargs)
        with patch.object(Path, "open", fail), self.assertRaisesRegex(RuntimeError, "rolled back"):
            setup.apply(self.root, "claude")
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse(any(self.root.rglob("SKILL.md")))

    def test_generated_mcp_config_launches_installed_tools_and_resources(self):
        setup.apply(self.root, "claude")
        config = json.loads((self.root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["coprogrammer"]
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "resources/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        ]
        result = subprocess.run([config["command"], *config["args"]], cwd=self.root,
                                input="".join(json.dumps(r) + "\n" for r in requests),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertIn("resources", replies[0]["result"]["capabilities"])
        self.assertEqual(len(replies[1]["result"]["resources"]), len(knowledge.documents()))
        self.assertIn("task_claim", {t["name"] for t in replies[2]["result"]["tools"]})

    def test_cli_preview_list_read_and_conflict_exit(self):
        def run(args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(args)
            return code, output.getvalue()
        code, text = run(["knowledge", "list", "--kind", "skill"])
        self.assertEqual(code, 0)
        self.assertTrue(all(d["kind"] == "skill" for d in json.loads(text)["documents"]))
        code, text = run(["knowledge", "show", "templates/handoff"])
        self.assertEqual(text, knowledge.read_document("templates/handoff"))
        code, text = run(["setup", "--client", "claude", "--cwd", str(self.root)])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(text)["applied"])
        self.assertEqual(list(self.root.iterdir()), [])
        (self.root / ".mcp.json").write_text("{}")
        code, text = run(["setup", "--client", "claude", "--cwd", str(self.root), "--apply"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(text)["applied"])


if __name__ == "__main__":
    unittest.main()
