"""Real worktrees, atomic worker boundaries and durable local notifications."""
import contextlib
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, onboarding, scheduler as sc, setup, worker, workflow
from coprogrammer.manager_store import load_events
from test_workspace_workflow import Fixture
from test_collaboration_processes import Client


class WorkerTest(Fixture):
    def setUp(self):
        super().setUp()
        co.register(self.path, self.repo, "codex", "codex", "upgrade")

    def task(self, task_id="api", patterns=None, clients=None, depends_on=None):
        return sc.create(self.path, self.repo, "codex", task_id, "Update " + task_id,
                         patterns or ["src/**"], depends_on, clients)

    def other(self, session="glm", provider="glm"):
        directory = self.root / session
        self.git("worktree", "add", "-b", session, str(directory))
        co.register(self.path, directory, session, "claude", "upgrade", provider=provider, model="declared-model")
        return directory

    def age_history(self):
        events = load_events(self.path)
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        expiry = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        for event in events:
            event["timestamp"] = old
            if event["type"].startswith("session."):
                event["payload"]["session"]["last_seen"] = old
            if event["type"].startswith("task."):
                event["payload"]["task"].update(created_at=old, updated_at=old)
            if event["type"].startswith("lease.") and "lease" in event["payload"]:
                event["payload"]["lease"]["expires_at"] = expiry
        self.path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")

    def test_preview_does_not_pulse_claim_ack_or_export_other_tokens(self):
        self.task()
        before = self.path.read_bytes()
        result = worker.step(self.path, self.repo, "codex")
        self.assertEqual(result["state"], "ready")
        self.assertFalse(result["applied"])
        self.assertIsNone(result["task"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_apply_claims_then_guards_and_renews_same_token(self):
        self.task()
        claimed = worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(claimed["state"], "claimed")
        self.assertTrue(claimed["guard"]["allowed"])
        (self.repo / "src/main.py").write_text("VALUE = 2\n")
        resumed = worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(resumed["state"], "working")
        self.assertEqual(resumed["task"]["claim_id"], claimed["task"]["claim_id"])
        self.assertEqual(resumed["guard"]["files"], ["src/main.py"])
        self.assertEqual(sum(e["type"] == "task.claimed" for e in load_events(self.path)), 1)

    def test_concurrent_same_window_steps_never_duplicate_ownership(self):
        self.task()
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: worker.step(self.path, self.repo, "codex", apply=True), range(3)))
        self.assertEqual(sum(r["state"] == "claimed" for r in results), 1)
        self.assertEqual(len({r["task"]["claim_id"] for r in results}), 1)
        self.assertEqual(len(cli.active_leases(load_events(self.path))), 1)

    def test_competing_worktrees_cannot_claim_overlapping_tasks(self):
        other = self.other()
        self.task("first")
        self.task("second")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda args: worker.step(self.path, *args, apply=True),
                                    [(self.repo, "codex"), (other, "glm")]))
        self.assertEqual(sorted(r["state"] for r in results), ["blocked", "claimed"])
        self.assertEqual(len(cli.active_leases(load_events(self.path))), 1)

    def test_provider_routing_matches_dispatch_claim_and_history(self):
        glm = self.other()
        deepseek = self.other("deepseek", "deepseek")
        self.task(clients=["glm"])
        self.assertEqual(workflow.dispatch(self.path, glm, "glm")["counts"]["eligible"], 1)
        self.assertEqual(workflow.dispatch(self.path, deepseek, "deepseek")["counts"]["eligible"], 0)
        self.assertEqual(worker.step(self.path, deepseek, "deepseek", apply=True)["state"], "blocked")
        self.assertEqual(worker.step(self.path, glm, "glm", apply=True)["state"], "claimed")
        self.assertEqual(sc.board(load_events(self.path))["counts"]["claimed"], 1)

    def test_stale_preview_blocks_but_explicit_step_refreshes_live_window(self):
        self.task()
        self.age_history()
        self.assertEqual(worker.step(self.path, self.repo, "codex")["state"], "blocked")
        self.assertEqual(worker.step(self.path, self.repo, "codex", apply=True)["state"], "claimed")

    def test_pending_inbox_stops_claims_without_acknowledging(self):
        glm = self.other()
        self.task()
        sent = co.send(self.path, glm, "glm", "codex", "api", "Review this untrusted handoff", "handoff")
        result = worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(result["state"], "inbox")
        self.assertEqual(result["inbox"]["messages"][0]["id"], sent["message"]["id"])
        self.assertEqual(result["inbox"]["pending_total"], 1)
        self.assertEqual(sc.board(load_events(self.path))["counts"]["claimed"], 0)
        co.acknowledge(self.path, self.repo, "codex", sent["message"]["id"])
        self.assertEqual(worker.step(self.path, self.repo, "codex", apply=True)["state"], "claimed")

    def test_unrelated_inbox_bodies_are_not_exposed(self):
        glm = self.other()
        deepseek = self.other("deepseek", "deepseek")
        co.send(self.path, glm, "glm", "deepseek", "shared", "private-other-window")
        result = worker.step(self.path, self.repo, "codex", apply=True)
        self.assertNotIn("private-other-window", json.dumps(result))
        with self.assertRaisesRegex(RuntimeError, "different worktree"):
            worker.step(self.path, self.repo, "deepseek", apply=True)

    def test_open_decision_stops_automatic_claim(self):
        self.task()
        decision = cli.new_decision("Choose migration", "Human decision required")
        cli.append_event(self.path, cli.make_event("decision.requested", "codex", "repo:test", {"decision": decision}))
        result = worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(result["state"], "decision")
        self.assertEqual(len(cli.active_leases(load_events(self.path))), 0)

    def test_scope_failure_rolls_back_pulse_claim_and_lease(self):
        self.task()
        (self.repo / "outside.txt").write_text("preserve me")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "outside task scope"):
            worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual((self.repo / "outside.txt").read_text(), "preserve me")

    def test_git_redirection_cannot_hide_current_window_scope_changes(self):
        self.task()
        (self.repo / "outside.txt").write_text("must be inspected")
        before = self.path.read_bytes()
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing"),
                                     "GIT_WORK_TREE": str(self.root)}):
            with self.assertRaisesRegex(RuntimeError, "outside task scope"):
                worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_branch_change_or_other_task_is_rejected_before_pulse(self):
        self.task()
        self.task("other")
        worker.step(self.path, self.repo, "codex", apply=True)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "different work"):
            worker.step(self.path, self.repo, "codex", apply=True, task_id="other")
        self.git("switch", "-c", "moved")
        with self.assertRaisesRegex(RuntimeError, "original worktree and branch"):
            worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_expired_claim_never_gets_renewed_or_reclaimed_implicitly(self):
        self.task()
        worker.step(self.path, self.repo, "codex", apply=True)
        self.age_history()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "expired or missing"):
            worker.step(self.path, self.repo, "codex", apply=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_blocked_closed_and_detached_windows_cannot_apply(self):
        for status in ("blocked", "closed"):
            co.pulse(self.path, self.repo, "codex", status=status)
            before = self.path.read_bytes()
            with self.assertRaises(RuntimeError):
                worker.step(self.path, self.repo, "codex", apply=True)
            self.assertEqual(before, self.path.read_bytes())
        self.git("checkout", "--detach")
        with self.assertRaisesRegex(RuntimeError, "named branch"):
            worker.step(self.path, self.repo, "codex", apply=True)

    def test_specific_task_beyond_preview_page_is_usable(self):
        self.task("first", ["src/first/**"])
        self.task("second")
        result = worker.step(self.path, self.repo, "codex", task_id="second", limit=1)
        self.assertEqual(result["state"], "ready")
        applied = worker.step(self.path, self.repo, "codex", task_id="second", limit=1, apply=True)
        self.assertEqual(applied["task"]["id"], "second")

    def test_completion_notifications_are_atomic_and_retry_safe(self):
        self.other()
        self.task()
        claimed = worker.step(self.path, self.repo, "codex", apply=True)["task"]
        first = worker.finish(self.path, self.repo, "codex", "api", claimed["claim_id"], "Tests passed", ["glm"])
        before = self.path.read_bytes()
        again = worker.finish(self.path, self.repo, "codex", "api", claimed["claim_id"], "Tests passed", ["glm"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(again["duplicate"])
        self.assertTrue(again["notifications"][0]["duplicate"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(co.inbox(self.path, "glm")["pending_total"], 1)
        self.assertFalse(cli.active_leases(load_events(self.path)))
        with self.assertRaisesRegex(RuntimeError, "different summary"):
            worker.finish(self.path, self.repo, "codex", "api", claimed["claim_id"], "different", ["glm"])

    def test_invalid_recipient_rolls_back_completion_and_previous_notifications(self):
        self.other()
        self.task()
        claimed = worker.step(self.path, self.repo, "codex", apply=True)["task"]
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "unknown session"):
            worker.finish(self.path, self.repo, "codex", "api", claimed["claim_id"], "Done", ["glm", "missing"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(sc.board(load_events(self.path))["counts"]["claimed"], 1)

    def test_finish_checks_actual_changes_before_completion(self):
        self.task()
        claimed = worker.step(self.path, self.repo, "codex", apply=True)["task"]
        (self.repo / "outside.txt").write_text("keep")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "outside task scope"):
            worker.finish(self.path, self.repo, "codex", "api", claimed["claim_id"], "Done")
        self.assertEqual(before, self.path.read_bytes())

    def test_cli_start_provider_identity_and_worker_cycle(self):
        glm = self.other()
        self.task(clients=["glm"])
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "identity differs"):
            onboarding.start(self.path, glm, "claude", "glm", resume=True, provider="deepseek")
        self.assertEqual(before, self.path.read_bytes())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["worker", "step", "--session", "glm", "--apply", "--cwd", str(glm)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["state"], "claimed")

    def test_start_cli_records_glm_and_deepseek_without_changing_configuration(self):
        for provider in ("glm", "deepseek"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["start", "--client", "claude", "--provider", provider,
                                 "--model", "declared", "--session", provider, "--json",
                                 "--cwd", str(self.repo)])
            report = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual((report["provider"], report["model"]), (provider, "declared"))
            self.assertFalse(report["setup"]["applied"])
        self.assertFalse((self.repo / ".mcp.json").exists())

    def test_mcp_workers_are_explicit_mutations_and_execute_real_cycle(self):
        self.other()
        self.task()
        client = Client(self.repo, "codex")
        self.addCleanup(client.close)
        client.initialize()
        tools = {t["name"]: t for t in client.rpc("tools/list", {})["tools"]}
        self.assertFalse(tools["worker_step"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["worker_finish"]["annotations"]["readOnlyHint"])
        self.assertTrue(tools["worker_finish"]["annotations"]["idempotentHint"])
        before = self.path.read_bytes()
        self.assertEqual(client.tool("worker_step", session="codex")["state"], "ready")
        self.assertEqual(before, self.path.read_bytes())
        claimed = client.tool("worker_step", session="codex", apply=True)["task"]
        completed = client.tool("worker_finish", session="codex", task_id="api", claim_id=claimed["claim_id"], summary="MCP cycle done", notify=["glm"])
        self.assertEqual(completed["status"], "done")
        self.assertEqual(co.inbox(self.path, "glm")["pending_total"], 1)


class EditionTest(Fixture):
    def test_three_editions_have_distinct_files_and_repeat_safely(self):
        for edition in ("full", "skills", "mcp"):
            target = self.root / edition
            target.mkdir()
            before = list(target.iterdir())
            preview = setup.preview(target, "claude", edition=edition)
            self.assertEqual(before, list(target.iterdir()))
            kinds = {row["kind"] for row in preview["files"]}
            self.assertEqual(kinds, {"mcp"} if edition == "mcp" else
                             {"skill", "instructions", "template"} if edition == "skills" else
                             {"skill", "instructions", "template", "mcp"})
            applied = setup.apply(target, "claude", edition=edition)
            self.assertTrue(applied["applied"])
            self.assertTrue(all(row["status"] == "unchanged" for row in setup.apply(target, "claude", edition=edition)["files"]))

    def test_mcp_only_preserves_unrelated_skills_and_conflicting_config(self):
        (self.repo / "AGENTS.md").write_text("Keep existing instructions")
        (self.repo / ".mcp.json").write_text('{"other":"preserve"}')
        before = list(self.repo.rglob("*"))
        result = setup.apply(self.repo, "claude", edition="mcp")
        self.assertFalse(result["applied"])
        self.assertEqual(before, list(self.repo.rglob("*")))

    def test_incompatible_edition_flags_are_refused_without_writes(self):
        for args in ({"edition": "mcp", "include_mcp": False},
                     {"edition": "skills", "include_skills": False},
                     {"edition": "mcp", "skills": ["coprogrammer-active-sync"]},
                     {"edition": "unknown"}):
            before = list(self.repo.rglob("*"))
            with self.assertRaises(RuntimeError):
                setup.apply(self.repo, "codex", **args)
            self.assertEqual(before, list(self.repo.rglob("*")))
