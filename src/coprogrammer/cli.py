from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


REQUIRED_MANIFEST_FIELDS = {
    "task",
    "intent",
    "scope",
    "core_changes",
    "contracts",
    "tests",
    "risks",
}
REQUIRED_INTEGRATION_PLAN_FIELDS = {
    "source_branch",
    "source_head",
    "main_base",
    "objective",
    "changes_to_rebuild",
    "changes_to_drop",
    "patch_primitives",
    "validation",
    "rollback_plan",
    "status",
}

DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_COMMENT_MARKER = "<!-- coprogrammer-branch-digest -->"
GITHUB_COMMENT_LIMIT = 65000
DEFAULT_LANGUAGE = "en"
DEFAULT_CONFIG_FILE = ".coprogrammer.json"
DEFAULT_MANAGER_DIR = ".coprogrammer"
DEFAULT_EVENT_LOG = "events.jsonl"
RISK_LEVELS = ("low", "medium", "high", "critical")
EVENT_TYPES = (
    "agent.heartbeat",
    "agent.blocked",
    "lease.requested",
    "lease.granted",
    "lease.released",
    "contract.change.proposed",
    "branch.digest.created",
    "decision.requested",
    "decision.recorded",
    "integration.plan.created",
    "integration.recorded",
)
LEASE_KINDS = ("path", "contract", "test_surface", "integration_branch")
DECISION_RECORD_STATUSES = ("decided", "deferred", "rejected", "superseded")
CONTRACT_KINDS = (
    "api",
    "schema",
    "database",
    "shared_type",
    "auth",
    "payment",
    "deployment",
    "config",
    "other",
)
CONTRACT_COMPATIBILITY = ("compatible", "breaking", "unknown")
AGENTS_FORBIDDEN_STATE_HEADINGS = {
    "# backlog",
    "## backlog",
    "# current tasks",
    "## current tasks",
    "# current status",
    "## current status",
    "# active leases",
    "## active leases",
    "# open decisions",
    "## open decisions",
    "# decision log",
    "## decision log",
}

RISK_PATTERNS: dict[str, tuple[str, ...]] = {
    "contract": (
        "schema",
        "schemas/",
        "openapi",
        "proto",
        "graphql",
        "shared",
        "types",
    ),
    "database": ("migration", "migrations/", "db/", "database"),
    "security": ("auth", "permission", "role", "payment", "secret", ".env"),
    "build": (
        "package-lock",
        "pnpm-lock",
        "yarn.lock",
        "poetry.lock",
        "pyproject.toml",
        "requirements",
    ),
    "architecture": ("architecture", "constitution", "config", "settings"),
}

DEFAULT_RISK_LEVEL_BY_CATEGORY = {
    "contract": "medium",
    "database": "high",
    "security": "high",
    "build": "medium",
    "architecture": "medium",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "language": DEFAULT_LANGUAGE,
    "risk_level_by_category": DEFAULT_RISK_LEVEL_BY_CATEGORY,
    "protected_paths": [],
}

LANGUAGE_ALIASES = {
    "en": "en",
    "en-US": "en",
    "zh": "zh-CN",
    "zh-CN": "zh-CN",
    "zh_CN": "zh-CN",
    "cn": "zh-CN",
}

RISK_LABELS = {
    "en": {
        "contract": "contract",
        "database": "database",
        "security": "security",
        "build": "build",
        "architecture": "architecture",
    },
    "zh-CN": {
        "contract": "共享契约",
        "database": "数据库",
        "security": "安全/权限",
        "build": "构建/依赖",
        "architecture": "架构",
    },
}

DIGEST_TEXT = {
    "en": {
        "title": "Branch Digest",
        "generated": "Generated",
        "branch_intent": "Branch Intent",
        "branch_intent_todo": "TODO: Describe the problem this branch is trying to solve.",
        "core_contribution": "Core Contribution",
        "core_contribution_todo": (
            "TODO: List the useful ideas, experiments, and implementation decisions "
            "worth preserving."
        ),
        "changed_files": "Changed Files",
        "no_changed_files": "- No changed files detected.",
        "commit_summary": "Commit Summary",
        "no_commits": "- No commits detected.",
        "signals": "Contract and Architecture Signals",
        "no_signals": "- No high-signal risk paths detected by the first-pass rules.",
        "risk_level": "Risk Level",
        "protected_paths": "Protected Path Matches",
        "no_protected_paths": "- No protected path matches detected.",
        "owner_review": "owner review required",
        "noise": "Noise / Non-Essential Changes",
        "noise_todo": (
            "TODO: Identify formatting churn, broad rewrites, temporary debugging, "
            "generated artifacts, or unrelated refactors."
        ),
        "integration_plan": "Integration Plan",
        "integration_plan_todo": (
            "TODO: Explain how to rebuild the smallest safe patch from latest main."
        ),
        "validation_needed": "Validation Needed",
        "validation_items": [
            "Formatter",
            "Linter",
            "Type check",
            "Unit tests",
            "Integration tests",
            "Contract tests",
            "Owner review for protected areas",
        ],
        "human_decisions": "Human Decisions",
        "human_decisions_todo": "TODO: List decisions that should not be delegated to an autonomous agent.",
    },
    "zh-CN": {
        "title": "分支消化报告",
        "generated": "生成时间",
        "branch_intent": "分支意图",
        "branch_intent_todo": "TODO: 说明这个分支要解决的问题。",
        "core_contribution": "核心贡献",
        "core_contribution_todo": "TODO: 列出值得保留的思路、实验结果和实现决策。",
        "changed_files": "变更文件",
        "no_changed_files": "- 未检测到变更文件。",
        "commit_summary": "提交摘要",
        "no_commits": "- 未检测到提交。",
        "signals": "契约与架构信号",
        "no_signals": "- 第一轮规则未检测到高信号风险路径。",
        "risk_level": "风险等级",
        "protected_paths": "受保护路径命中",
        "no_protected_paths": "- 未命中受保护路径。",
        "owner_review": "需要 owner review",
        "noise": "噪声 / 非必要变更",
        "noise_todo": "TODO: 标记格式化扰动、大范围重写、临时调试、生成物或无关重构。",
        "integration_plan": "融合计划",
        "integration_plan_todo": "TODO: 说明如何基于最新 main 重建最小安全补丁。",
        "validation_needed": "需要验证",
        "validation_items": [
            "格式化",
            "Lint 检查",
            "类型检查",
            "单元测试",
            "集成测试",
            "契约测试",
            "受保护区域 owner review",
        ],
        "human_decisions": "需要人工判断",
        "human_decisions_todo": "TODO: 列出不应交给自治 agent 决定的问题。",
    },
}

