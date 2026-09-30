"""Offline review handoffs through the CLI and MCP client boundaries."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, mcp_server
from coprogrammer.review import create_review


class ReviewSummarySurfaceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Test Fixture")
        (self.root / "app.py").write_text("VALUE = 1\n")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.git("checkout", "-b", "feature")
        (self.root / "app.py").write_text("VALUE = 2\n")
        self.git("commit", "-am", "change")
        advice = {"summary": "Fixture advice", "changes": [
            {"path": "app.py", "decision": "preserve", "reason": "Value change"}
        ], "risks": [], "validation": ["Check value"]}
        with patch("coprogrammer.providers.complete", return_value={
            "text": json.dumps(advice), "finish_reason": "stop", "truncated": False,
        }):
            artifact = create_review(self.root, "main", "feature", "glm", "fixture-model", send=True)
        (self.root / "review.json").write_text(json.dumps(artifact), encoding="utf-8")
        self.ctx = mcp_server.ManagerContext(self.root)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def run_cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = cli.main(["review-summary", "--cwd", str(self.root),
                             "--base", "main", "--head", "feature", *args])
        return code, output.getvalue(), errors.getvalue()

    def call_mcp(self, arguments):
        return mcp_server.handle_request(self.ctx, {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "review_summary", "arguments": arguments},
        })

    def test_cli_summarizes_relative_artifact_without_network_or_manager_writes(self):
        with patch("coprogrammer.providers.complete") as provider:
            code, output, errors = self.run_cli("--review", "glm=review.json", "--fail-on-attention")
        self.assertEqual((code, errors), (0, ""))
        report = json.loads(output)
        self.assertEqual(report["target"]["head_sha"], self.git("rev-parse", "feature"))
        self.assertEqual(report["reviewers"][0]["status"], "current")
        self.assertEqual(report["status"], "draft")
        self.assertTrue(report["requires_human_review"])
        provider.assert_not_called()
        self.assertFalse((self.root / ".coprogrammer").exists())

    def test_attention_exit_preserves_report_and_names_missing_reviewer(self):
        output = self.root / "summary.json"
        code, _, errors = self.run_cli("--review", "glm=review.json", "--expect", "claude",
                                       "--fail-on-attention", "--output", str(output))
        self.assertEqual((code, errors), (1, ""))
        report = json.loads(output.read_text())
        states = {item["label"]: item["status"] for item in report["reviewers"]}
        self.assertEqual(states, {"glm": "current", "claude": "missing"})

    def test_existing_output_is_preserved_before_artifact_collection(self):
        output = self.root / "summary.json"
        output.write_text("prior report")
        with patch("coprogrammer.review_summary.build_summary") as build:
            code, _, errors = self.run_cli("--expect", "claude", "--output", str(output))
        self.assertEqual(code, 2)
        self.assertIn("already exists", errors)
        self.assertEqual(output.read_text(), "prior report")
        build.assert_not_called()

    def test_duplicate_or_malformed_labels_are_errors_not_overwrites(self):
        for arguments in (("--review", "a=review.json", "--review", "a=elsewhere.json"),
                          ("--review", "review.json"), ("--review", "a="),
                          ("--review", "bad label=review.json"), ()):
            with self.subTest(arguments=arguments):
                code, output, errors = self.run_cli(*arguments)
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertTrue(errors)

    def test_cli_renders_both_languages_and_reports_old_immutable_targets(self):
        for language in ("en", "zh-CN"):
            code, output, errors = self.run_cli("--review", "glm=review.json",
                                               "--format", "markdown", "--language", language)
            self.assertEqual((code, errors), (0, ""))
            self.assertTrue(output.startswith("# "))
            self.assertIn("glm", output)
        self.git("commit", "--allow-empty", "-m", "target moved")
        code, output, _ = self.run_cli("--review", "glm=review.json", "--fail-on-attention")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["reviewers"][0]["status"], "stale")

    def test_mcp_exposes_read_only_structured_report_and_no_state_mutation(self):
        descriptor = next(tool for tool in mcp_server.TOOLS if tool["name"] == "review_summary")
        self.assertTrue(descriptor["annotations"]["readOnlyHint"])
        self.assertFalse(descriptor["annotations"]["openWorldHint"])
        with patch("coprogrammer.providers.complete") as provider:
            response = self.call_mcp({"base": "main", "head": "feature",
                                     "reviews": [{"label": "glm", "path": "review.json"}],
                                     "expected": ["glm", "claude"]})
        self.assertFalse(response["result"].get("isError", False))
        report = response["result"]["structuredContent"]
        self.assertTrue(report["attention_required"])
        self.assertEqual(report["counts"]["current"], 1)
        self.assertEqual(report["counts"]["missing"], 1)
        self.assertEqual(report["remote_freshness"], "not_checked")
        provider.assert_not_called()
        self.assertFalse((self.root / ".coprogrammer").exists())

    def test_mcp_rejects_invalid_nested_inputs_and_recovers(self):
        cases = [
            {"reviews": [{"label": "a", "path": "review.json", "send": True}]},
            {"reviews": [{"label": "a"}]},
            {"reviews": [{"label": "bad label", "path": "review.json"}]},
            {"reviews": [{"label": "a", "path": "review.json"}] * 17},
            {"reviews": [{"label": "a", "path": "review.json"}] * 2},
            {"expected": "claude"},
            {"expected": ["a"] * 17},
            {"send": True},
        ]
        for case in cases:
            with self.subTest(case=case):
                response = self.call_mcp({"base": "main", "head": "feature", **case})
                self.assertTrue(response["result"]["isError"])
        response = self.call_mcp({"base": "main", "head": "feature", "expected": ["claude"]})
        self.assertEqual(response["result"]["structuredContent"]["counts"]["missing"], 1)
        self.assertFalse((self.root / ".coprogrammer").exists())

    def test_stdio_roundtrip_produces_json_and_pong_after_summary(self):
        stream = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "review_summary", "arguments": {
                    "base": "main", "head": "feature", "expected": ["claude"]}}},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        ]
        stdout = io.StringIO()
        mcp_server.serve(self.root, None, io.StringIO("\n".join(map(json.dumps, stream)) + "\n"), stdout)
        responses = list(map(json.loads, stdout.getvalue().splitlines()))
        self.assertEqual(responses[1]["result"]["structuredContent"]["status"], "draft")
        self.assertEqual(responses[2], {"jsonrpc": "2.0", "id": 3, "result": {}})
