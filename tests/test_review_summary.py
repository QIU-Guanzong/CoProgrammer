from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer.review import collect_evidence, create_review
from coprogrammer.review_summary import MAX_ARTIFACT_BYTES, build_summary, render_markdown


class ReviewSummaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Test Fixture")
        (self.root / "app.py").write_text("VALUE = 1\n")
        self.git("add", ".")
        self.git("commit", "-m", "baseline")
        self.git("checkout", "-b", "feature")
        (self.root / "app.py").write_text("VALUE = 2\n")
        self.git("add", ".")
        self.git("commit", "-m", "feature")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def advance(self, ref):
        sha = self.git("commit-tree", f"{ref}^{{tree}}", "-p", ref, "-m", "concurrent advance")
        self.git("update-ref", f"refs/heads/{ref}", sha)

    def artifact(self, *, decision="preserve", provider="glm", limit=64_000):
        evidence = collect_evidence(self.root, "main", "feature", limit)
        return {"format": "coprogrammer.review.v1", "status": "advisory",
                "provider": provider, "model": "declared-model", "network_used": True,
                "requires_human_review": True, "finish_reason": "stop", "evidence": evidence,
                "advice": {"summary": "Update value", "changes": [
                    {"path": item["path"], "decision": decision, "reason": "The diff changes value."}
                    for item in evidence["files"]], "risks": [], "validation": ["Check behavior"]}}

    def save(self, data, name="review.json"):
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def summary(self, reviews, expected=None, base="main", head="feature"):
        return build_summary(self.root, base, head, reviews, expected or [])

    def test_current_agreement_is_draft_without_approval_or_identity_claims(self):
        first = self.save(self.artifact(), "one.json")
        second = self.save(self.artifact(provider="deepseek"), "two.json")
        with patch("coprogrammer.providers.complete", side_effect=AssertionError("No network")) as complete:
            summary = self.summary({"codex": first, "claude": second})
        complete.assert_not_called()
        self.assertEqual(summary["format"], "coprogrammer.review-summary.v1")
        self.assertEqual(summary["status"], "draft")
        self.assertTrue(summary["requires_human_review"])
        self.assertEqual(summary["identity_verification"], "not_verified")
        self.assertEqual(summary["remote_freshness"], "not_checked")
        self.assertEqual(summary["counts"]["current"], 2)
        self.assertFalse(summary["attention_required"])
        self.assertFalse(summary["files"][0]["disagreement"])
        for field in ("approved", "merge_ready", "quorum", "quorum_passed"):
            self.assertNotIn(field, summary)

    def test_conflicting_substantive_decisions_are_visible(self):
        first = self.save(self.artifact(), "one.json")
        second = self.save(self.artifact(decision="rebuild"), "two.json")
        summary = self.summary({"a": first, "b": second})
        self.assertTrue(summary["attention_required"])
        self.assertEqual(summary["counts"]["disagreements"], 1)
        self.assertEqual({item["decision"] for item in summary["files"][0]["recommendations"]},
                         {"preserve", "rebuild"})

    def test_defer_is_coverage_gap_not_substantive_disagreement(self):
        first = self.save(self.artifact(), "one.json")
        second = self.save(self.artifact(decision="defer"), "two.json")
        summary = self.summary({"a": first, "b": second})
        self.assertTrue(summary["attention_required"])
        self.assertTrue(summary["files"][0]["coverage_gap"])
        self.assertFalse(summary["files"][0]["disagreement"])
        self.assertEqual(summary["counts"]["deferred_files"], 1)

    def test_expected_missing_prepared_invalid_do_not_contribute_advice(self):
        preview = create_review(self.root, "main", "feature", "glm", "declared-model")
        broken = self.root / "bad.json"
        broken.write_text("not json")
        summary = self.summary({"sent": self.save(self.artifact()),
                                "preview": self.save(preview, "preview.json"), "bad": broken,
                                "gone": self.root / "absent.json"}, ["absent", "sent"])
        states = {item["label"]: item["status"] for item in summary["reviewers"]}
        self.assertEqual(states, {"absent": "missing", "sent": "current", "preview": "prepared",
                                  "bad": "invalid", "gone": "missing"})
        self.assertEqual(summary["counts"]["total"], 5)
        self.assertEqual([item["reviewer"] for item in summary["files"][0]["recommendations"]], ["sent"])
        self.assertTrue(summary["attention_required"])

    def test_old_immutable_commits_are_stale_against_selected_target(self):
        for ref in ("main", "feature"):
            with self.subTest(ref=ref):
                artifact = self.artifact()
                artifact["evidence"]["base_ref"] = artifact["evidence"]["base_sha"]
                artifact["evidence"]["head_ref"] = artifact["evidence"]["head_sha"]
                path = self.save(artifact)
                self.advance(ref)  # Empty commit changes identity without changing the diff.
                summary = self.summary({"old": path})
                self.assertEqual(summary["reviewers"][0]["status"], "stale")
                self.assertEqual(summary["files"], [])
                pinned = self.summary({"old": path}, base=artifact["evidence"]["base_sha"],
                                      head=artifact["evidence"]["head_sha"])
                self.assertEqual(pinned["reviewers"][0]["status"], "current")

    def test_saved_reference_names_are_not_identity_when_target_sha_matches(self):
        artifact = self.artifact()
        artifact["evidence"]["base_ref"] = "deleted-old-main"
        artifact["evidence"]["head_ref"] = "deleted-old-feature"
        summary = self.summary({"named": self.save(artifact)})
        self.assertEqual(summary["reviewers"][0]["status"], "current")

    def test_reformatted_duplicate_artifact_is_counted_once(self):
        artifact = self.artifact()
        first = self.save(artifact, "first.json")
        second = self.root / "second.json"
        second.write_text(json.dumps(artifact, sort_keys=True, indent=4))
        summary = self.summary({"a": first, "b": second})
        self.assertEqual(summary["counts"]["current"], 1)
        self.assertEqual(summary["counts"]["duplicate"], 1)
        self.assertEqual(summary["reviewers"][1]["status"], "duplicate")
        self.assertEqual(summary["reviewers"][1]["duplicate_of"], "a")
        self.assertNotEqual(summary["reviewers"][0]["artifact_sha256"], summary["reviewers"][1]["artifact_sha256"])
        self.assertNotIn("risks", summary["reviewers"][1])
        self.assertEqual(len(summary["files"][0]["recommendations"]), 1)
        self.assertTrue(summary["attention_required"])

    def test_current_review_notes_are_preserved_and_risks_require_attention(self):
        artifact = self.artifact()
        artifact["advice"]["summary"] = "Value update needs caller review"
        artifact["advice"]["risks"] = ["Existing callers may assume the old value.", " "]
        artifact["advice"]["validation"] = ["Run caller compatibility checks."]
        summary = self.summary({"a": self.save(artifact)})
        reviewer = summary["reviewers"][0]
        for field in ("summary", "risks", "validation"):
            self.assertEqual(reviewer[field], artifact["advice"][field])
        self.assertTrue(summary["attention_required"])
        self.assertEqual(summary["counts"]["risk_notes"], 1)
        self.assertFalse(summary["files"][0]["disagreement"])
        rendered = render_markdown(summary, "en")
        self.assertIn("Value update needs caller review", rendered)
        self.assertIn("Existing callers may assume the old value", rendered)
        self.assertIn("Run caller compatibility checks", rendered)
        self.assertIn("not evidence that tests ran or passed", rendered)

    def test_raw_artifact_hash_matches_the_same_bytes_read_for_parsing(self):
        path = self.save(self.artifact())
        original = path.read_bytes()
        from coprogrammer import review_summary
        read_artifact = review_summary._read_artifact

        def read_then_replace(selected):
            result = read_artifact(selected)
            path.write_text("file replaced after reading")
            return result

        with patch("coprogrammer.review_summary._read_artifact", side_effect=read_then_replace):
            summary = self.summary({"a": path})
        self.assertEqual(summary["reviewers"][0]["status"], "current")
        self.assertEqual(summary["reviewers"][0]["artifact_sha256"], hashlib.sha256(original).hexdigest())
        invalid = self.root / "invalid-object.json"
        invalid.write_text("[]")
        row = self.summary({"invalid": invalid})["reviewers"][0]
        self.assertEqual(row["status"], "invalid")
        self.assertEqual(row["artifact_sha256"], hashlib.sha256(b"[]").hexdigest())

    def test_empty_advisory_evidence_is_invalid_even_on_matching_target(self):
        artifact = self.artifact()
        artifact["evidence"] = collect_evidence(self.root, "main", "main")
        artifact["advice"]["changes"] = []
        summary = self.summary({"a": self.save(artifact)}, base="main", head="main")
        self.assertEqual(summary["reviewers"][0]["status"], "invalid")
        self.assertEqual(summary["files"], [])

    def test_incomplete_advisory_metadata_is_invalid(self):
        for field, value in (("provider", ""), ("model", " "), ("network_used", 1),
                             ("requires_human_review", 1), ("finish_reason", "length"),
                             ("status", "approved")):
            with self.subTest(field=field):
                artifact = self.artifact()
                artifact[field] = value
                summary = self.summary({"a": self.save(artifact)})
                self.assertEqual(summary["reviewers"][0]["status"], "invalid")
                self.assertEqual(summary["files"], [])

    def test_tampered_evidence_fields_are_invalid_even_with_original_hash(self):
        original = self.artifact()
        for field, value in (("diff", "invented diff"), ("diff_bytes", 1),
                             ("diff_truncated", 0), ("coverage", "partial"),
                             ("files", []), ("excluded_paths", ["app.py"]),
                             ("merge_base_sha", original["evidence"]["head_sha"]),
                             ("diff_sha256", "0" * 64)):
            with self.subTest(field=field):
                artifact = copy.deepcopy(original)
                artifact["evidence"][field] = value
                summary = self.summary({"a": self.save(artifact)})
                self.assertEqual(summary["reviewers"][0]["status"], "invalid")
                self.assertEqual(summary["files"], [])

    def test_invented_or_duplicate_file_recommendations_are_invalid(self):
        for kind in ("invented", "duplicate"):
            with self.subTest(kind=kind):
                artifact = self.artifact()
                change = artifact["advice"]["changes"][0]
                if kind == "invented":
                    change["path"] = "missing.py"
                else:
                    artifact["advice"]["changes"].append(copy.deepcopy(change))
                self.assertEqual(self.summary({"a": self.save(artifact)})["reviewers"][0]["status"], "invalid")

    def test_omitted_decisions_are_deferred(self):
        artifact = self.artifact()
        artifact["advice"]["changes"] = []
        summary = self.summary({"a": self.save(artifact)})
        self.assertEqual(summary["reviewers"][0]["status"], "current")
        self.assertEqual(summary["files"][0]["recommendations"][0]["decision"], "defer")
        self.assertTrue(summary["attention_required"])

    def test_truncated_input_is_current_but_partial_with_deferred_decisions(self):
        (self.root / "large.txt").write_text("content line\n" * 500)
        self.git("add", "large.txt")
        self.git("commit", "-m", "large change")
        partial = self.save(self.artifact(limit=1024), "partial.json")
        full = self.save(self.artifact(), "full.json")
        summary = self.summary({"partial": partial, "full": full})
        self.assertEqual(summary["counts"]["current"], 2)
        self.assertEqual(summary["counts"]["partial"], 1)
        self.assertTrue(all(not row["disagreement"] and row["coverage_gap"] for row in summary["files"]))
        self.assertTrue(all(row["recommendations"][0]["decision"] == "defer" for row in summary["files"]))

    def test_sensitive_exclusions_remain_partial_and_are_not_echoed(self):
        (self.root / ".env").write_text("SECRET=fixture-secret-value\n")
        self.git("add", ".env")
        self.git("commit", "-m", "sensitive fixture")
        summary = self.summary({"a": self.save(self.artifact())})
        self.assertEqual(summary["counts"]["partial"], 1)
        sensitive = next(row for row in summary["files"] if row["path"] == ".env")
        self.assertEqual(sensitive["recommendations"][0]["decision"], "defer")
        self.assertNotIn("fixture-secret-value", json.dumps(summary))

    def test_bad_json_inputs_are_isolated_without_provider_calls(self):
        good = self.save(self.artifact(), "good.json")
        variants = ["{", "[]", '{"x":1,"x":2}', '{"x":{"a":1,"a":2}}',
                    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}',
                    '{"x":' + '[' * 1100 + '0' + ']' * 1100 + '}',
                    '{"x":' + '[' * 70 + '0' + ']' * 70 + '}', '{"x":"\\ud800"}']
        for index, raw in enumerate(variants):
            with self.subTest(index=index):
                bad = self.root / "bad.json"
                bad.write_text(raw)
                with patch("coprogrammer.providers.complete", side_effect=AssertionError("No network")):
                    summary = self.summary({"bad": bad, "good": good})
                self.assertEqual([item["status"] for item in summary["reviewers"]], ["invalid", "current"])

    def test_oversized_and_non_file_inputs_are_invalid(self):
        oversized = self.root / "large.json"
        oversized.write_bytes(b" " * (MAX_ARTIFACT_BYTES + 1))
        summary = self.summary({"large": oversized, "directory": self.root})
        self.assertTrue(all(item["status"] == "invalid" for item in summary["reviewers"]))

    def test_labels_limits_and_empty_participant_list(self):
        for reviews, expected in (({}, []), ({}, ["bad label"]), ({}, ["_first"]),
                                  ({}, ["中"]), ({}, ["a" * 65]), ({}, [None]),
                                  ({}, [f"a{i}" for i in range(17)])):
            with self.subTest(expected=expected):
                with self.assertRaises(RuntimeError):
                    self.summary(reviews, expected)
        summary = self.summary({}, ["a.b-c_0", "a.b-c_0"])
        self.assertEqual(summary["counts"]["total"], 1)
        summary = self.summary({}, [f"a{i}" for i in range(16)])
        self.assertEqual(summary["counts"]["missing"], 16)

    def test_selected_refs_moving_during_collection_abort_summary(self):
        for ref in ("main", "feature"):
            with self.subTest(ref=ref):
                path = self.save(self.artifact())

                def collect_and_advance(*args, **kwargs):
                    evidence = collect_evidence(*args, **kwargs)
                    self.advance(ref)
                    return evidence

                with patch("coprogrammer.review_summary.collect_evidence", side_effect=collect_and_advance):
                    with self.assertRaisesRegex(RuntimeError, "Summary is stale"):
                        self.summary({"a": path})

    def test_relative_artifact_paths_are_relative_to_cwd(self):
        self.save(self.artifact())
        summary = self.summary({"a": Path("review.json")})
        self.assertEqual(summary["reviewers"][0]["status"], "current")

    def test_model_text_is_literal_in_markdown_and_never_executed(self):
        artifact = self.artifact()
        malicious = '<img src="x"> ![track](https://example.invalid/x) | next\n# heading `touch SHOULD_NOT_EXIST` [link](https://example.invalid)'
        artifact["advice"]["changes"][0]["reason"] = malicious
        artifact["advice"]["summary"] = malicious
        artifact["advice"]["risks"] = [malicious]
        artifact["advice"]["validation"] = [malicious]
        summary = self.summary({"a": self.save(artifact)})
        for language in ("en", "zh-CN"):
            rendered = render_markdown(summary, language)
            self.assertNotIn('<img src=', rendered)
            self.assertNotIn('![track](', rendered)
            self.assertNotIn('[link](', rendered)
            self.assertNotIn('\n# heading', rendered)
            self.assertIn(r'\| next', rendered)
            self.assertIn('&lt;img', rendered)
            self.assertIn(r'\`touch SHOULD\_NOT\_EXIST\`', rendered)
            self.assertIn('draft' if language == 'en' else '待人工审核', rendered)
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())
        with self.assertRaises(RuntimeError):
            render_markdown(summary, "unsupported")

    def test_missing_only_summary_has_no_recommendations(self):
        summary = self.summary({}, ["waiting"])
        self.assertEqual(summary["files"], [])
        self.assertTrue(summary["attention_required"])
        self.assertIn("No recommendations", render_markdown(summary, "en"))


if __name__ == "__main__":
    unittest.main()