COMMENT_TEXT = {
    "en": {
        "title": "CoProgrammer Branch Digest",
        "footer": "Generated by CoProgrammer.",
        "truncated": "... truncated; see the workflow artifact for the full digest.",
    },
    "zh-CN": {
        "title": "CoProgrammer 分支消化报告",
        "footer": "由 CoProgrammer 生成。",
        "truncated": "... 内容已截断；完整报告请查看 workflow artifact。",
    },
}


def resolve_language(language: str | None = None) -> str:
    requested = language or os.environ.get("COPROGRAMMER_LANGUAGE") or DEFAULT_LANGUAGE
    resolved = LANGUAGE_ALIASES.get(requested)
    if not resolved:
        supported = ", ".join(sorted(set(LANGUAGE_ALIASES)))
        raise RuntimeError(f"unsupported language '{requested}'. Supported: {supported}")
    return resolved


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = {
        "language": DEFAULT_CONFIG["language"],
        "risk_level_by_category": dict(DEFAULT_RISK_LEVEL_BY_CATEGORY),
        "protected_paths": [],
    }
    if not config:
        return merged

    if "language" in config:
        merged["language"] = config["language"]
    if isinstance(config.get("risk_level_by_category"), dict):
        merged["risk_level_by_category"].update(config["risk_level_by_category"])
    if isinstance(config.get("protected_paths"), list):
        merged["protected_paths"] = config["protected_paths"]
    return merged


