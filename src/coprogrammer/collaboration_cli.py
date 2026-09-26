"""CLI adapter for local window coordination."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import collaboration as core


def command(args: argparse.Namespace) -> int:
    from .cli import event_log_path
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    action = args.collaboration_action
    if action == "register":
        result = core.register(path, cwd, args.session, args.client, args.task,
                               args.provider, args.model, args.ttl_seconds)
    elif action == "pulse":
        result = core.pulse(path, cwd, args.session, args.status, args.task, args.note)
    elif action == "send":
        body = args.body
        if args.body_file is not None:
            try:
                with Path(args.body_file).open(encoding="utf-8") as handle:
                    body = handle.read(16001)
            except UnicodeError as exc:
                raise RuntimeError("message body file must be UTF-8") from exc
        result = core.send(path, cwd, args.sender, args.to, args.task, body,
                           args.kind, args.reply_to, args.key)
    elif action == "ack":
        result = core.acknowledge(path, cwd, args.session, args.id)
    elif action == "inbox":
        result = core.inbox(path, args.session, args.task, args.include_acked, args.after, args.limit)
    else:
        result = core.sync(path, args.session, args.after, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def add_parsers(manager) -> None:
    def options(parser, action):
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.set_defaults(func=command, collaboration_action=action)
        return parser

    sessions = manager.add_parser("session", help="Register and update independent coding windows.")
    session_sub = sessions.add_subparsers(dest="session_command", required=True)
    register = options(session_sub.add_parser("register"), "register")
    register.add_argument("--session", required=True)
    register.add_argument("--client", required=True)
    register.add_argument("--task", required=True)
    register.add_argument("--provider", default="")
    register.add_argument("--model", default="")
    register.add_argument("--ttl-seconds", type=int, default=300)
    pulse = options(session_sub.add_parser("pulse"), "pulse")
    pulse.add_argument("--session", required=True)
    pulse.add_argument("--status", choices=core.STATUSES, default="working")
    pulse.add_argument("--task")
    pulse.add_argument("--note", default="")

    messages = manager.add_parser("message", help="Exchange durable task messages on the local Manager.")
    message_sub = messages.add_subparsers(dest="message_command", required=True)
    send = options(message_sub.add_parser("send"), "send")
    send.add_argument("--from", dest="sender", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--task", required=True)
    body = send.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    send.add_argument("--kind", choices=core.KINDS, default="update")
    send.add_argument("--reply-to", default="")
    send.add_argument("--key", default="", help="Retry key unique to the sender; reuse only for identical content.")
    inbox = options(message_sub.add_parser("inbox"), "inbox")
    inbox.add_argument("--session", required=True)
    inbox.add_argument("--task", default="")
    inbox.add_argument("--include-acked", action="store_true")
    inbox.add_argument("--after", default="")
    inbox.add_argument("--limit", type=int, default=50)
    ack = options(message_sub.add_parser("ack"), "ack")
    ack.add_argument("--session", required=True)
    ack.add_argument("--id", required=True)

    sync = options(manager.add_parser("sync", help="Read sessions, unread messages and resumable Manager changes."), "sync")
    sync.add_argument("--session", default="")
    sync.add_argument("--after", default="")
    sync.add_argument("--limit", type=int, default=50)
