"""CLI and MCP declarations for explicit local worker boundaries."""
from pathlib import Path
import json

from . import collaboration as co, worker


def command(args):
    from .cli import event_log_path
    from .workflow_cli import emit
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    if args.worker_action == "step":
        report = worker.step(path, cwd, args.session, apply=args.apply,
                             task_id=args.id, files=args.file, limit=args.limit,
                             ttl_seconds=args.ttl_seconds)
    else:
        report = worker.finish(path, cwd, args.session, args.id, args.claim,
                               args.summary, args.notify)
    emit(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


def add_parsers(parsers):
    root = parsers.add_parser("worker", help="Preview/apply work boundaries and finish with local notifications.")
    actions = root.add_subparsers(dest="worker_action", required=True)
    for action in ("step", "finish"):
        parser = actions.add_parser(action)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.add_argument("--session", required=True)
        if action == "step":
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
