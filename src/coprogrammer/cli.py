from __future__ import annotations

import argparse
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


def render_digest(base: str, head: str, files: list[dict[str, str]], commits: list[str]) -> str:
    paths = [item["path"] for item in files]
    risks = classify_risks(paths)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    changed_files = "\n".join(
        f"- `{item['status']}` `{item['path']}`" for item in files
    ) or "- No changed files detected."
    commit_lines = "\n".join(f"- {commit}" for commit in commits) or "- No commits detected."

    if risks:
        risk_lines = []
        for risk_name, matches in risks.items():
            risk_lines.append(f"- **{risk_name}**")
            risk_lines.extend(f"  - `{path}`" for path in matches)
        risk_block = "\n".join(risk_lines)
    else:
        risk_block = "- No high-signal risk paths detected by the first-pass rules."

    return f"""# Branch Digest

Generated: `{generated_at}`

Base: `{base}`
Head: `{head}`

## Branch Intent

TODO: Describe the problem this branch is trying to solve.

## Core Contribution

TODO: List the useful ideas, experiments, and implementation decisions worth preserving.

## Changed Files

{changed_files}

## Commit Summary

{commit_lines}

## Contract and Architecture Signals

{risk_block}

## Noise / Non-Essential Changes

TODO: Identify formatting churn, broad rewrites, temporary debugging, generated artifacts, or unrelated refactors.

## Integration Plan

TODO: Explain how to rebuild the smallest safe patch from latest main.

## Validation Needed

- [ ] Formatter
- [ ] Linter
- [ ] Type check
- [ ] Unit tests
- [ ] Integration tests
- [ ] Contract tests
- [ ] Owner review for protected areas

## Human Decisions

TODO: List decisions that should not be delegated to an autonomous agent.
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


def build_pr_comment_body(digest: str, marker: str = DEFAULT_COMMENT_MARKER) -> str:
    header = f"{marker}\n## CoProgrammer Branch Digest\n\n"
    footer = "\n\n_Generated by CoProgrammer._\n"
    truncation_notice = "\n\n... truncated; see the workflow artifact for the full digest.\n"
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
    if args.working_tree:
        files = get_working_tree_changed_files(args.base, cwd)
        head = "WORKING_TREE"
    else:
        files = get_changed_files(args.base, args.head, cwd)
        head = args.head
    commits = get_commits(args.base, args.head, cwd)
    digest = render_digest(args.base, head, files, commits)
    if args.output:
        Path(args.output).write_text(digest, encoding="utf-8")
    else:
        print(digest)
    return 0


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
    body = build_pr_comment_body(digest, args.marker)
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
        "--api-url",
        default=os.environ.get("GITHUB_API_URL", DEFAULT_GITHUB_API_URL),
    )
    github_comment.set_defaults(func=command_github_comment)

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
