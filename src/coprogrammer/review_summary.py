"""Offline comparison of declared review artifacts against one committed target."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path
from typing import Any

from .review import _commit, collect_evidence, validate_advice


MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_REVIEWERS = 16
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
STATES = ("current", "stale", "prepared", "missing", "invalid", "duplicate")
EVIDENCE_FIELDS = (
    "base_sha", "head_sha", "merge_base_sha", "files", "excluded_paths",
    "diff", "diff_bytes", "diff_sha256", "diff_truncated", "coverage",
)


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are not supported")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON numbers are not supported")
    return number


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not supported")
        result[key] = value
    return result


def _read_artifact(path: Path) -> tuple[Any, str]:
    if not path.is_file():
        raise ValueError("Artifact must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact exceeds the 2 MiB limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant, parse_float=_finite_float)
    return data, hashlib.sha256(raw).hexdigest()


def _validate_json_tree(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Artifact must be a JSON object")
    # Bound nested data before canonicalization or any later recursive encoder.
    pending = [(data, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 64:
            raise ValueError("Artifact nesting exceeds the supported depth")
        if isinstance(value, dict):
            for key, item in value.items():
                key.encode("utf-8")
                pending.append((item, depth + 1))
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, str):
            value.encode("utf-8")


def _validate_evidence_shape(evidence: Any) -> None:
    if not isinstance(evidence, dict):
        raise ValueError("Review evidence is missing")
    for key in ("base_sha", "head_sha", "merge_base_sha"):
        if not isinstance(evidence.get(key), str) or not SHA.fullmatch(evidence[key]):
            raise ValueError("Review must bind full commit IDs")
    for key in ("base_ref", "head_ref"):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            raise ValueError("Review reference metadata is missing")
    if (type(evidence.get("diff_bytes")) is not int
            or not 0 <= evidence["diff_bytes"] <= 1_000_000
            or type(evidence.get("diff_truncated")) is not bool
            or not isinstance(evidence.get("diff"), str)
            or not isinstance(evidence.get("diff_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["diff_sha256"])
            or evidence.get("coverage") not in ("partial", "collected")):
        raise ValueError("Review diff metadata is invalid")
    if (not isinstance(evidence.get("files"), list)
            or not isinstance(evidence.get("excluded_paths"), list)
            or any(not isinstance(path, str) for path in evidence["excluded_paths"])):
        raise ValueError("Review file metadata is invalid")
    seen = set()
    for item in evidence["files"]:
        if (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                or not item["path"] or item["path"] in seen
                or not isinstance(item.get("status"), str) or not item["status"]):
            raise ValueError("Review file metadata is invalid")
        seen.add(item["path"])


def _inspect(data: dict[str, Any], cwd: Path, target: dict[str, str]) -> tuple[dict, dict | None]:
    if data.get("format") != "coprogrammer.review.v1":
        raise ValueError("Unsupported review format")
    for field in ("provider", "model"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError("Review provider and model declarations are required")
    if data.get("requires_human_review") is not True:
        raise ValueError("Review must retain human review requirements")
    evidence = data.get("evidence")
    _validate_evidence_shape(evidence)
    metadata = {"provider": data["provider"], "model": data["model"]}
    if data.get("status") == "prepared":
        if data.get("network_used") is not False:
            raise ValueError("Prepared review must be an unsent request preview")
        return {**metadata, "status": "prepared", "reason": "Request preview; no completed review."}, None
    if (data.get("status") != "advisory" or data.get("network_used") is not True
            or data.get("finish_reason") not in ("stop", "end_turn", "stop_sequence")):
        raise ValueError("A normally completed advisory review is required")
    if not evidence["files"]:
        raise ValueError("An advisory review must contain committed changes")
    if any(evidence[key] != target[key] for key in ("base_sha", "head_sha")):
        return {**metadata, "status": "stale", "reason": "Review commits differ from the selected target."}, None
    fresh = collect_evidence(cwd, target["base_sha"], target["head_sha"],
                             max(1024, evidence["diff_bytes"]))
    for key in EVIDENCE_FIELDS:
        # Typed JSON comparison also rejects booleans used as integer fields.
        if json.dumps(fresh[key], sort_keys=True) != json.dumps(evidence.get(key), sort_keys=True):
            raise ValueError("Review evidence does not match the selected commits")
    advice = validate_advice(json.dumps(data.get("advice")), fresh)
    return {**metadata, "status": "current", "coverage": fresh["coverage"],
            "reason": "Evidence matches the selected committed target."}, advice


def build_summary(cwd: Path, base: str, head: str, reviews: dict[str, Path],
                  expected: list[str]) -> dict[str, Any]:
    """Compare local artifacts without calling providers or approving their advice."""
    if not isinstance(reviews, dict) or not isinstance(expected, list):
        raise RuntimeError("Reviews must be a label-to-path mapping and expected must be a list")
    labels = [*expected, *reviews]
    if any(not isinstance(label, str) or not LABEL.fullmatch(label) for label in labels):
        raise RuntimeError("Reviewer labels must use 1-64 ASCII letters, digits, dot, underscore or hyphen; start alphanumeric")
    labels = list(dict.fromkeys(labels))
    if not labels or len(labels) > MAX_REVIEWERS:
        raise RuntimeError("A summary requires between 1 and 16 unique reviewer labels")
    cwd = Path(cwd)
    target = {"base_ref": base, "head_ref": head,
              "base_sha": _commit(cwd, base), "head_sha": _commit(cwd, head)}
    reviewers, accepted = [], []
    fingerprints: dict[str, str] = {}
    for label in labels:
        item: dict[str, Any] = {"label": label}
        advice = None
        if label not in reviews:
            item.update(status="missing", reason="Expected review artifact was not supplied.")
        else:
            try:
                path = Path(reviews[label])
                if not path.is_absolute():
                    path = cwd / path
                item["artifact_path"] = str(path)
                if not path.exists():
                    raise FileNotFoundError
                data, item["artifact_sha256"] = _read_artifact(path)
                _validate_json_tree(data)
                metadata, advice = _inspect(data, cwd, target)
                item.update(metadata)
                canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
                fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if fingerprint in fingerprints:
                    item.update(status="duplicate", duplicate_of=fingerprints[fingerprint],
                                reason="Identical artifact supplied under another declared label.")
                    advice = None
                else:
                    fingerprints[fingerprint] = label
            except FileNotFoundError:
                item.update(status="missing", reason="Review artifact file is missing.")
            except (OSError, ValueError, TypeError, RecursionError, RuntimeError):
                # Parser/Git messages can contain untrusted values or host paths.
                item.update(status="invalid", reason="Artifact could not be read or failed format, completion or evidence validation.")
                advice = None
        reviewers.append(item)
        if item["status"] == "current" and advice is not None:
            item.update(summary=advice["summary"], risks=advice["risks"],
                        validation=advice["validation"])
            accepted.append((label, advice))
    for ref_key, sha_key in (("base_ref", "base_sha"), ("head_ref", "head_sha")):
        if _commit(cwd, target[ref_key]) != target[sha_key]:
            raise RuntimeError("Summary is stale: selected base or head changed during verification; rerun the summary")
    matrix: dict[str, list[dict[str, str]]] = {}
    for label, advice in accepted:
        for change in advice["changes"]:
            matrix.setdefault(change["path"], []).append({"reviewer": label, **change})
    files = []
    for path, recommendations in sorted(matrix.items()):
        decisions = {item["decision"] for item in recommendations}
        files.append({"path": path,
                      "recommendations": [{key: value for key, value in item.items() if key != "path"}
                                          for item in recommendations],
                      "disagreement": len(decisions - {"defer"}) > 1,
                      "coverage_gap": "defer" in decisions or len(recommendations) < len(labels)})
    counts = {"total": len(reviewers), **{state: sum(item["status"] == state for item in reviewers)
                                        for state in STATES}}
    counts.update(partial=sum(item["status"] == "current" and item.get("coverage") == "partial"
                              for item in reviewers),
                  deferred_files=sum(any(item["decision"] == "defer" for item in row["recommendations"])
                                     for row in files),
                  disagreements=sum(row["disagreement"] for row in files),
                  risk_notes=sum(bool(risk.strip()) for item in reviewers
                                 if item["status"] == "current" for risk in item["risks"]))
    return {"format": "coprogrammer.review-summary.v1", "status": "draft",
            "requires_human_review": True, "identity_verification": "not_verified",
            "remote_freshness": "not_checked",
            "scope": "Committed changes only; local artifact declarations do not verify reviewer identity, independence or remote PR freshness.",
            "target": target, "reviewers": reviewers, "files": files, "counts": counts,
            "attention_required": (counts["current"] != counts["total"] or counts["partial"] > 0
                                   or counts["deferred_files"] > 0 or counts["disagreements"] > 0
                                   or counts["risk_notes"] > 0)}


def _literal(value: Any) -> str:
    text = str(value)
    text = " ".join(text.splitlines())
    text = "".join(char for char in text if ord(char) >= 32 and ord(char) != 127)
    # Neutralize Markdown, HTML, autolinks and table separators in model text.
    text = re.sub(r"([\\`*_{}\[\]()#+.!|:>~-])", r"\\\1", text)
    return html.escape(text, quote=True)


def render_markdown(summary: dict[str, Any], language: str = "zh-CN") -> str:
    if language not in ("en", "zh-CN"):
        raise RuntimeError("language must be en or zh-CN")
    chinese = language == "zh-CN"
    title = "离线审核汇总（待人工审核）" if chinese else "Offline review summary (draft)"
    caveat = ("身份及审核独立性未经验证；仅覆盖选定的已提交内容，未检查远端 PR 状态。"
              if chinese else "Reviewer identity and independence are unverified. This covers selected committed content only; remote PR freshness was not checked.")
    target = summary["target"]
    lines = [f"# {title}", "", caveat, "",
             f"Base: {_literal(target['base_ref'])} ({_literal(target['base_sha'])})",
             f"Head: {_literal(target['head_ref'])} ({_literal(target['head_sha'])})", "",
             ("需要处理未完成审核、覆盖缺口、风险或建议分歧。" if chinese else "Review gaps, risks or disagreements require attention.")
             if summary["attention_required"] else
             ("未发现汇总缺口；仍需人工审核。" if chinese else "No summary gaps detected; human review is still required."), "",
             "## 审核工件" if chinese else "## Review artifacts", "",
             "| Label | Status | Provider / model | Coverage | Notes |",
             "| --- | --- | --- | --- | --- |"]
    for reviewer in summary["reviewers"]:
        notes = reviewer["reason"]
        if reviewer.get("duplicate_of"):
            notes += " Duplicate of: " + reviewer["duplicate_of"]
        values = (reviewer["label"], reviewer["status"],
                  f"{reviewer.get('provider', '')} / {reviewer.get('model', '')}",
                  reviewer.get("coverage", ""), notes)
        lines.append("| " + " | ".join(_literal(value) for value in values) + " |")
    current = [item for item in summary["reviewers"] if item["status"] == "current"]
    if current:
        lines.extend(["", "## 审核说明" if chinese else "## Review notes", "",
                      "以下风险和待执行检查来自审核建议，不表示测试已运行或通过。" if chinese else
                      "Risks and planned checks below are review recommendations, not evidence that tests ran or passed."])
        for reviewer in current:
            lines.extend(["", "### " + _literal(reviewer["label"]), "", _literal(reviewer["summary"])])
            for risk in reviewer["risks"]:
                if risk.strip():
                    lines.append("- " + ("风险：" if chinese else "Risk: ") + _literal(risk))
            for check in reviewer["validation"]:
                if check.strip():
                    lines.append("- " + ("待执行检查：" if chinese else "Planned check: ") + _literal(check))
    lines.extend(["", "## 文件建议" if chinese else "## File recommendations", "",
                  "| File | Reviewer | Decision | Reason | Disagreement | Coverage gap |",
                  "| --- | --- | --- | --- | --- | --- |"])
    for row in summary["files"]:
        for recommendation in row["recommendations"]:
            values = (row["path"], recommendation["reviewer"], recommendation["decision"],
                      recommendation["reason"], str(row["disagreement"]).lower(),
                      str(row["coverage_gap"]).lower())
            lines.append("| " + " | ".join(_literal(value) for value in values) + " |")
    if not summary["files"]:
        lines.extend(["", "暂无通过当前目标验证的建议。" if chinese else "No recommendations verified against the selected target."])
    return "\n".join(lines) + "\n"
