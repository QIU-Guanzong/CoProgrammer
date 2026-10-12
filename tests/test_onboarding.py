"""First-use CLI and MCP journeys using real Git worktrees and existing state."""
import contextlib
import io
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from coprogrammer import cli, collaboration as co, integrations, onboarding, scheduler
from coprogrammer.manager_store import load_events
from test_collaboration_processes import Client
from test_workspace_workflow import Fixture


class OnboardingTests(Fixture):
    def call(self, *argv, cwd=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main([*argv, "--cwd", str(cwd or self.repo)])
        return code, output.getvalue()

    def test_empty_status_and_dry_run_preserve_project_and_runtime_files(self):
        (self.repo / "AGENTS.md").write_text("Personal instructions", encoding="utf-8")
        (self.repo / ".mcp.json").write_text('{"private":true}', encoding="utf-8")
        before = list(self.repo.rglob("*"))
        report = onboarding.overview(self.path, self.repo)
        self.assertEqual(report["briefing"]["counts"]["sessions"], 0)
        preview = onboarding.start(self.path, self.repo, "claude", "claude", dry_run=True)
        self.assertFalse(preview["applied"])
        self.assertIn(".mcp.json", preview["setup"]["conflicts"])
        self.assertEqual(before, list(self.repo.rglob("*")))
        self.assertIn("would register", onboarding.render_start(preview))

    def test_start_registers_three_clients_without_installing_files(self):
        for client in ("codex", "claude", "copilot"):
            result = onboarding.start(self.path, self.repo, client, client)
            self.assertTrue(result["applied"])
            self.assertFalse(result["setup"]["applied"])
            self.assertEqual(result["task"], client)
            self.assertEqual(result["setup"]["connection"], "not_checked")
        self.assertEqual(len(co.directory(load_events(self.path))["sessions"]), 3)
        self.assertFalse((self.repo / "AGENTS.md").exists())
        self.assertFalse((self.repo / ".codex").exists())
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            onboarding.start(self.path, self.repo, "codex", "codex")
        self.assertEqual(before, self.path.read_bytes())

    def test_explicit_resume_preserves_identity_task_and_provider(self):
        co.register(self.path, self.repo, "codex", "codex", "upgrade", "custom", "local")
        co.pulse(self.path, self.repo, "codex", status="idle")
        before = self.path.read_bytes()
        preview = onboarding.start(self.path, self.repo, "codex", "codex", resume=True, dry_run=True)
        self.assertEqual(preview["task"], "upgrade")
        self.assertEqual(before, self.path.read_bytes())
        onboarding.start(self.path, self.repo, "codex", "codex", resume=True)
        window = co.directory(load_events(self.path))["sessions"][0]
        self.assertEqual((window["status"], window["provider"], window["model"]), ("working", "custom", "local"))

    def test_concurrent_starts_register_exactly_one_window(self):
        def attempt(_):
            try:
                onboarding.start(self.path, self.repo, "codex", "one-window")
                return "registered"
            except RuntimeError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(attempt, range(3)))
        self.assertEqual(results.count("registered"), 1)
        self.assertTrue(all(r == "registered" or "already exists" in r for r in results))
        self.assertEqual(len(load_events(self.path)), 1)

    def test_resume_rejects_other_client_worktree_blocked_or_closed_session(self):
        self.session()
        other = self.root / "other"
        self.git("worktree", "add", "-b", "other", str(other))
        for client, cwd in (("claude", self.repo), ("codex", other)):
            before = self.path.read_bytes()
            with self.assertRaises(RuntimeError):
                onboarding.start(self.path, cwd, client, "codex", resume=True)
            self.assertEqual(before, self.path.read_bytes())
        for status in ("blocked", "closed"):
            co.pulse(self.path, self.repo, "codex", status=status)
            before = self.path.read_bytes()
            with self.assertRaises(RuntimeError):
                onboarding.start(self.path, self.repo, "codex", "codex", resume=True)
            self.assertEqual(before, self.path.read_bytes())

    def test_resume_does_not_move_an_active_claim_to_another_branch_or_task(self):
        self.session()
        self.task()
        scheduler.claim(self.path, self.repo, "codex", "api")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "current claim"):
            onboarding.start(self.path, self.repo, "codex", "codex", "other-task", resume=True)
        self.git("switch", "-c", "moved")
        with self.assertRaisesRegex(RuntimeError, "original worktree and branch"):
            onboarding.start(self.path, self.repo, "codex", "codex", resume=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_status_distinguishes_repository_readiness_from_client_eligibility(self):
        self.session()
        self.task(clients=["claude"])
        repo = onboarding.overview(self.path, self.repo)
        window = onboarding.overview(self.path, self.repo, "codex")
        self.assertEqual(repo["briefing"]["counts"]["ready"], 1)
        self.assertEqual(window["dispatch"]["counts"]["eligible"], 0)
        self.assertNotIn("Available work:", onboarding.render_status(window))
        self.assertIn("0 eligible for this window", onboarding.render_status(window))

    def test_status_retains_pending_counts_without_exposing_messages_or_tokens(self):
        self.session()
        self.session("claude", "claude")
        self.task()
        claim = scheduler.claim(self.path, self.repo, "codex", "api")
        co.send(self.path, self.repo, "claude", "codex", "upgrade", "private-message-marker")
        before = self.path.read_bytes()
        report = onboarding.overview(self.path, self.repo, "codex")
        self.assertEqual(report["briefing"]["counts"]["pending_messages"], 1)
        self.assertEqual(len(report["briefing"]["claimed_tasks"]), 1)
        text = json.dumps(report) + onboarding.render_status(report)
        self.assertNotIn("private-message-marker", text)
        self.assertNotIn(claim["claim_id"], text)
        self.assertEqual(before, self.path.read_bytes())

    def test_stale_window_fails_attention_check_without_refreshing_it(self):
        self.session()
        event = json.loads(self.path.read_text(encoding="utf-8").splitlines()[0])
        old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        event["timestamp"] = event["payload"]["session"]["last_seen"] = old
        self.path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        before = self.path.read_bytes()
        code, output = self.call("status", "--session", "codex", "--fail-on-attention", "--json")
        self.assertEqual(code, 1)
        self.assertIn("session_stale", json.loads(output)["dispatch"]["session_reasons"])
        self.assertEqual(before, self.path.read_bytes())

    def test_named_committed_checkout_is_required_before_start(self):
        self.git("checkout", "--detach")
        with self.assertRaisesRegex(RuntimeError, "named branch"):
            onboarding.start(self.path, self.repo, "codex", "codex")
        self.assertFalse(self.path.exists())
        with self.assertRaisesRegex(RuntimeError, "Git checkout"):
            onboarding.overview(self.path, self.root)
        with self.assertRaisesRegex(RuntimeError, "unknown session"):
            onboarding.overview(self.path, self.repo, "missing")
        self.assertFalse(self.path.parent.exists())

    def test_unicode_worktree_and_branch_keep_their_actual_names(self):
        other = self.root / "协作目录"
        subprocess.run(["git", "worktree", "add", "-b", "codex/接口", str(other)],
                       cwd=self.repo, capture_output=True, check=True, timeout=20)
        report = onboarding.start(self.path, other, "codex", "unicode-window")
        self.assertEqual(report["workspace"]["worktree"], str(other))
        self.assertEqual(report["workspace"]["branch"], "codex/接口")
        self.assertEqual(onboarding.overview(self.path, other, "unicode-window")["workspace"], report["workspace"])

    def test_two_window_cli_start_status_claim_and_message_journey(self):
        other = self.root / "claude"
        self.git("worktree", "add", "-b", "claude-ui", str(other))
        for client, cwd in (("codex", self.repo), ("claude", other)):
            code, output = self.call("start", "--client", client, "--session", client, "--task", "upgrade", "--json", cwd=cwd)
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output)["applied"])
        self.task(clients=["codex"])
        code, text = self.call("status", "--session", "codex")
        self.assertEqual(code, 0)
        self.assertIn("manager task claim --session codex --id api", text)
        code, text = self.call("status", "--session", "claude", cwd=other)
        self.assertIn("0 eligible for this window", text)
        scheduler.claim(self.path, self.repo, "codex", "api")
        co.send(self.path, self.repo, "codex", "claude", "upgrade", "API is ready for review")
        code, text = self.call("status", "--session", "claude", cwd=other)
        self.assertIn("Pending messages: 1", text)
        self.assertIn("read_inbox", json.dumps(onboarding.overview(self.path, other, "claude")))

    def test_stdio_status_is_read_only_and_validates_its_schema(self):
        self.session()
        client = Client(self.repo, "codex")
        self.addCleanup(client.close)
        client.initialize()
        tools = client.rpc("tools/list", {})["tools"]
        tool = next(t for t in tools if t["name"] == "workspace_status")
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        before = self.path.read_bytes()
        self.assertEqual(client.tool("workspace_status", session="codex")["format"], "coprogrammer.status.v1")
        self.assertTrue(client.rpc("tools/call", {"name": "workspace_status", "arguments": {"limit": 0}})["isError"])
        self.assertEqual(before, self.path.read_bytes())

    def test_legacy_encoding_stdout_receives_utf8_status_and_start(self):
        self.session()
        scheduler.create(self.path, self.repo, "codex", "api", "更新接口", ["src/**"])
        config = json.loads(integrations.client_config("claude", self.repo))["mcpServers"]["coprogrammer"]
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        for args, expected in ((["status", "--session", "codex"], "更新接口"),
                               (["start", "--client", "claude", "--session", "new", "--dry-run"], "would register")):
            result = subprocess.run([config['command'], *config['args'][1:3], *args], cwd=self.repo,
                                    env=env, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout.decode("utf-8"))
