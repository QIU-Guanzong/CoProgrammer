"""CLI adapter for workspace observations, explicit checks and handoffs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import evidence, workflow, workspace


def command(args):
    from .cli import event_log_path
    cwd = Path(args.cwd).resolve()
    action = args.workflow_action
    status = 0
    if action == "snapshot":
        result = workspace.snapshot(cwd, args.base)
    elif action == "compare":
        result = workflow.compare(cwd, cwd / args.bundle, args.base)
        status = int(not result["aligned"])
    elif action in ("run", "verify"):
        argv = args.check_argv
        if argv[:1] == ["--"]:
            argv = argv[1:]
        if action == "run":
            result = evidence.run(cwd, argv, args.label, cwd / args.output, args.timeout_seconds)
            status = int(result["exit_code"] != 0 or not result["stable"] or bool(result["error"]))
        else:
            result = evidence.verify(cwd, cwd / args.artifact, argv or None, max_age_seconds=args.max_age_seconds)
            status = int(not result["fresh"])
    else:
        path = event_log_path(cwd, args.state_dir)
        if action == "dispatch":
            result = workflow.dispatch(path, cwd, args.session, args.limit)
        else:
            result = workflow.handoff(path, cwd, args.session, args.task, args.base,
                                      [cwd / p for p in args.check])
            if args.format == "markdown":
                print(workflow.render_handoff(result), end="")
                return 0
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return status


def add_parsers(root, manager):
    workspace_parser = root.add_parser("workspace", help="Inspect content and compare portable handoff context.")
    workspace_actions = workspace_parser.add_subparsers(required=True)
    for action in ("snapshot", "compare"):
        parser = workspace_actions.add_parser(action)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--base", default="HEAD" if action == "snapshot" else None)
        if action == "compare":
            parser.add_argument("bundle")
        parser.set_defaults(func=command, workflow_action=action)
    check = root.add_parser("check", help="Run an explicit local command and verify content-bound receipts.")
    actions = check.add_subparsers(required=True)
    for action in ("run", "verify"):
        parser = actions.add_parser(action)
        parser.add_argument("--cwd", default=".")
        if action == "run":
            parser.add_argument("--label", required=True)
            parser.add_argument("--output", required=True)
            parser.add_argument("--timeout-seconds", type=int, default=300)
        else:
            parser.add_argument("--artifact", required=True)
            parser.add_argument("--max-age-seconds", type=int, default=86400)
        parser.add_argument("check_argv", nargs=argparse.REMAINDER, help="Explicit command arguments after --.")
        parser.set_defaults(func=command, workflow_action=action)
    for action in ("dispatch", "handoff"):
        parser = manager.add_parser(action)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.add_argument("--session", required=True)
        if action == "dispatch":
            parser.add_argument("--limit", type=int, default=20)
        else:
            parser.add_argument("--task", required=True)
            parser.add_argument("--base", default="HEAD")
            parser.add_argument("--check", action="append", default=[])
            parser.add_argument("--format", choices=("json", "markdown"), default="json")
        parser.set_defaults(func=command, workflow_action=action)
