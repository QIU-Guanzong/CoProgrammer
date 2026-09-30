from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, collaboration as co, mcp_server, scheduler
from coprogrammer.briefing import build_briefing, render_text


class BriefingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name).resolve()
        self.path = self.cwd / ".coprogrammer" / "events.jsonl"
        co.register(self.path, self.cwd, "a", "codex", "upgrade")
        co.register(self.path, self.cwd, "b", "claude", "upgrade")

    def report(self, **kwargs):
        return build_briefing(cli.load_events(self.path), **kwargs)

    def test_empty_repository_has_action_without_false_alarm(self):
        report = build_briefing([])
        self.assertFalse(report["attention_required"])
        self.assertEqual(report["cursor"], "")
        self.assertEqual(report["next_actions"][0]["code"], "register_session")

    def test_dependencies_and_client_requirements_are_visible(self):
        scheduler.create(self.path, self.cwd, "a", "api", "API", ["src/api/**"], clients=["codex"])
        scheduler.create(self.path, self.cwd, "b", "ui", "UI", ["src/ui/**"], depends_on=["api"])
        report = self.report(session="b")
        self.assertEqual([t["id"] for t in report["ready_tasks"]], ["api"])
        self.assertEqual(report["ready_tasks"][0]["clients"], ["codex"])
        self.assertEqual(report["blocked_tasks"][0]["blocked_reasons"], ["unfinished_dependencies"])
        self.assertFalse(report["attention_required"])
        self.assertIn("repository-wide", report["note"])
        self.assertIn("clients: codex", render_text(report))
        self.assertIn("a (codex): working / fresh", render_text(report))

    def test_counts_are_complete_when_rows_are_bounded_and_order_is_stable(self):
        for name in ("z", "x", "y"):
            scheduler.create(self.path, self.cwd, "a", name, name, [name + "/**"])
        report = self.report(limit=1)
        self.assertEqual(report["counts"]["ready"], 3)
        self.assertEqual(report["omitted"]["ready_tasks"], 2)
        self.assertEqual(report["ready_tasks"][0]["id"], "x")
        self.assertIn("2 more ready_tasks", render_text(report))

    def test_inbox_is_scoped_without_bodies_or_mutations(self):
        message = co.send(self.path, self.cwd, "a", "b", "upgrade", "private-body-value")
        co.send(self.path, self.cwd, "b", "a", "upgrade", "other-private-body")
        before = self.path.read_bytes()
        report = self.report(session="b")
        self.assertEqual(report["counts"]["pending_messages"], 1)
        self.assertEqual(self.report()["counts"]["pending_messages"], 2)
        self.assertTrue(report["attention_required"])
        self.assertNotIn("private-body", json.dumps(report))
        self.assertNotIn(message["message"]["id"], json.dumps(report))
        self.assertEqual(self.path.read_bytes(), before)

    def test_stale_and_future_pulses_need_attention_but_closed_windows_do_not(self):
        events = cli.load_events(self.path)
        for offset, expected in ((-900, "stale"), (900, "unknown")):
            changed = copy.deepcopy(events)
            when = (co.timestamp(events[0]["timestamp"]) + timedelta(seconds=offset)).isoformat()
            changed[0]["timestamp"] = when
            changed[0]["payload"]["session"]["last_seen"] = when
            report = build_briefing(changed)
            self.assertEqual(report["sessions"][0]["freshness"], expected)
            self.assertTrue(report["attention_required"])
        co.pulse(self.path, self.cwd, "a", status="closed")
        report = self.report()
        self.assertEqual(report["counts"]["sessions"], 1)
        self.assertFalse(report["attention_required"])

    def test_decisions_and_lease_conflicts_have_explicit_actions(self):
        decision = cli.new_decision("Review this", "context", [], "high")
        cli.append_event(self.path, cli.make_event("decision.requested", "a", "repo:local", {"decision": decision}))
        for holder in ("a", "b"):
            lease = cli.new_lease(holder, "path", ["src/**"])
            cli.append_event(self.path, cli.make_event("lease.granted", holder, "repo:local", {"lease": lease}))
        report = self.report()
        self.assertEqual(report["counts"]["lease_overlaps"], 1)
        self.assertEqual(report["counts"]["open_decisions"], 1)
        self.assertEqual({a["code"] for a in report["next_actions"]}, {"review_decision", "resolve_overlap"})

    def test_malformed_history_unknown_session_and_invalid_limit_fail(self):
        for limit in (0, 201, True):
            with self.assertRaises(RuntimeError):
                self.report(limit=limit)
        with self.assertRaisesRegex(RuntimeError, "unknown session"):
            self.report(session="missing")
        events = cli.load_events(self.path)
        events.append(copy.deepcopy(events[0]))
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            build_briefing(events)

    def test_cli_attention_exit_and_mcp_report_match(self):
        co.send(self.path, self.cwd, "a", "b", "upgrade", "private-text")
        before = self.path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["manager", "briefing", "--cwd", str(self.cwd), "--session", "b",
                             "--json", "--fail-on-attention"])
        self.assertEqual(code, 1)
        report = json.loads(output.getvalue())
        response = mcp_server.handle_request(mcp_server.ManagerContext(self.cwd), {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "manager_briefing", "arguments": {"session": "b"}}})
        mcp_report = json.loads(response["result"]["content"][0]["text"])
        report.pop("generated_at")
        mcp_report.pop("generated_at")
        self.assertEqual(mcp_report, report)
        self.assertEqual(self.path.read_bytes(), before)
        declaration = next(t for t in mcp_server.TOOLS if t["name"] == "manager_briefing")
        self.assertTrue(declaration["annotations"]["readOnlyHint"])

    def test_one_observation_time_keeps_lease_and_window_expiry_consistent(self):
        scheduler.create(self.path, self.cwd, "a", "api", "API", ["src/**"])
        claim = scheduler.claim(self.path, self.cwd, "a", "api", ttl_seconds=30)
        events = cli.load_events(self.path)
        lease = cli.active_leases(events)[claim["lease_id"]]
        expiry = cli.lease_expiry(lease)
        # Simulate an operation that would cross expiry between its reducers.
        with patch("coprogrammer.briefing.datetime") as clock, \
                patch("coprogrammer.cli.datetime") as other_clock:
            clock.now.return_value = expiry - timedelta(milliseconds=1)
            other_clock.now.return_value = expiry + timedelta(milliseconds=1)
            other_clock.fromisoformat.side_effect = co.datetime.fromisoformat
            report = build_briefing(events)
        self.assertEqual(report["counts"]["active_leases"], 1)
        self.assertFalse(report["attention_required"])
        self.assertEqual(report["blocked_tasks"], [])
        with patch("coprogrammer.briefing.datetime") as clock:
            clock.now.return_value = expiry
            report = build_briefing(events)
        self.assertEqual(report["counts"]["active_leases"], 0)
        self.assertTrue(report["attention_required"])
        self.assertIn("explicit_reclaim_required", report["blocked_tasks"][0]["blocked_reasons"])

    def test_expired_claim_is_visible_without_reclaiming_or_exposing_token(self):
        scheduler.create(self.path, self.cwd, "a", "api", "API", ["src/**"])
        claim = scheduler.claim(self.path, self.cwd, "a", "api")
        cli.append_event(self.path, cli.make_event("lease.released", "a", "repo:local",
                                                  {"lease_id": claim["lease_id"]}))
        before = self.path.read_bytes()
        report = self.report(session="a")
        self.assertIn("review_reclaim", [a["code"] for a in report["next_actions"]])
        self.assertNotIn(claim["claim_id"], json.dumps(report))
        self.assertEqual(self.path.read_bytes(), before)
