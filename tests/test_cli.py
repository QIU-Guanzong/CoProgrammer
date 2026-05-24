import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from coprogrammer.cli import (
    build_pr_comment_body,
    classify_risks,
    find_lease_conflicts,
    load_events,
    load_pull_request_number,
    main,
    match_protected_paths,
    new_lease,
    new_heartbeat,
    open_decisions,
    patterns_overlap,
    render_digest,
    resolve_language,
    score_risk,
    validate_agents_file,
    validate_config_data,
    validate_manifest,
)


class RiskClassificationTest(unittest.TestCase):
    def test_classifies_contract_and_security_paths(self) -> None:
        risks = classify_risks(
            [
                "schemas/change-manifest.schema.json",
                "src/auth/session.py",
                "README.md",
            ]
        )

        self.assertIn("contract", risks)
        self.assertIn("security", risks)
        self.assertNotIn("build", risks)

    def test_matches_protected_paths_and_scores_highest_risk(self) -> None:
        config = {
            "risk_level_by_category": {"security": "high"},
            "protected_paths": [
                {
                    "pattern": "schemas/**",
                    "risk": "critical",
                    "reason": "contract",
                    "owner_review": True,
                }
            ],
        }
        paths = ["schemas/api.json", "src/auth/session.py"]
        risks = classify_risks(paths)
        matches = match_protected_paths(paths, config)

        self.assertEqual(matches[0]["path"], "schemas/api.json")
        self.assertEqual(score_risk(risks, matches, config), "critical")


class LocalizationTest(unittest.TestCase):
    def test_resolves_chinese_alias(self) -> None:
        self.assertEqual(resolve_language("zh"), "zh-CN")

    def test_render_digest_in_chinese(self) -> None:
        digest = render_digest(
            "origin/main",
            "HEAD",
            [{"status": "A", "path": "schemas/api.json"}],
            ["abc123 Add API"],
            "zh-CN",
        )

        self.assertIn("# 分支消化报告", digest)
        self.assertIn("## 变更文件", digest)
        self.assertIn("**共享契约**", digest)


class ConfigValidationTest(unittest.TestCase):
    def test_accepts_minimal_config(self) -> None:
        ok, errors = validate_config_data(
            {
                "language": "zh-CN",
                "protected_paths": [{"pattern": "schemas/**", "risk": "high"}],
            }
        )

        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_rejects_invalid_risk_level(self) -> None:
        ok, errors = validate_config_data(
            {"protected_paths": [{"pattern": "schemas/**", "risk": "severe"}]}
        )

        self.assertFalse(ok)
        self.assertTrue(any("risk" in error for error in errors))

    def test_rejects_unknown_config_key(self) -> None:
        ok, errors = validate_config_data({"unknown": True})

        self.assertFalse(ok)
        self.assertIn("unknown config key: unknown", errors)


