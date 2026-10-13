"""CLI and MCP declarations for explicit local worker boundaries."""
from pathlib import Path
import json

from . import collaboration as co, worker


def command(args):
    from .cli import event_log_path
    from .workflow_cli import emit
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    if args.worker_action in ("run", "watch"):
        from .runner import run
        argv = args.command[1:] if args.command[:1] == ["--"] else args.command
        options = dict(apply=args.apply, timeout=args.timeout_seconds,
                       notify=args.notify, handle_inbox=args.handle_inbox)
        if args.worker_action == "watch":
            from .watcher import watch
            import sys
            def progress(event):
                emit(json.dumps(event, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            report = watch(path, cwd, args.session, argv, **options, wait=args.wait,
                           max_cycles=args.max_cycles, duration=args.duration_seconds,
                           poll_seconds=args.poll_seconds,
                           progress=progress)
        else:
            report = run(path, cwd, args.session, argv, **options)
    elif args.worker_action == "step":
        report = worker.step(path, cwd, args.session, apply=args.apply,
                             task_id=args.id, files=args.file, limit=args.limit,
                             ttl_seconds=args.ttl_seconds)
    else:
        report = worker.finish(path, cwd, args.session, args.id, args.claim,
                               args.summary, args.notify)
    emit(json.dumps(report, ensure_ascii=False, indent=None if args.worker_action == "watch" else 2) + "\n")
    if args.worker_action in ("run", "watch") and report.get("state") == "attention":
        return 1
    return 0


def add_parsers(parsers):
    root = parsers.add_parser("worker", help="Preview/apply work boundaries and finish with local notifications.")
    actions = root.add_subparsers(dest="worker_action", required=True)
    for action in ("step", "finish", "run", "watch"):
        parser = actions.add_parser(action)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.add_argument("--session", required=True)
        if action in ("run", "watch"):
            import argparse
            parser.add_argument("--apply", action="store_true", help="Explicitly run one trusted harness command after claiming/guarding work.")
            parser.add_argument("--timeout-seconds", type=int, default=120)
            parser.add_argument("--notify", action="append")
            parser.add_argument("--handle-inbox", action="store_true", help="Deliver inbox to the trusted command; acknowledge only its explicit receipt IDs, with no project edits.")
            if action == "watch":
                parser.add_argument("--wait", action="store_true", help="Wait in this foreground process for peer task/message changes; bounded by cycle/duration limits.")
                parser.add_argument("--max-cycles", type=int, default=20)
                parser.add_argument("--duration-seconds", type=int, default=300)
                parser.add_argument("--poll-seconds", type=int, default=5)
            parser.add_argument("command", nargs=argparse.REMAINDER, help="Trusted command argv after --; JSON task on stdin, JSON result on stdout.")
        elif action == "step":
            parser.add_argument("--apply", action="store_true", help="Pulse and claim/guard/renew atomically; never ACK or launch clients.")
            parser.add_argument("--id", default="", help="Optional specific task; otherwise choose the first eligible task.")
            parser.add_argument("--file", action="append", help="Planned path; actual working-tree changes are also checked.")
            parser.add_argument("--limit", type=int, default=20)
            parser.add_argument("--ttl-seconds", type=int, default=3600)
        else:
            parser.add_argument("--id", required=True)
            parser.add_argument("--claim", required=True)
            parser.add_argument("--summary", required=True)
            parser.add_argument("--notify", action="append", help="Explicit local recipient; repeatable, sends a durable handoff.")
        parser.set_defaults(func=command)


def declarations(string_schema):
    identity = {"type": "string", "pattern": co.ID_PATTERN, "minLength": 1, "maxLength": 64}
    return [{"name": "worker_step",
             "description": "Preview or explicitly apply one local work boundary: pulse, inspect inbox/decisions, claim ready work or guard/renew owned work. Messages/decisions stop work; no auto-ACK, process launch or takeover.",
             "inputSchema": {"type": "object", "additionalProperties": False,
                             "properties": {"session": identity, "apply": {"type": "boolean", "default": False},
                                            "task_id": identity, "files": {"type": "array", "items": string_schema(4096), "maxItems": 128},
                                            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
                                            "ttl_seconds": {"type": "integer", "minimum": 1, "maximum": 604800, "default": 3600}},
                             "required": ["session"]}},
            {"name": "worker_finish",
             "description": "Guard changes, finish this claim and send optional handoffs to explicit local recipients atomically. Identical completion retries do not duplicate messages. No recipient ACK, client wakeup or code approval.",
             "inputSchema": {"type": "object", "additionalProperties": False,
                             "properties": {"session": identity, "task_id": identity, "claim_id": identity,
                                            "summary": string_schema(16000),
                                            "notify": {"type": "array", "items": identity, "maxItems": 16, "uniqueItems": True}},
                             "required": ["session", "task_id", "claim_id", "summary"]}}]


def dispatch(name, ctx, args):
    return getattr(worker, name.removeprefix("worker_"))(ctx.log_path, ctx.cwd, **args)
