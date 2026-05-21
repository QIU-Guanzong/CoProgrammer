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


REQUIRED_MANIFEST_FIELDS = {
    "task",
    "intent",
    "scope",
    "core_changes",
    "contracts",
    "tests",
    "risks",
}

DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_COMMENT_MARKER = "<!-- coprogrammer-branch-digest -->"
GITHUB_COMMENT_LIMIT = 65000
DEFAULT_LANGUAGE = "en"
DEFAULT_CONFIG_FILE = ".coprogrammer.json"
RISK_LEVELS = ("low", "medium", "high", "critical")

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


def new_heartbeat(agent: str, task: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
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


def command_heartbeat_new(args: argparse.Namespace) -> int:
    heartbeat = new_heartbeat(args.agent, args.task)
    text = json.dumps(heartbeat, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
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

    heartbeat = subparsers.add_parser("heartbeat", help="Work with agent heartbeats.")
    heartbeat_subparsers = heartbeat.add_subparsers(dest="heartbeat_command", required=True)
    heartbeat_new = heartbeat_subparsers.add_parser("new", help="Create a heartbeat JSON.")
    heartbeat_new.add_argument("--agent", required=True)
    heartbeat_new.add_argument("--task", required=True)
    heartbeat_new.add_argument("--output")
    heartbeat_new.set_defaults(func=command_heartbeat_new)

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