class ManifestValidationTest(unittest.TestCase):
    def test_accepts_minimal_valid_manifest(self) -> None:
        payload = {
            "task": "Add login API",
            "intent": "Allow users to sign in",
            "scope": "backend",
            "core_changes": [],
            "contracts": [],
            "tests": [],
            "risks": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            ok, errors = validate_manifest(path)

        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_rejects_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text("{}", encoding="utf-8")

            ok, errors = validate_manifest(path)

        self.assertFalse(ok)
        self.assertIn("missing required field: task", errors)


class AgentsFileValidationTest(unittest.TestCase):
    def test_accepts_minimal_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(
                "# AGENTS.md\n\n## Validation\n\n```bash\npython -m unittest\n```\n",
                encoding="utf-8",
            )

            ok, errors = validate_agents_file(path)

        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_rejects_live_state_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(
                "# AGENTS.md\n\n## Open Decisions\n\n- decide auth\n",
                encoding="utf-8",
            )

            ok, errors = validate_agents_file(path)

        self.assertFalse(ok)
        self.assertTrue(any("open decisions" in error for error in errors))

    def test_rejects_agents_file_over_max_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text("\n".join(["line"] * 4), encoding="utf-8")

            ok, errors = validate_agents_file(path, max_lines=3)

        self.assertFalse(ok)
        self.assertTrue(any("too long" in error for error in errors))


class HeartbeatTest(unittest.TestCase):
    def test_new_heartbeat_shape(self) -> None:
        heartbeat = new_heartbeat("agent-a", "Implement digest")

        self.assertEqual(heartbeat["agent"], "agent-a")
        self.assertEqual(heartbeat["status"], "working")
        self.assertEqual(heartbeat["currently_editing"], [])


class ManagerPrototypeTest(unittest.TestCase):
    def test_patterns_overlap_for_parent_glob_and_child_path(self) -> None:
        self.assertTrue(patterns_overlap("src/api/**", "src/api/auth.py"))
        self.assertFalse(patterns_overlap("src/api/**", "docs/**"))

    def test_find_lease_conflicts(self) -> None:
        existing = new_lease("agent-a", "path", ["src/api/**"], "API work")
        requested = new_lease("agent-b", "path", ["src/api/auth.py"], "Auth work")

        conflicts = find_lease_conflicts(requested, {existing["id"]: existing})

        self.assertEqual(conflicts[0]["holder"], "agent-a")

    def test_manager_cli_creates_decision_for_overlapping_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = str(Path(tmp) / ".coprogrammer")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                first = main(
                    [
                        "manager",
                        "lease",
                        "request",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                        "--holder",
                        "agent-a",
                        "--pattern",
                        "src/api/**",
                    ]
                )
                second = main(
                    [
                        "manager",
                        "lease",
                        "request",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                        "--holder",
                        "agent-b",
                        "--pattern",
                        "src/api/auth.py",
                    ]
                )

            events = load_events(Path(state_dir) / "events.jsonl")
            event_types = [event["type"] for event in events]

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)
        self.assertIn("lease.granted", event_types)
        self.assertIn("decision.requested", event_types)

    def test_manager_cli_records_decision_and_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = str(Path(tmp) / ".coprogrammer")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(
                    [
                        "manager",
                        "lease",
                        "request",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                        "--holder",
                        "agent-a",
                        "--pattern",
                        "src/api/**",
                    ]
                )
                main(
                    [
                        "manager",
                        "lease",
                        "request",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                        "--holder",
                        "agent-b",
                        "--pattern",
                        "src/api/auth.py",
                    ]
                )

            events = load_events(Path(state_dir) / "events.jsonl")
            decision_id = next(
                event["payload"]["decision"]["id"]
                for event in events
                if event["type"] == "decision.requested"
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                recorded = main(
                    [
                        "manager",
                        "decision",
                        "record",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                        "--id",
                        decision_id,
                        "--decision",
                        "serialize agent-b after agent-a",
                        "--decider",
                        "maintainer",
                    ]
                )
                status = main(
                    [
                        "manager",
                        "status",
                        "--cwd",
                        tmp,
                        "--state-dir",
                        state_dir,
                    ]
                )

            events = load_events(Path(state_dir) / "events.jsonl")
            event_types = [event["type"] for event in events]

        self.assertEqual(recorded, 0)
        self.assertEqual(status, 0)
        self.assertEqual(open_decisions(events), {})
        self.assertIn("decision.recorded", event_types)
        self.assertIn("open decisions: 0", output.getvalue())


class GitHubCommentTest(unittest.TestCase):
    def test_build_pr_comment_body_includes_marker_and_digest(self) -> None:
        body = build_pr_comment_body("# Branch Digest\n\ncontent", "<!-- marker -->")

        self.assertIn("<!-- marker -->", body)
        self.assertIn("# Branch Digest", body)
        self.assertIn("Generated by CoProgrammer", body)

    def test_build_pr_comment_body_truncates_large_digest(self) -> None:
        body = build_pr_comment_body("x" * 70000)

        self.assertLessEqual(len(body), 65000)
        self.assertIn("truncated", body)

    def test_build_pr_comment_body_in_chinese(self) -> None:
        body = build_pr_comment_body("# 分支消化报告", language="zh-CN")

        self.assertIn("CoProgrammer 分支消化报告", body)
        self.assertIn("由 CoProgrammer 生成", body)

    def test_load_pull_request_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(
                json.dumps({"pull_request": {"number": 42}}),
                encoding="utf-8",
            )

            number = load_pull_request_number(path)

        self.assertEqual(number, 42)


if __name__ == "__main__":
    unittest.main()