def load_config(cwd: Path, config_path: str | None = None) -> dict[str, Any]:
    path = Path(config_path or DEFAULT_CONFIG_FILE)
    if not path.is_absolute():
        path = cwd / path
    if not path.exists():
        return merge_config(None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid config JSON: {path}: {exc}") from exc
    ok, errors = validate_config_data(data)
    if not ok:
        joined = "; ".join(errors)
        raise RuntimeError(f"invalid config {path}: {joined}")
    return merge_config(data)


def validate_config_data(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    allowed_keys = {"$schema", "language", "risk_level_by_category", "protected_paths"}
    for key in data:
        if key not in allowed_keys:
            errors.append(f"unknown config key: {key}")

    language = data.get("language")
    if language is not None:
        try:
            resolve_language(str(language))
        except RuntimeError as exc:
            errors.append(str(exc))

    risk_level_by_category = data.get("risk_level_by_category", {})
    if risk_level_by_category and not isinstance(risk_level_by_category, dict):
        errors.append("risk_level_by_category must be an object")
    elif isinstance(risk_level_by_category, dict):
        for category, level in risk_level_by_category.items():
            if category not in RISK_PATTERNS:
                errors.append(f"unknown risk category: {category}")
            if level not in RISK_LEVELS:
                errors.append(f"invalid risk level for {category}: {level}")

    protected_paths = data.get("protected_paths", [])
    if not isinstance(protected_paths, list):
        errors.append("protected_paths must be an array")
    else:
        allowed_rule_keys = {"pattern", "risk", "reason", "owner_review"}
        for index, rule in enumerate(protected_paths):
            if not isinstance(rule, dict):
                errors.append(f"protected_paths[{index}] must be an object")
                continue
            for key in rule:
                if key not in allowed_rule_keys:
                    errors.append(f"protected_paths[{index}] has unknown key: {key}")
            if not isinstance(rule.get("pattern"), str) or not rule.get("pattern"):
                errors.append(f"protected_paths[{index}].pattern is required")
            level = rule.get("risk", "high")
            if level not in RISK_LEVELS:
                errors.append(f"protected_paths[{index}].risk must be one of {', '.join(RISK_LEVELS)}")
            if "owner_review" in rule and not isinstance(rule["owner_review"], bool):
                errors.append(f"protected_paths[{index}].owner_review must be a boolean")

    return not errors, errors


def validate_config(path: Path) -> tuple[bool, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"invalid JSON: {exc}"]
    except OSError as exc:
        return False, [str(exc)]
    return validate_config_data(data)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def get_changed_files(base: str, head: str, cwd: Path) -> list[dict[str, str]]:
    output = run_git(["diff", "--name-status", f"{base}...{head}"], cwd)
    return parse_name_status(output)


def get_working_tree_changed_files(base: str, cwd: Path) -> list[dict[str, str]]:
    output = run_git(["diff", "--name-status", base], cwd)
    files = parse_name_status(output)
    known_paths = {item["path"] for item in files}
    untracked = run_git(["ls-files", "--others", "--exclude-standard"], cwd)
    for path in untracked.splitlines():
        if path and path not in known_paths:
            files.append({"status": "A", "path": path})
    return files


def parse_name_status(output: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        path = parts[-1]
        files.append({"status": status, "path": path})
    return files


def get_commits(base: str, head: str, cwd: Path) -> list[str]:
    output = run_git(["log", "--oneline", f"{base}..{head}"], cwd)
    return [line for line in output.splitlines() if line.strip()]


def classify_risks(paths: list[str]) -> dict[str, list[str]]:
    risks: dict[str, list[str]] = {name: [] for name in RISK_PATTERNS}
    for path in paths:
        lowered = path.lower()
        for risk_name, patterns in RISK_PATTERNS.items():
            if any(pattern in lowered for pattern in patterns):
                risks[risk_name].append(path)
    return {name: sorted(set(matches)) for name, matches in risks.items() if matches}


def match_protected_paths(
    paths: list[str],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = merge_config(config)
    matches: list[dict[str, Any]] = []
    for path in paths:
        for rule in config["protected_paths"]:
            pattern = rule["pattern"]
            if fnmatch.fnmatch(path, pattern):
                matches.append(
                    {
                        "path": path,
                        "pattern": pattern,
                        "risk": rule.get("risk", "high"),
                        "reason": rule.get("reason", ""),
                        "owner_review": rule.get("owner_review", True),
                    }
                )
    return matches


def highest_risk_level(levels: list[str]) -> str:
    if not levels:
        return "low"
    return max(levels, key=RISK_LEVELS.index)


def score_risk(
    risks: dict[str, list[str]],
    protected_matches: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> str:
    config = merge_config(config)
    levels: list[str] = []
    for category, matches in risks.items():
        if matches:
            levels.append(config["risk_level_by_category"].get(category, "medium"))
    levels.extend(match["risk"] for match in protected_matches)
    return highest_risk_level(levels)


def render_digest(
    base: str,
    head: str,
    files: list[dict[str, str]],
    commits: list[str],
    language: str = DEFAULT_LANGUAGE,
    config: dict[str, Any] | None = None,
) -> str:
    language = resolve_language(language)
    config = merge_config(config)
    text = DIGEST_TEXT[language]
    paths = [item["path"] for item in files]
    risks = classify_risks(paths)
    protected_matches = match_protected_paths(paths, config)
    risk_level = score_risk(risks, protected_matches, config)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    changed_files = "\n".join(
        f"- `{item['status']}` `{item['path']}`" for item in files
    ) or text["no_changed_files"]
    commit_lines = "\n".join(f"- {commit}" for commit in commits) or text["no_commits"]

    if risks:
        risk_lines = []
        risk_labels = RISK_LABELS[language]
        for risk_name, matches in risks.items():
            risk_lines.append(f"- **{risk_labels[risk_name]}**")
            risk_lines.extend(f"  - `{path}`" for path in matches)
        risk_block = "\n".join(risk_lines)
    else:
        risk_block = text["no_signals"]

    if protected_matches:
        protected_lines = []
        for match in protected_matches:
            suffix = []
            if match["reason"]:
                suffix.append(match["reason"])
            if match["owner_review"]:
                suffix.append(text["owner_review"])
            detail = f" ({'; '.join(suffix)})" if suffix else ""
            protected_lines.append(
                f"- `{match['path']}` matches `{match['pattern']}` "
                f"[{match['risk']}]{detail}"
            )
        protected_block = "\n".join(protected_lines)
    else:
        protected_block = text["no_protected_paths"]

    validation_items = "\n".join(f"- [ ] {item}" for item in text["validation_items"])

    return f"""# {text["title"]}

{text["generated"]}: `{generated_at}`

Base: `{base}`
Head: `{head}`

## {text["branch_intent"]}

{text["branch_intent_todo"]}

## {text["core_contribution"]}

{text["core_contribution_todo"]}

## {text["changed_files"]}

{changed_files}

## {text["commit_summary"]}

{commit_lines}

## {text["signals"]}

{risk_block}

## {text["risk_level"]}

`{risk_level}`

## {text["protected_paths"]}

{protected_block}

## {text["noise"]}

{text["noise_todo"]}

## {text["integration_plan"]}

{text["integration_plan_todo"]}

## {text["validation_needed"]}

{validation_items}

## {text["human_decisions"]}

{text["human_decisions_todo"]}
"""


def validate_manifest(path: Path) -> tuple[bool, list[str]]:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"invalid JSON: {exc}"]
    except OSError as exc:
        return False, [str(exc)]

    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(payload))
    errors = [f"missing required field: {field}" for field in missing]

    if not isinstance(payload.get("core_changes", []), list):
        errors.append("core_changes must be a list")
    if not isinstance(payload.get("contracts", []), list):
        errors.append("contracts must be a list")
    if not isinstance(payload.get("tests", []), list):
        errors.append("tests must be a list")
    if not isinstance(payload.get("risks", []), list):
        errors.append("risks must be a list")

    return not errors, errors


def validate_integration_plan(path: Path) -> tuple[bool, list[str]]:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"invalid JSON: {exc}"]
    except OSError as exc:
        return False, [str(exc)]

    missing = sorted(REQUIRED_INTEGRATION_PLAN_FIELDS - set(payload))
    errors = [f"missing required field: {field}" for field in missing]

    for field in (
        "changes_to_rebuild",
        "changes_to_drop",
        "patch_primitives",
        "validation",
    ):
        if field in payload and not isinstance(payload[field], list):
            errors.append(f"{field} must be a list")

    if "rollback_plan" in payload and not isinstance(payload["rollback_plan"], str):
        errors.append("rollback_plan must be a string")

    status = payload.get("status")
    if status is not None and status not in {
        "draft",
        "approved",
        "applied",
        "superseded",
    }:
        errors.append("status must be one of draft, approved, applied, superseded")

    return not errors, errors


def validate_agents_file(path: Path, max_lines: int = 120) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return False, [str(exc)]

    if len(lines) > max_lines:
        errors.append(
            f"AGENTS.md is too long: {len(lines)} lines; expected <= {max_lines}"
        )

    headings = {
        line.strip().lower()
        for line in lines
        if line.lstrip().startswith("#")
    }
    forbidden = sorted(headings & AGENTS_FORBIDDEN_STATE_HEADINGS)
    for heading in forbidden:
        errors.append(
            f"AGENTS.md should not store live coordination state in heading: {heading}"
        )

    return not errors, errors


def new_heartbeat(agent: str, task: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "agent": agent,
        "task": task,
        "timestamp": now,
        "status": "working",
        "currently_editing": [],
        "next_step": "",
        "contracts_touched": [],
        "blockers": [],
        "insights": [],
    }


def manager_dir(cwd: Path, state_dir: str = DEFAULT_MANAGER_DIR) -> Path:
    path = Path(state_dir)
    if not path.is_absolute():
        path = cwd / path
    return path


def event_log_path(cwd: Path, state_dir: str = DEFAULT_MANAGER_DIR) -> Path:
    return manager_dir(cwd, state_dir) / DEFAULT_EVENT_LOG


def make_event(
    event_type: str,
    actor: str,
    subject: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid4().hex}",
        "type": event_type,
        "timestamp": utc_now(),
        "actor": actor,
        "subject": subject,
        "payload": payload or {},
    }


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid event log JSON at line {line_number}: {exc}"
                ) from exc
            if not isinstance(event, dict):
                raise RuntimeError(
                    f"invalid event log entry at line {line_number}: expected object"
                )
            events.append(event)
    return events


