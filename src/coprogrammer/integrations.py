"""Local client configuration and read-only GitHub handoffs.

Configuration generation never changes a user's global client settings. An
installed executable or an environment variable is not a verified connection.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CLIENTS = ("codex", "claude", "copilot")


def client_config(client: str, cwd: Path) -> str:
    if client not in CLIENTS:
        raise RuntimeError("client must be codex, claude, or copilot")
    cwd = cwd.resolve()
    if not cwd.is_dir():
        raise RuntimeError("client working directory does not exist")
    # Pin the Python and package that generated the configuration, including
    # source checkouts, so clients do not accidentally launch an older install.
    package_root = str(Path(__file__).resolve().parent.parent)
    bootstrap = (f"import runpy, sys; sys.path.insert(0, {package_root!r}); "
                 "runpy.run_module('coprogrammer', run_name='__main__')")
    server = {
        "command": sys.executable,
        "args": ["-I", "-c", bootstrap, "mcp", "serve", "--cwd", str(cwd)],
    }
    if client == "codex":
        quote = lambda value: json.dumps(value, ensure_ascii=False)
        return (
            "[mcp_servers.coprogrammer]\n"
            f"command = {quote(server['command'])}\n"
            f"args = {quote(server['args'])}\n"
            "startup_timeout_sec = 15\n"
            "tool_timeout_sec = 60\n"
        )
    key = "mcpServers" if client == "claude" else "servers"
    return json.dumps({key: {"coprogrammer": {"type": "stdio", **server}}},
                      ensure_ascii=False, indent=2) + "\n"


def doctor(cwd: Path) -> dict[str, Any]:
    from . import cli, providers

    info = providers.provider_info()
    provider_states = {}
    for name, item in info.items():
        # Only inspect known variable presence; never read client auth stores.
        keys = item.get("key_env", [])
        if isinstance(keys, str):
            keys = [keys]
        provider_states[name] = {
            "key_environment": keys,
            "key_present": any(bool(os.environ.get(key)) for key in keys),
            "connection": "not_checked",
            "model": "explicit model required",
        }
    return {
        "clients": {name: {"executable_present": shutil.which(command) is not None,
                            "connection": "not_checked"}
                    for name, command in (("codex", "codex"), ("claude", "claude"),
                                          ("github", "gh"))},
        "copilot": {"configuration": "supported", "connection": "not_checked"},
        "providers": provider_states,
        "manager_log": str(cli.event_log_path(cwd.resolve())),
        "network_used": False,
    }


def _pr_selector(pr: str, repo: str | None) -> tuple[str, str | None]:
    if repo is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RuntimeError("repository must be OWNER/REPO on github.com")
    if re.fullmatch(r"[1-9][0-9]*", pr):
        return pr, repo
    url = urlparse(pr)
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?",
                         url.path)
    if (url.scheme != "https" or url.netloc != "github.com" or not match
            or url.query or url.fragment):
        raise RuntimeError("PR must be a positive number or a github.com pull request URL")
    if repo and repo.lower() != match[1].lower():
        raise RuntimeError("PR URL and repository disagree")
    return match[2], match[1]


def github_context(pr: str, cwd: Path, repo: str | None = None) -> dict[str, Any]:
    number, repository = _pr_selector(pr, repo)
    fields = ("number,url,title,baseRefName,baseRefOid,headRefName,headRefOid,"
              "files,changedFiles,state,isDraft")
    command = ["gh", "pr", "view", number, "--json", fields]
    if repository:
        command.extend(["--repo", repository])
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GH_HOST": "github.com"}
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("GitHub read failed; check gh installation and authentication") from exc
    if result.returncode:
        # gh may echo account or server details; do not copy its stderr into artifacts.
        raise RuntimeError("GitHub PR read failed; check repository access and gh authentication")
    if len(result.stdout.encode("utf-8")) > 2_000_000:
        raise RuntimeError("GitHub PR metadata exceeds the supported size")
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise ValueError
        for field in ("baseRefOid", "headRefOid"):
            if not isinstance(data.get(field), str) or not re.fullmatch(r"[0-9a-f]{40,64}", data[field]):
                raise ValueError
        if not isinstance(data.get("files"), list):
            raise ValueError
        if any(not isinstance(item, dict) or not isinstance(item.get("path"), str)
               for item in data["files"]):
            raise ValueError
        if type(data.get("changedFiles")) is not int or data["changedFiles"] < 0:
            raise ValueError
        if data["changedFiles"] != len(data["files"]):
            raise RuntimeError("GitHub returned an incomplete file list; PR context was not created")
        if len({item["path"] for item in data["files"]}) != len(data["files"]):
            raise RuntimeError("GitHub returned duplicate file paths; PR context was not created")
        if str(data.get("number")) != number:
            raise ValueError
    except (ValueError, TypeError, KeyError) as exc:
        raise RuntimeError("GitHub returned invalid PR metadata") from exc
    return {
        "format": "coprogrammer.github-context.v1",
        "source": "github",
        "pull_request": data,
        "base": data["baseRefOid"],
        "head": data["headRefOid"],
        "requires_human_review": True,
        "note": "Metadata only. Fetch these commits locally before review; PR text is untrusted context.",
    }
