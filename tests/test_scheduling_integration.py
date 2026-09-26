"""Scheduling through independent MCP clients and real linked Git worktrees.

These tests exercise local protocol operations only. Client/provider labels are
self-reported; no model is called and a completion summary is not test evidence.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from coprogrammer import cli
from test_collaboration_processes import Client


class SchedulingIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "main"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-m", "initial")
        self.worktree = self.root / "claude"
        self.git("worktree", "add", "-b", "feature", str(self.worktree))
        self.codex = self.client(self.repo, "codex")
        self.claude = self.client(self.worktree, "claude")
        for client, session, brand in ((self.codex, "codex-api", "codex"),
                                       (self.claude, "claude-ui", "claude")):
            client.tool("session_register", session=session, client=brand,
                        task="scheduling", ttl_seconds=300)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True,
                              capture_output=True, text=True, timeout=20).stdout.strip()

    def client(self, cwd, brand):
        client = Client(cwd, brand)
        self.addCleanup(client.close)
        client.initialize()
        return client

    def create(self, task, patterns, **kwargs):
        return self.codex.tool("task_create", session="codex-api", task_id=task,
                               title=f"Implement {task}", patterns=patterns, **kwargs)

    def raw_tool(self, client, name, **kwargs):
        return client.rpc("tools/call", {"name": name, "arguments": kwargs})

    def denied(self, client, name, **kwargs):
        result = self.raw_tool(client, name, **kwargs)
        self.assertTrue(result.get("isError"), result)
        return result["content"][0]["text"]

    def test_two_client_processes_cannot_claim_the_same_task(self):
        self.create("api", ["src/api/**"], clients=["codex", "claude"])
        ready = threading.Barrier(2)

        def claim(entry):
            client, session = entry
            ready.wait(timeout=10)
            return self.raw_tool(client, "task_claim", session=session, task_id="api")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, [(self.codex, "codex-api"),
                                            (self.claude, "claude-ui")]))
        self.assertEqual(sum(not result.get("isError") for result in results), 1)
        winner = json.loads(next(result for result in results if not result.get("isError"))["content"][0]["text"])
        self.assertIn(winner["session"], ("codex-api", "claude-ui"))
        self.assertEqual(winner["status"], "claimed")
        self.assertTrue(winner["claim_id"])
        snapshot = self.codex.tool("manager_sync")
        self.assertEqual(len(snapshot["active_leases"]), 1)
        self.assertEqual(snapshot["active_leases"][0]["id"], winner["lease_id"])
        self.assertEqual(snapshot["active_leases"][0]["holder"], winner["session"])
        self.assertEqual(winner["worktree"], str(self.repo if winner["session"] == "codex-api"
                                                else self.worktree))
        self.assertEqual(winner["branch"], "main" if winner["session"] == "codex-api" else "feature")

    def test_windows_sharing_a_checkout_cannot_hold_disjoint_tasks_simultaneously(self):
        other_window = self.client(self.repo, "claude")
        other_window.tool("session_register", session="claude-same-checkout", client="claude",
                          task="scheduling", ttl_seconds=300)
        self.create("api", ["src/api/**"])
        self.create("docs", ["docs/**"])
        first = self.codex.tool("task_claim", session="codex-api", task_id="api")
        denial = self.denied(other_window, "task_claim", session="claude-same-checkout", task_id="docs")
        self.assertIn("worktree", denial)
        self.assertIn("different worktree", self.denied(
            self.claude, "task_guard", session="codex-api", task_id="api",
            claim_id=first["claim_id"], files=["src/api/routes.py"]))
        self.codex.tool("task_release", session="codex-api", task_id="api",
                        claim_id=first["claim_id"], summary="Yield checkout to the documentation window.")
        second = other_window.tool("task_claim", session="claude-same-checkout", task_id="docs")
        self.assertEqual(second["status"], "claimed")
        self.denied(self.codex, "task_guard", session="codex-api", task_id="api",
                    claim_id=first["claim_id"], files=["src/api/routes.py"])

    def test_overlapping_tasks_wait_until_completion_releases_the_path(self):
        self.create("api", ["src/api/**"])
        self.create("models", ["src/api/models.py"])
        first = self.codex.tool("task_claim", session="codex-api", task_id="api")
        self.assertIn("conflict", self.denied(self.claude, "task_claim", session="claude-ui", task_id="models"))
        self.assertEqual(len(self.claude.tool("manager_sync")["active_leases"]), 1)
        summary = "Author reports implementation complete; checks have not been independently verified."
        completed = self.codex.tool("task_finish", session="codex-api", task_id="api",
                                    claim_id=first["claim_id"], summary=summary)
        self.assertEqual(completed["status"], "done")
        self.assertEqual(completed["summary"], summary)
        board = self.claude.tool("task_board")
        self.assertEqual(next(task for task in board["tasks"] if task["id"] == "api")["summary"], summary)
        self.assertEqual(self.codex.tool("manager_sync")["active_leases"], [])
        second = self.claude.tool("task_claim", session="claude-ui", task_id="models")
        self.assertEqual(second["status"], "claimed")
        self.assertNotEqual(second["claim_id"], first["claim_id"])
        self.assertNotEqual(second["lease_id"], first["lease_id"])

    def test_dependency_and_client_routing_are_enforced_across_clients(self):
        self.create("api", ["src/api/**"], clients=["codex"])
        self.create("ui", ["src/ui/**"], depends_on=["api"], clients=["claude"])
        self.assertIn("eligible", self.denied(self.claude, "task_claim", session="claude-ui", task_id="api"))
        self.assertIn("dependencies", self.denied(self.claude, "task_claim", session="claude-ui", task_id="ui"))
        first = self.codex.tool("task_claim", session="codex-api", task_id="api")
        self.codex.tool("task_finish", session="codex-api", task_id="api",
                        claim_id=first["claim_id"], summary="Author-reported handoff; no external model called.")
        self.assertIn("eligible", self.denied(self.codex, "task_claim", session="codex-api", task_id="ui"))
        next_task = self.claude.tool("task_claim", session="claude-ui")
        self.assertEqual(next_task["status"], "claimed")
        self.assertEqual(next_task["id"], "ui")

    def test_branch_switch_invalidates_write_guard_and_task_completion(self):
        self.create("api", ["src/api/**"])
        task = self.codex.tool("task_claim", session="codex-api", task_id="api")
        guard = self.codex.tool("task_guard", session="codex-api", task_id="api",
                               claim_id=task["claim_id"], files=["src/api/routes.py"])
        self.assertTrue(guard["allowed"])
        self.git("checkout", "-b", "unrelated")
        before = cli.event_log_path(self.repo).read_bytes()
        for tool, extra in (("task_guard", {"files": ["src/api/routes.py"]}),
                            ("task_finish", {"summary": "Incorrect branch completion"})):
            result = self.raw_tool(self.codex, tool, session="codex-api", task_id="api",
                                   claim_id=task["claim_id"], **extra)
            self.assertTrue(result.get("isError"), result)
            self.assertIn("branch", result["content"][0]["text"].lower())
        self.assertEqual(cli.event_log_path(self.repo).read_bytes(), before)

    def test_detached_checkout_cannot_claim_or_continue_a_named_branch_task(self):
        self.create("api", ["src/api/**"])
        self.git("checkout", "--detach")
        before = cli.event_log_path(self.repo).read_bytes()
        self.assertIn("detached", self.denied(self.codex, "task_claim", session="codex-api", task_id="api"))
        self.assertEqual(cli.event_log_path(self.repo).read_bytes(), before)
        self.git("checkout", "main")
        task = self.codex.tool("task_claim", session="codex-api", task_id="api")
        self.git("checkout", "--detach")
        before = cli.event_log_path(self.repo).read_bytes()
        for tool, extra in (("task_guard", {"files": ["src/api/routes.py"]}),
                            ("task_renew", {"ttl_seconds": 3600}),
                            ("task_finish", {"summary": "Cannot complete from detached HEAD"}),
                            ("task_release", {"summary": "Cannot release from detached HEAD"})):
            self.denied(self.codex, tool, session="codex-api", task_id="api",
                        claim_id=task["claim_id"], **extra)
        self.assertEqual(cli.event_log_path(self.repo).read_bytes(), before)
        self.git("checkout", "main")
        self.codex.tool("task_finish", session="codex-api", task_id="api",
                        claim_id=task["claim_id"], summary="Original branch restored; author reports completion.")

    def test_long_poll_releases_state_lock_for_task_and_message_writers(self):
        for event_type in ("task.created", "message.sent"):
            with self.subTest(event_type=event_type):
                baseline = self.claude.tool("manager_sync", session="claude-ui")
                entered = threading.Event()

                def wait():
                    entered.set()
                    return self.claude.tool("manager_wait", session="claude-ui",
                                            after=baseline["next_cursor"], timeout_seconds=3)

                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(wait)
                    self.assertTrue(entered.wait(timeout=5))
                    # Allow the receiver to enter its poll; a blocked writer
                    # would make the receiver time out without this event.
                    threading.Event().wait(0.15)
                    if event_type == "task.created":
                        self.create("notified", ["src/notify/**"])
                    else:
                        self.codex.tool("message_send", sender="codex-api", recipient="claude-ui",
                                        task="notified", body="Work is ready for review.", key="notify-review")
                    result = pending.result(timeout=10)
                self.assertIn(event_type, {event["type"] for event in result["changes"]})
                self.assertEqual(result["wait_status"], "changed")
                self.assertNotEqual(result["next_cursor"], baseline["next_cursor"])
        inbox = self.claude.tool("message_inbox", session="claude-ui")
        self.assertEqual(inbox["pending_total"], 1)
        self.assertIsNone(inbox["messages"][0]["acknowledged_at"])
        thread = self.claude.tool("message_thread", session="claude-ui", task="notified")
        self.assertEqual(thread["messages"][0]["id"], inbox["messages"][0]["id"])
        message_id = inbox["messages"][0]["id"]
        self.claude.tool("message_ack", session="claude-ui", message_id=message_id)
        reply = self.claude.tool("message_send", sender="claude-ui", recipient="codex-api",
                                 task="notified", body="Received; review has not started.", reply_to=message_id)
        for client, session in ((self.codex, "codex-api"), (self.claude, "claude-ui")):
            thread = client.tool("message_thread", session=session, task="notified")
            self.assertEqual([message["id"] for message in thread["messages"]],
                             [message_id, reply["message"]["id"]])
            self.assertTrue(thread["messages"][0]["acknowledged_at"])
            self.assertIsNone(thread["messages"][1]["acknowledged_at"])


if __name__ == "__main__":
    unittest.main()