def pattern_static_prefix(pattern: str) -> str:
    magic_positions = [
        position
        for token in ("*", "?", "[")
        if (position := pattern.find(token)) != -1
    ]
    if not magic_positions:
        return pattern.rstrip("/")
    return pattern[: min(magic_positions)].rstrip("/")


def patterns_overlap(left: str, right: str) -> bool:
    if fnmatch.fnmatch(left, right) or fnmatch.fnmatch(right, left):
        return True

    left_prefix = pattern_static_prefix(left)
    right_prefix = pattern_static_prefix(right)
    if not left_prefix or not right_prefix:
        return False
    return (
        left_prefix == right_prefix
        or left_prefix.startswith(f"{right_prefix}/")
        or right_prefix.startswith(f"{left_prefix}/")
    )


def lease_scopes_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("kind") != right.get("kind"):
        return False
    for left_pattern in left.get("patterns", []):
        for right_pattern in right.get("patterns", []):
            if patterns_overlap(str(left_pattern), str(right_pattern)):
                return True
    return False


def active_leases(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    leases: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event.get("payload", {})
        if event.get("type") == "lease.granted":
            lease = payload.get("lease", {})
            lease_id = lease.get("id")
            if lease_id:
                leases[str(lease_id)] = lease
        elif event.get("type") == "lease.released":
            lease_id = payload.get("lease_id")
            if lease_id:
                leases.pop(str(lease_id), None)
    return leases


def open_decisions(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event.get("payload", {})
        if event.get("type") == "decision.requested":
            decision = payload.get("decision", {})
            decision_id = decision.get("id")
            if decision_id:
                decisions[str(decision_id)] = decision
        elif event.get("type") == "decision.recorded":
            decision_id = payload.get("decision_id")
            if decision_id:
                decisions.pop(str(decision_id), None)
    return decisions


def latest_heartbeats(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    heartbeats: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") != "agent.heartbeat":
            continue
        heartbeat = event.get("payload", {}).get("heartbeat", {})
        agent = heartbeat.get("agent") or event.get("actor")
        if agent:
            heartbeats[str(agent)] = heartbeat
    return heartbeats


def contract_changes(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") != "contract.change.proposed":
            continue
        change = event.get("payload", {}).get("contract_change", {})
        change_id = change.get("id")
        if change_id:
            changes[str(change_id)] = change
    return changes


def find_lease_conflicts(
    requested_lease: dict[str, Any],
    leases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    requested_scope = requested_lease.get("scope", {})
    for lease in leases.values():
        if lease_scopes_overlap(requested_scope, lease.get("scope", {})):
            conflicts.append(lease)
    return conflicts


def new_lease(
    holder: str,
    kind: str,
    patterns: list[str],
    task: str = "",
) -> dict[str, Any]:
    return {
        "id": f"lease_{uuid4().hex}",
        "holder": holder,
        "task": task,
        "scope": {"kind": kind, "patterns": patterns},
        "status": "requested",
        "created_at": utc_now(),
        "reason": "",
    }


def new_decision(
    question: str,
    context: str,
    related_artifacts: list[str] | None = None,
    risk: str = "medium",
) -> dict[str, Any]:
    return {
        "id": f"decision_{uuid4().hex}",
        "question": question,
        "context": context,
        "options": [],
        "decision": "",
        "decider": "",
        "status": "open",
        "risk": risk,
        "created_at": utc_now(),
        "related_artifacts": related_artifacts or [],
    }


def new_contract_change(
    proposer: str,
    kind: str,
    name: str,
    summary: str,
    compatibility: str = "unknown",
    affected_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"contract_{uuid4().hex}",
        "proposer": proposer,
        "kind": kind,
        "name": name,
        "summary": summary,
        "compatibility": compatibility,
        "status": "proposed",
        "created_at": utc_now(),
        "affected_artifacts": affected_artifacts or [],
    }


def build_pr_comment_body(
    digest: str,
    marker: str = DEFAULT_COMMENT_MARKER,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    language = resolve_language(language)
    text = COMMENT_TEXT[language]
    header = f"{marker}\n## {text['title']}\n\n"
    footer = f"\n\n_{text['footer']}_\n"
    truncation_notice = f"\n\n{text['truncated']}\n"
    budget = GITHUB_COMMENT_LIMIT - len(header) - len(footer) - len(truncation_notice)

    if len(digest) > budget:
        digest = digest[:budget].rstrip() + truncation_notice

    return header + digest + footer


def load_pull_request_number(event_path: Path) -> int:
    try:
        payload: dict[str, Any] = json.loads(event_path.read_text(encoding="utf-8"))
        return int(payload["pull_request"]["number"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("could not read pull request number from GitHub event") from exc


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "coprogrammer",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {body}") from exc

    if not text:
        return None
    return json.loads(text)


def upsert_pr_comment(
    repository: str,
    pull_number: int,
    token: str,
    body: str,
    marker: str = DEFAULT_COMMENT_MARKER,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> str:
    comments_url = f"{api_url}/repos/{repository}/issues/{pull_number}/comments?per_page=100"
    comments = github_request("GET", comments_url, token)
    for comment in comments:
        if marker in comment.get("body", ""):
            comment_url = f"{api_url}/repos/{repository}/issues/comments/{comment['id']}"
            github_request("PATCH", comment_url, token, {"body": body})
            return "updated"

    create_url = f"{api_url}/repos/{repository}/issues/{pull_number}/comments"
    github_request("POST", create_url, token, {"body": body})
    return "created"


def command_digest(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    config = load_config(cwd, args.config)
    language = args.language or config.get("language") or DEFAULT_LANGUAGE
    if args.working_tree:
        files = get_working_tree_changed_files(args.base, cwd)
        head = "WORKING_TREE"
    else:
        files = get_changed_files(args.base, args.head, cwd)
        head = args.head
    commits = get_commits(args.base, args.head, cwd)
    digest = render_digest(args.base, head, files, commits, language, config)
    if args.output:
        Path(args.output).write_text(digest, encoding="utf-8")
    else:
        print(digest)
    return 0


def command_config_validate(args: argparse.Namespace) -> int:
    ok, errors = validate_config(Path(args.file))
    if ok:
        print("config ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def command_github_comment(args: argparse.Namespace) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    if not repository:
        raise RuntimeError("GITHUB_REPOSITORY is required")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is required")

    digest = Path(args.file).read_text(encoding="utf-8")
    pull_number = load_pull_request_number(Path(event_path))
    body = build_pr_comment_body(digest, args.marker, args.language)
    result = upsert_pr_comment(
        repository=repository,
        pull_number=pull_number,
        token=token,
        body=body,
        marker=args.marker,
        api_url=args.api_url,
    )
    print(f"pull request comment {result}")
    return 0


def command_manifest_validate(args: argparse.Namespace) -> int:
    ok, errors = validate_manifest(Path(args.file))
    if ok:
        print("manifest ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def command_integration_plan_validate(args: argparse.Namespace) -> int:
    ok, errors = validate_integration_plan(Path(args.file))
    if ok:
        print("integration plan ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def command_agents_check(args: argparse.Namespace) -> int:
    ok, errors = validate_agents_file(Path(args.file), args.max_lines)
    if ok:
        print("agents ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def command_heartbeat_new(args: argparse.Namespace) -> int:
    heartbeat = new_heartbeat(args.agent, args.task)
    text = json.dumps(heartbeat, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def command_manager_init(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    print(f"manager initialized: {path}")
    return 0


def command_manager_event_append(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    payload: dict[str, Any] = {}
    if args.payload:
        try:
            payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid payload JSON: {exc}") from exc
    event = make_event(args.type, args.actor, args.subject, payload)
    append_event(event_log_path(cwd, args.state_dir), event)
    print(json.dumps(event, indent=2, ensure_ascii=False))
    return 0


def command_manager_heartbeat(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    heartbeat = new_heartbeat(args.agent, args.task)
    event = make_event(
        "agent.heartbeat",
        args.agent,
        args.subject,
        {"heartbeat": heartbeat},
    )
    append_event(event_log_path(cwd, args.state_dir), event)
    print(json.dumps(event, indent=2, ensure_ascii=False))
    return 0


def command_manager_lease_request(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    events = load_events(path)
    lease = new_lease(args.holder, args.kind, args.pattern, args.task)

    append_event(
        path,
        make_event(
            "lease.requested",
            args.holder,
            args.subject,
            {"lease": lease},
        ),
    )

    conflicts = find_lease_conflicts(lease, active_leases(events))
    if conflicts:
        decision = new_decision(
            question=(
                f"Should {args.holder} proceed with {', '.join(args.pattern)} "
                "despite active lease overlap?"
            ),
            context=json.dumps(
                {
                    "requested_lease": lease,
                    "conflicting_leases": conflicts,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            related_artifacts=[
                lease["id"],
                *[conflict["id"] for conflict in conflicts],
            ],
            risk="medium",
        )
        append_event(
            path,
            make_event(
                "decision.requested",
                "manager",
                args.subject,
                {"decision": decision},
            ),
        )
        print(f"conflict: {args.holder} overlaps active lease(s)")
        for conflict in conflicts:
            patterns = ", ".join(conflict.get("scope", {}).get("patterns", []))
            print(f"- {conflict['id']} held by {conflict['holder']}: {patterns}")
        print(f"decision requested: {decision['id']}")
        return 0

    lease["status"] = "active"
    append_event(
        path,
        make_event(
            "lease.granted",
            "manager",
            args.subject,
            {"lease": lease},
        ),
    )
    print(f"lease granted: {lease['id']}")
    return 0


def command_manager_lease_release(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    append_event(
        path,
        make_event(
            "lease.released",
            args.actor,
            args.subject,
            {"lease_id": args.id},
        ),
    )
    print(f"lease released: {args.id}")
    return 0


def command_manager_leases(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    leases = list(
        active_leases(load_events(event_log_path(cwd, args.state_dir))).values()
    )
    if args.json:
        print(json.dumps(leases, indent=2, ensure_ascii=False))
        return 0
    if not leases:
        print("no active leases")
        return 0
    for lease in leases:
        patterns = ", ".join(lease.get("scope", {}).get("patterns", []))
        print(
            f"{lease['id']} {lease['holder']} "
            f"{lease.get('scope', {}).get('kind')}: {patterns}"
        )
    return 0


def command_manager_decisions(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    decisions = list(
        open_decisions(load_events(event_log_path(cwd, args.state_dir))).values()
    )
    if args.json:
        print(json.dumps(decisions, indent=2, ensure_ascii=False))
        return 0
    if not decisions:
        print("no open decisions")
        return 0
    for decision in decisions:
        print(
            f"{decision['id']} [{decision.get('risk', 'unknown')}] "
            f"{decision['question']}"
        )
    return 0


def command_manager_contract_propose(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    change = new_contract_change(
        proposer=args.proposer,
        kind=args.kind,
        name=args.name,
        summary=args.summary,
        compatibility=args.compatibility,
        affected_artifacts=args.artifact,
    )
    append_event(
        path,
        make_event(
            "contract.change.proposed",
            args.proposer,
            args.subject,
            {"contract_change": change},
        ),
    )
    print(f"contract change proposed: {change['id']}")

    if args.compatibility == "breaking":
        decision = new_decision(
            question=f"Should breaking contract change proceed: {args.name}?",
            context=json.dumps(change, ensure_ascii=False, sort_keys=True),
            related_artifacts=[change["id"], *args.artifact],
            risk="high",
        )
        append_event(
            path,
            make_event(
                "decision.requested",
                "manager",
                args.subject,
                {"decision": decision},
            ),
        )
        print(f"decision requested: {decision['id']}")
    return 0


def command_manager_contracts(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    changes = list(
        contract_changes(load_events(event_log_path(cwd, args.state_dir))).values()
    )
    if args.kind:
        changes = [change for change in changes if change.get("kind") == args.kind]

    if args.json:
        print(json.dumps(changes, indent=2, ensure_ascii=False))
        return 0
    if not changes:
        print("no contract changes")
        return 0
    for change in changes:
        print(
            f"{change['id']} [{change.get('compatibility', 'unknown')}] "
            f"{change.get('kind')}: {change.get('name')}"
        )
    return 0


def command_manager_decision_record(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    events = load_events(path)
    decisions = open_decisions(events)
    if args.id not in decisions:
        raise RuntimeError(f"open decision not found: {args.id}")

    payload = {
        "decision_id": args.id,
        "decision": args.decision,
        "decider": args.decider,
        "status": args.status,
        "note": args.note,
        "recorded_at": utc_now(),
    }
    append_event(
        path,
        make_event(
            "decision.recorded",
            args.decider,
            args.subject,
            payload,
        ),
    )
    print(f"decision recorded: {args.id} [{args.status}]")
    return 0


def command_manager_status(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    events = load_events(event_log_path(cwd, args.state_dir))
    leases = list(active_leases(events).values())
    decisions = list(open_decisions(events).values())
    heartbeats = latest_heartbeats(events)
    status = {
        "event_count": len(events),
        "active_leases": leases,
        "open_decisions": decisions,
        "contract_changes": list(contract_changes(events).values()),
        "latest_heartbeats": heartbeats,
    }

    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    print(f"events: {len(events)}")
    print(f"active leases: {len(leases)}")
    print(f"open decisions: {len(decisions)}")
    print(f"contract changes: {len(status['contract_changes'])}")
    print(f"latest heartbeats: {len(heartbeats)}")
    for agent, heartbeat in sorted(heartbeats.items()):
        task = heartbeat.get("task", "")
        state = heartbeat.get("status", "unknown")
        print(f"- {agent}: {state} {task}".rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coprogrammer",
        description="Protocol tooling for semantic branch integration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    digest = subparsers.add_parser("digest", help="Generate a branch digest draft.")
    digest.add_argument("--base", default="origin/main")
    digest.add_argument("--head", default="HEAD")
    digest.add_argument("--cwd", default=".")
    digest.add_argument("--output")
    digest.add_argument(
        "--config",
        default=DEFAULT_CONFIG_FILE,
        help=f"Project policy config path. Default: {DEFAULT_CONFIG_FILE}.",
    )
    digest.add_argument(
        "--language",
        default=os.environ.get("COPROGRAMMER_LANGUAGE"),
        help="Output language: en or zh-CN. Overrides config and COPROGRAMMER_LANGUAGE.",
    )
    digest.add_argument(
        "--working-tree",
        action="store_true",
        help="Digest uncommitted working-tree changes, including untracked files.",
    )
    digest.set_defaults(func=command_digest)

    github_comment = subparsers.add_parser(
        "github-comment",
        help="Create or update a GitHub PR comment with a digest file.",
    )
    github_comment.add_argument("--file", required=True)
    github_comment.add_argument("--marker", default=DEFAULT_COMMENT_MARKER)
    github_comment.add_argument(
        "--language",
        default=os.environ.get("COPROGRAMMER_LANGUAGE", DEFAULT_LANGUAGE),
        help="Comment language: en or zh-CN. Can also use COPROGRAMMER_LANGUAGE.",
    )
    github_comment.add_argument(
        "--api-url",
        default=os.environ.get("GITHUB_API_URL", DEFAULT_GITHUB_API_URL),
    )
    github_comment.set_defaults(func=command_github_comment)

    config = subparsers.add_parser("config", help="Work with CoProgrammer config.")
    config_subparsers = config.add_subparsers(dest="config_command", required=True)
    config_validate = config_subparsers.add_parser("validate", help="Validate config JSON.")
    config_validate.add_argument("file", nargs="?", default=DEFAULT_CONFIG_FILE)
    config_validate.set_defaults(func=command_config_validate)

    manifest = subparsers.add_parser("manifest", help="Work with change manifests.")
    manifest_subparsers = manifest.add_subparsers(dest="manifest_command", required=True)
    validate = manifest_subparsers.add_parser("validate", help="Validate a manifest.")
    validate.add_argument("file")
    validate.set_defaults(func=command_manifest_validate)

    integration_plan = subparsers.add_parser(
        "integration-plan",
        help="Work with integration plan artifacts.",
    )
    integration_plan_subparsers = integration_plan.add_subparsers(
        dest="integration_plan_command",
        required=True,
    )
    integration_plan_validate = integration_plan_subparsers.add_parser(
        "validate",
        help="Validate an integration plan JSON artifact.",
    )
    integration_plan_validate.add_argument("file")
    integration_plan_validate.set_defaults(func=command_integration_plan_validate)

    agents = subparsers.add_parser(
        "agents",
        help="Work with agent instruction files.",
    )
    agents_subparsers = agents.add_subparsers(dest="agents_command", required=True)
    agents_check = agents_subparsers.add_parser(
        "check",
        help="Check that AGENTS.md stays minimal and static.",
    )
    agents_check.add_argument("file", nargs="?", default="AGENTS.md")
    agents_check.add_argument("--max-lines", type=int, default=120)
    agents_check.set_defaults(func=command_agents_check)

    heartbeat = subparsers.add_parser("heartbeat", help="Work with agent heartbeats.")
    heartbeat_subparsers = heartbeat.add_subparsers(dest="heartbeat_command", required=True)
    heartbeat_new = heartbeat_subparsers.add_parser("new", help="Create a heartbeat JSON.")
    heartbeat_new.add_argument("--agent", required=True)
    heartbeat_new.add_argument("--task", required=True)
    heartbeat_new.add_argument("--output")
    heartbeat_new.set_defaults(func=command_heartbeat_new)

    manager = subparsers.add_parser(
        "manager",
        help="Work with the local Manager Plane prototype.",
    )
    manager_subparsers = manager.add_subparsers(dest="manager_command", required=True)

    manager_init = manager_subparsers.add_parser(
        "init",
        help="Initialize local Manager event log.",
    )
    manager_init.add_argument("--cwd", default=".")
    manager_init.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_init.set_defaults(func=command_manager_init)

    manager_status = manager_subparsers.add_parser(
        "status",
        help="Show reconstructed Manager state.",
    )
    manager_status.add_argument("--cwd", default=".")
    manager_status.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_status.add_argument("--json", action="store_true")
    manager_status.set_defaults(func=command_manager_status)

    manager_heartbeat = manager_subparsers.add_parser(
        "heartbeat",
        help="Append an agent heartbeat event.",
    )
    manager_heartbeat.add_argument("--cwd", default=".")
    manager_heartbeat.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_heartbeat.add_argument("--subject", default="repo:local")
    manager_heartbeat.add_argument("--agent", required=True)
    manager_heartbeat.add_argument("--task", required=True)
    manager_heartbeat.set_defaults(func=command_manager_heartbeat)

    manager_event = manager_subparsers.add_parser(
        "event",
        help="Work with raw manager events.",
    )
    manager_event_subparsers = manager_event.add_subparsers(
        dest="event_command",
        required=True,
    )
    manager_event_append = manager_event_subparsers.add_parser(
        "append",
        help="Append a raw manager event.",
    )
    manager_event_append.add_argument("--cwd", default=".")
    manager_event_append.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_event_append.add_argument("--type", required=True, choices=EVENT_TYPES)
    manager_event_append.add_argument("--actor", required=True)
    manager_event_append.add_argument("--subject", default="repo:local")
    manager_event_append.add_argument("--payload")
    manager_event_append.set_defaults(func=command_manager_event_append)

    manager_lease = manager_subparsers.add_parser(
        "lease",
        help="Work with workspace leases.",
    )
    manager_lease_subparsers = manager_lease.add_subparsers(
        dest="lease_command",
        required=True,
    )
    manager_lease_request = manager_lease_subparsers.add_parser(
        "request",
        help="Request a workspace lease.",
    )
    manager_lease_request.add_argument("--cwd", default=".")
    manager_lease_request.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_lease_request.add_argument("--subject", default="repo:local")
    manager_lease_request.add_argument("--holder", required=True)
    manager_lease_request.add_argument("--kind", default="path", choices=LEASE_KINDS)
    manager_lease_request.add_argument("--pattern", action="append", required=True)
    manager_lease_request.add_argument("--task", default="")
    manager_lease_request.set_defaults(func=command_manager_lease_request)

    manager_lease_release = manager_lease_subparsers.add_parser(
        "release",
        help="Release a workspace lease.",
    )
    manager_lease_release.add_argument("--cwd", default=".")
    manager_lease_release.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_lease_release.add_argument("--subject", default="repo:local")
    manager_lease_release.add_argument("--actor", required=True)
    manager_lease_release.add_argument("--id", required=True)
    manager_lease_release.set_defaults(func=command_manager_lease_release)

    manager_leases = manager_subparsers.add_parser(
        "leases",
        help="List active workspace leases.",
    )
    manager_leases.add_argument("--cwd", default=".")
    manager_leases.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_leases.add_argument("--json", action="store_true")
    manager_leases.set_defaults(func=command_manager_leases)

    manager_decisions = manager_subparsers.add_parser(
        "decisions",
        help="List open decision records.",
    )
    manager_decisions.add_argument("--cwd", default=".")
    manager_decisions.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_decisions.add_argument("--json", action="store_true")
    manager_decisions.set_defaults(func=command_manager_decisions)

    manager_contract = manager_subparsers.add_parser(
        "contract",
        help="Work with shared contract changes.",
    )
    manager_contract_subparsers = manager_contract.add_subparsers(
        dest="contract_command",
        required=True,
    )
    manager_contract_propose = manager_contract_subparsers.add_parser(
        "propose",
        help="Propose a shared contract change.",
    )
    manager_contract_propose.add_argument("--cwd", default=".")
    manager_contract_propose.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_contract_propose.add_argument("--subject", default="repo:local")
    manager_contract_propose.add_argument("--proposer", required=True)
    manager_contract_propose.add_argument(
        "--kind",
        required=True,
        choices=CONTRACT_KINDS,
    )
    manager_contract_propose.add_argument("--name", required=True)
    manager_contract_propose.add_argument("--summary", required=True)
    manager_contract_propose.add_argument(
        "--compatibility",
        default="unknown",
        choices=CONTRACT_COMPATIBILITY,
    )
    manager_contract_propose.add_argument("--artifact", action="append", default=[])
    manager_contract_propose.set_defaults(func=command_manager_contract_propose)

    manager_contracts = manager_subparsers.add_parser(
        "contracts",
        help="List proposed shared contract changes.",
    )
    manager_contracts.add_argument("--cwd", default=".")
    manager_contracts.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_contracts.add_argument("--kind", choices=CONTRACT_KINDS)
    manager_contracts.add_argument("--json", action="store_true")
    manager_contracts.set_defaults(func=command_manager_contracts)

    manager_decision = manager_subparsers.add_parser(
        "decision",
        help="Work with a single decision record.",
    )
    manager_decision_subparsers = manager_decision.add_subparsers(
        dest="decision_command",
        required=True,
    )
    manager_decision_record = manager_decision_subparsers.add_parser(
        "record",
        help="Record the outcome for an open decision.",
    )
    manager_decision_record.add_argument("--cwd", default=".")
    manager_decision_record.add_argument("--state-dir", default=DEFAULT_MANAGER_DIR)
    manager_decision_record.add_argument("--subject", default="repo:local")
    manager_decision_record.add_argument("--id", required=True)
    manager_decision_record.add_argument("--decision", required=True)
    manager_decision_record.add_argument("--decider", required=True)
    manager_decision_record.add_argument(
        "--status",
        default="decided",
        choices=DECISION_RECORD_STATUSES,
    )
    manager_decision_record.add_argument("--note", default="")
    manager_decision_record.set_defaults(func=command_manager_decision_record)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
