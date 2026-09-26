"""CLI adapter and Git change collection for cooperative task dispatch."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import scheduler


def working_files(cwd: Path) -> list[str]:
    """Keep both rename paths and unquoted Unicode names from Git's NUL format."""
    try:
        result = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                                cwd=cwd, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("cannot inspect working-tree files") from exc
    if result.returncode or len(result.stdout) > 2_000_000:
        raise RuntimeError("cannot inspect working-tree files or result is too large")
    try:
        entries = result.stdout.decode("utf-8").split("\0")
    except UnicodeError as exc:
        raise RuntimeError("working-tree paths must be valid UTF-8") from exc
    paths, index = [], 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise RuntimeError("unexpected Git status record")
        paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if index >= len(entries) or not entries[index]:
                raise RuntimeError("missing original rename path")
            paths.append(entries[index])
            index += 1
    return list(dict.fromkeys(paths))


def command(args):
    from .cli import event_log_path, load_events
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    action = args.task_action
    if action == "board":
        result = scheduler.board(load_events(path))
    elif action == "create":
        result = scheduler.create(path, cwd, args.session, args.id, args.title,
                                  args.pattern, args.depends_on, args.client)
    elif action == "claim":
        result = scheduler.claim(path, cwd, args.session, args.id, args.ttl_seconds)
    elif action == "renew":
        result = scheduler.renew(path, cwd, args.session, args.id, args.claim, args.ttl_seconds)
    elif action == "reclaim":
        result = scheduler.reclaim(path, cwd, args.session, args.id, args.summary)
    elif action == "guard":
        files = list(dict.fromkeys([*args.file, *(working_files(cwd) if args.working_tree else [])]))
        result = scheduler.guard(path, cwd, args.session, args.id, args.claim, files)
    else:
        result = getattr(scheduler, action)(path, cwd, args.session, args.id, args.claim, args.summary)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def add_parsers(manager):
    group = manager.add_parser("task", help="Dispatch dependency-aware work with atomic path reservations.")
    tasks = group.add_subparsers(dest="task_action", required=True)
    for action in ("create", "claim", "renew", "finish", "release", "reclaim", "guard", "board"):
        parser = tasks.add_parser(action)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.set_defaults(func=command)
        if action == "board":
            continue
        parser.add_argument("--session", required=True)
        parser.add_argument("--id", required=action != "claim", default="")
        if action == "create":
            parser.add_argument("--title", required=True)
            parser.add_argument("--pattern", action="append", required=True)
            parser.add_argument("--depends-on", action="append", default=[])
            parser.add_argument("--client", action="append", default=[])
        if action in ("claim", "renew"):
            parser.add_argument("--ttl-seconds", type=int, default=3600)
        if action in ("renew", "finish", "release", "guard"):
            parser.add_argument("--claim", required=True)
        if action in ("finish", "release", "reclaim"):
            parser.add_argument("--summary", required=True)
        if action == "guard":
            parser.add_argument("--file", action="append", default=[])
            parser.add_argument("--working-tree", action="store_true",
                                help="Check staged, unstaged and untracked nonignored paths, including both rename paths.")
