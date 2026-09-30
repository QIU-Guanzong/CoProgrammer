from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer.review import collect_evidence, create_review, integration_plan, validate_advice


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Test Fixture")
        (self.root / "src").mkdir()
        (self.root / "src/app.py").write_text("VALUE = 1\n")
        (self.root / ".coprogrammer.json").write_text(json.dumps({
            "protected_paths": [{"pattern": "src/**", "risk": "high", "owner_review": True}]
        }))
        self.git("add", ".")
        self.git("commit", "-m", "baseline")
        self.git("checkout", "-b", "feature")
        (self.root / "src/app.py").write_text("VALUE = 2\n")
        self.git("add", ".")
        self.git("commit", "-m", "feature")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def advance_ref(self, ref):
        commit = self.git("commit-tree", f"{ref}^{{tree}}", "-p", ref,
                          "-m", "concurrent reference advance")
        self.git("update-ref", f"refs/heads/{ref}", commit)

    def advice(self, evidence, decision="preserve"):
        return {"summary": "Update value", "changes": [
            {"path": item["path"], "decision": decision, "reason": "Value diff is present."}
            for item in evidence["files"]], "risks": [], "validation": ["Verify value behavior"]}

    def artifact(self):
        evidence = collect_evidence(self.root, "main", "feature")
        return {"format": "coprogrammer.review.v1", "status": "advisory", "evidence": evidence,
                "created_at": "2026-09-26T00:00:00+00:00", "provider": "glm",
                "model": "explicit-model", "requires_human_review": True,
                "network_used": True, "finish_reason": "stop", "usage": None,
                "advice": self.advice(evidence)}

    def test_evidence_binds_commits_and_loads_root_policy_from_subdirectory(self):
        from coprogrammer import cli
        self.assertEqual(cli.load_config(self.root / "src"), cli.load_config(self.root))
        self.assertEqual(cli.load_config(self.root / "src", ".coprogrammer.json")["protected_paths"], [])
        evidence = collect_evidence(self.root / "src", "main", "feature")
        self.assertEqual(evidence["head_sha"], self.git("rev-parse", "feature"))
        self.assertIn("+VALUE = 2", evidence["diff"])
        self.assertEqual(evidence["protected_paths"][0]["path"], "src/app.py")

    def test_sensitive_content_and_uncommitted_data_are_excluded(self):
        (self.root / ".env.production").write_text("KEY=fixture-secret-value\n")
        self.git("add", ".env.production")
        self.git("commit", "-m", "sensitive fixture")
        (self.root / "src/app.py").write_text("UNCOMMITTED=fixture-draft\n")
        evidence = collect_evidence(self.root, "main", "feature")
        self.assertNotIn("fixture-secret-value", evidence["diff"])
        self.assertNotIn("fixture-draft", evidence["diff"])
        self.assertEqual(evidence["coverage"], "partial")
        advice = validate_advice(json.dumps(self.advice(evidence)), evidence)
        self.assertEqual(next(x for x in advice["changes"] if x["path"] == ".env.production")["decision"], "defer")

    def test_rename_sensitive_source_does_not_leak_content(self):
        self.git("checkout", "main")
        (self.root / ".env").write_text("SECRET=fixture-rename-secret\n" * 10)
        self.git("add", ".env")
        self.git("commit", "-m", "secret fixture")
        self.git("checkout", "-B", "feature", "main")
        self.git("mv", ".env", "config.txt")
        self.git("commit", "-m", "rename")
        evidence = collect_evidence(self.root, "main", "feature")
        self.assertEqual(evidence["files"][0]["old_path"], ".env")
        self.assertNotIn("fixture-rename-secret", evidence["diff"])

    @unittest.skipIf(os.name == "nt", "Windows forbids literal glob characters in filenames")
    def test_literal_glob_filename_does_not_select_sensitive_files(self):
        (self.root / "*").write_text("literal glob path")
        (self.root / ".env").write_text("fixture-glob-secret")
        self.git("add", ".")
        self.git("commit", "-m", "special paths")
        evidence = collect_evidence(self.root, "main", "feature")
        self.assertNotIn("fixture-glob-secret", evidence["diff"])

    def test_preview_never_calls_provider(self):
        with patch("coprogrammer.providers.complete") as complete:
            result = create_review(self.root, "main", "feature", "deepseek", "explicit-model")
        self.assertEqual(result["status"], "prepared")
        self.assertFalse(result["network_used"])
        complete.assert_not_called()

    def test_send_creates_advisory_and_usage(self):
        evidence = collect_evidence(self.root, "main", "feature")
        response = {"text": json.dumps(self.advice(evidence)), "usage": {"total_tokens": 10},
                    "truncated": False, "finish_reason": "stop"}
        with patch("coprogrammer.providers.complete", return_value=response) as complete:
            result = create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)
        complete.assert_called_once()
        self.assertEqual(result["status"], "advisory")
        self.assertTrue(result["requires_human_review"])
        self.assertNotIn("request", result)

    def test_reference_move_before_send_does_not_call_provider(self):
        for ref in ("main", "feature"):
            with self.subTest(ref=ref):
                def collect_and_advance(*args, **kwargs):
                    evidence = collect_evidence(*args, **kwargs)
                    self.advance_ref(ref)
                    return evidence

                with patch("coprogrammer.review.collect_evidence", side_effect=collect_and_advance), \
                        patch("coprogrammer.providers.complete") as complete:
                    with self.assertRaisesRegex(RuntimeError, "Review is stale"):
                        create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)
                complete.assert_not_called()

    def test_reference_move_during_send_rejects_advice_without_retry(self):
        for ref in ("main", "feature"):
            with self.subTest(ref=ref):
                evidence = collect_evidence(self.root, "main", "feature")

                def respond_after_advance(*args, **kwargs):
                    self.advance_ref(ref)
                    return {"text": json.dumps(self.advice(evidence)), "truncated": False,
                            "finish_reason": "stop"}

                with patch("coprogrammer.providers.complete", side_effect=respond_after_advance) as complete:
                    with self.assertRaisesRegex(RuntimeError, "Review is stale"):
                        create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)
                complete.assert_called_once()

    def test_fixed_commits_remain_reviewable_when_branches_advance(self):
        evidence = collect_evidence(self.root, "main", "feature")

        def respond_after_advance(*args, **kwargs):
            self.advance_ref("main")
            self.advance_ref("feature")
            return {"text": json.dumps(self.advice(evidence)), "truncated": False,
                    "finish_reason": "stop"}

        with patch("coprogrammer.providers.complete", side_effect=respond_after_advance) as complete:
            result = create_review(self.root, evidence["base_sha"], evidence["head_sha"],
                                   "glm", "explicit-model", send=True)
        complete.assert_called_once()
        self.assertEqual(result["status"], "advisory")
        self.assertEqual(result["evidence"]["base_sha"], evidence["base_sha"])
        self.assertEqual(result["evidence"]["head_sha"], evidence["head_sha"])

    def test_invented_files_rejected_and_omitted_decisions_deferred(self):
        evidence = collect_evidence(self.root, "main", "feature")
        data = self.advice(evidence)
        data["changes"][0]["path"] = "invented.py"
        with self.assertRaises(RuntimeError):
            validate_advice(json.dumps(data), evidence)
        data["changes"] = []
        result = validate_advice(json.dumps(data), evidence)
        self.assertEqual(result["changes"][0]["decision"], "defer")

    def test_truncated_evidence_and_model_output_are_explicit(self):
        (self.root / "large.txt").write_text("evidence line\n" * 500)
        self.git("add", ".")
        self.git("commit", "-m", "large change")
        evidence = collect_evidence(self.root, "main", "feature", 1024)
        self.assertTrue(evidence["diff_truncated"])
        self.assertEqual(evidence["coverage"], "partial")
        advice = validate_advice(json.dumps(self.advice(evidence)), evidence)
        self.assertTrue(all(item["decision"] == "defer" for item in advice["changes"]))
        with patch("coprogrammer.providers.complete", return_value={"truncated": True}):
            with self.assertRaisesRegex(RuntimeError, "truncated"):
                create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)

    def test_abnormal_stop_reason_is_not_accepted(self):
        with patch("coprogrammer.providers.complete", return_value={"truncated": False, "finish_reason": "content_filter"}):
            with self.assertRaisesRegex(RuntimeError, "did not finish normally"):
                create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)

    def test_plan_is_draft_protected_and_never_executes_model_commands(self):
        artifact = self.artifact()
        artifact["advice"]["validation"] = ["touch SHOULD_NOT_EXIST"]
        plan = integration_plan(artifact, self.root)
        self.assertEqual(plan["status"], "draft")
        self.assertEqual(plan["protected_areas"], ["src/app.py"])
        self.assertEqual(plan["validation"][0]["command"], "")
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())

    def test_stale_or_tampered_review_cannot_create_plan(self):
        artifact = self.artifact()
        tampered = json.loads(json.dumps(artifact))
        tampered["evidence"]["files"] = []
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            integration_plan(tampered, self.root)
        self.git("commit", "--allow-empty", "-m", "head advanced")
        with self.assertRaisesRegex(RuntimeError, "stale"):
            integration_plan(artifact, self.root)

    def test_plan_rejects_tampered_diff_and_coverage_fields(self):
        artifact = self.artifact()
        mutations = (
            ("diff", "The saved body no longer matches its Git evidence hash."),
            ("diff_bytes", artifact["evidence"]["diff_bytes"] + 1),
            ("diff_truncated", True),
            ("coverage", "partial"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                tampered = json.loads(json.dumps(artifact))
                tampered["evidence"][field] = value
                with self.assertRaisesRegex(RuntimeError, "does not match"):
                    integration_plan(tampered, self.root)
        for field, value in (("diff", None), ("diff_bytes", True),
                             ("diff_truncated", 0), ("coverage", "complete")):
            with self.subTest(field=field, value=value):
                tampered = json.loads(json.dumps(artifact))
                tampered["evidence"][field] = value
                with self.assertRaisesRegex(RuntimeError, "invalid"):
                    integration_plan(tampered, self.root)
        for field in ("diff", "diff_bytes", "diff_truncated", "coverage"):
            with self.subTest(missing=field):
                tampered = json.loads(json.dumps(artifact))
                del tampered["evidence"][field]
                with self.assertRaisesRegex(RuntimeError, "invalid"):
                    integration_plan(tampered, self.root)

    def test_plan_rejects_incomplete_or_inconsistent_advisory_metadata(self):
        artifact = self.artifact()
        invalid_values = {
            "provider": (None, "", " ", 1),
            "model": (None, "", "\t", []),
            "requires_human_review": (None, False, 1, "true"),
            "network_used": (None, False, 1, "true"),
            "finish_reason": (None, "length", "content_filter", "refusal", []),
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    tampered = json.loads(json.dumps(artifact))
                    tampered[field] = value
                    with self.assertRaisesRegex(RuntimeError, "Advisory review"):
                        integration_plan(tampered, self.root)
            with self.subTest(missing=field):
                tampered = json.loads(json.dumps(artifact))
                del tampered[field]
                with self.assertRaisesRegex(RuntimeError, "Advisory review"):
                    integration_plan(tampered, self.root)

    def test_completed_review_creates_only_a_draft_plan_without_another_call(self):
        evidence = collect_evidence(self.root, "main", "feature")
        response = {"text": json.dumps(self.advice(evidence)), "truncated": False,
                    "finish_reason": "stop", "usage": {"total_tokens": 10}}
        with patch("coprogrammer.providers.complete", return_value=response) as complete:
            review = create_review(self.root, "main", "feature", "glm", "explicit-model", send=True)
            plan = integration_plan(review, self.root)
        complete.assert_called_once()
        self.assertEqual(plan["status"], "draft")
        self.assertTrue(plan["changes_to_rebuild"])
        self.assertIn("Maintainer must review every model recommendation before integration.",
                      plan["required_decisions"])
        self.assertNotIn("authenticated", plan)
        self.assertFalse(any(check["command"] for check in plan["validation"]))

    def test_partial_completed_review_remains_deferred_in_draft_plan(self):
        (self.root / "large.txt").write_text("evidence line\n" * 500)
        self.git("add", ".")
        self.git("commit", "-m", "large change")
        evidence = collect_evidence(self.root, "main", "feature", 1024)
        response = {"text": json.dumps(self.advice(evidence)), "truncated": False,
                    "finish_reason": "end_turn"}
        with patch("coprogrammer.providers.complete", return_value=response) as complete:
            review = create_review(self.root, "main", "feature", "anthropic", "explicit-model",
                                   send=True, max_diff_bytes=1024)
            plan = integration_plan(review, self.root)
        complete.assert_called_once()
        self.assertEqual(plan["status"], "draft")
        self.assertEqual(plan["patch_primitives"], [])
        self.assertEqual(plan["changes_to_rebuild"], [])
        self.assertIn("Evidence is incomplete; inspect omitted content before approval.",
                      plan["required_decisions"])

    def test_consistent_metadata_does_not_authenticate_declared_provider(self):
        artifact = self.artifact()
        artifact.update(provider="self-reported-provider", model="self-reported-model",
                        finish_reason="stop_sequence")
        with patch("coprogrammer.providers.complete") as complete:
            plan = integration_plan(artifact, self.root)
        complete.assert_not_called()
        self.assertEqual(plan["status"], "draft")
        self.assertIn("Maintainer must review every model recommendation before integration.",
                      plan["required_decisions"])
        self.assertNotIn("authenticated", plan)

    def test_reference_move_during_recollection_is_rejected(self):
        artifact = self.artifact()
        def collect_and_advance(*args, **kwargs):
            result = collect_evidence(*args, **kwargs)
            self.git("commit", "--allow-empty", "-m", "concurrent head advance")
            return result
        with patch("coprogrammer.review.collect_evidence", side_effect=collect_and_advance):
            with self.assertRaisesRegex(RuntimeError, "stale"):
                integration_plan(artifact, self.root)
