"""Durable, cooperative window coordination; no terminal control or networking.

All mutations check and append inside the existing Manager transaction. Session
labels are local routing identifiers, not authenticated identities. Reading an
inbox or syncing never acknowledges a message or refreshes a session's pulse.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .manager_store import load_events, transaction

EVENT_TYPES = ("session.registered", "session.updated", "message.sent", "message.acknowledged")
STATUSES = ("working", "blocked", "idle", "closed")
KINDS = ("update", "question", "handoff")
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"


def text(value: Any, name: str, maximum: int = 256, *, empty: bool = False) -> str:
    if (not isinstance(value, str) or len(value) > maximum
            or (not empty and not value.strip())
            or any(ord(c) < 32 and c not in "\n\t" for c in value)):
        raise RuntimeError(f"invalid {name}")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RuntimeError(f"invalid {name} Unicode") from exc
    return value


def identity(value: Any, name: str = "session") -> str:
    if not isinstance(value, str) or re.fullmatch(ID_PATTERN, value) is None:
        raise RuntimeError(f"{name} must use 1-64 letters, digits, dots, underscores or hyphens")
    return value


def bounded(value: Any, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}")
    return value


def timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("invalid coordination timestamp") from exc


def workspace(cwd: Path) -> dict[str, str]:
    from .cli import run_git
    cwd = cwd.resolve()
    if not cwd.is_dir():
        raise RuntimeError("session working directory does not exist")
    try:
        root = run_git(["rev-parse", "--show-toplevel"], cwd)
    except RuntimeError:
        return {"worktree": str(cwd), "branch": "", "head": ""}
    try:
        head = run_git(["rev-parse", "--verify", "HEAD"], cwd)
    except RuntimeError:
        head = ""
    try:
        branch = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd)
    except RuntimeError:
        branch = "HEAD" if head else ""
    return {"worktree": str(Path(root).resolve()), "branch": branch, "head": head}


def validate_event(event: dict[str, Any]) -> None:
    """Validate stored payloads too, so malformed history fails closed."""
    kind, payload = event["type"], event.get("payload", {})
    timestamp(event["timestamp"])
    if kind.startswith("session."):
        record = payload.get("session")
        fields = {"id", "client", "provider", "model", "task", "status", "worktree",
                  "branch", "head", "ttl_seconds", "last_seen", "note"}
        if not isinstance(record, dict) or set(record) != fields:
            raise RuntimeError("invalid session record")
        identity(record["id"])
        for field in ("client", "task", "worktree"):
            text(record[field], field, 4096 if field == "worktree" else 256)
        for field in ("provider", "model", "branch", "head", "note"):
            text(record[field], field, 2000, empty=True)
        if record["status"] not in STATUSES:
            raise RuntimeError("invalid session status")
        bounded(record["ttl_seconds"], "ttl_seconds", 86400)
        timestamp(record["last_seen"])
        if record["last_seen"] != event["timestamp"] or record["id"] != event["actor"]:
            raise RuntimeError("session actor or timestamp mismatch")
    elif kind == "message.sent":
        record = payload.get("message")
        fields = {"id", "sender", "recipient", "task", "kind", "body", "reply_to", "key"}
        if not isinstance(record, dict) or set(record) != fields:
            raise RuntimeError("invalid message record")
        for field in ("id", "sender", "recipient"):
            identity(record[field], field)
        text(record["task"], "task")
        text(record["body"], "body", 16000)
        for field in ("reply_to", "key"):
            if record[field]:
                identity(record[field], field)
            elif record[field] != "":
                raise RuntimeError(f"invalid {field}")
        if record["kind"] not in KINDS or record["sender"] != event["actor"]:
            raise RuntimeError("invalid message kind or actor")
    elif kind == "message.acknowledged":
        if set(payload) != {"message_id", "recipient"}:
            raise RuntimeError("invalid acknowledgement")
        identity(payload["message_id"], "message_id")
        identity(payload["recipient"], "recipient")
        if payload["recipient"] != event["actor"]:
            raise RuntimeError("acknowledgement actor mismatch")


def reconstruct(events: list[dict[str, Any]]) -> tuple[dict, dict]:
    sessions: dict[str, dict] = {}
    messages: dict[str, dict] = {}
    keys: set[tuple[str, str]] = set()
    for event in events:
        kind, payload = event["type"], event.get("payload", {})
        if kind not in EVENT_TYPES:
            continue
        validate_event(event)
        if kind.startswith("session."):
            session = dict(payload["session"])
            old = sessions.get(session["id"])
            if kind == "session.registered":
                if old or session["status"] != "working":
                    raise RuntimeError("invalid duplicate or closed session registration")
            elif (not old or old["status"] == "closed"
                  or any(old[k] != session[k] for k in ("client", "provider", "model", "worktree"))):
                raise RuntimeError("invalid session update history")
            sessions[session["id"]] = session
        elif kind == "message.sent":
            message = dict(payload["message"])
            if (message["id"] in messages
                    or any(s not in sessions or sessions[s]["status"] == "closed"
                           for s in (message["sender"], message["recipient"]))):
                raise RuntimeError("invalid message session or duplicate ID")
            if message["reply_to"]:
                parent = messages.get(message["reply_to"])
                if (not parent or parent["task"] != message["task"]
                        or {parent["sender"], parent["recipient"]} != {message["sender"], message["recipient"]}):
                    raise RuntimeError("reply must keep the original task and participants")
            key = (message["sender"], message["key"])
            if message["key"]:
                if key in keys:
                    raise RuntimeError("duplicate message request key in history")
                keys.add(key)
            messages[message["id"]] = {**message, "timestamp": event["timestamp"],
                                       "event_id": event["id"], "acknowledged_at": None}
        else:
            message = messages.get(payload["message_id"])
            if not message or message["recipient"] != payload["recipient"] or message["acknowledged_at"]:
                raise RuntimeError("invalid acknowledgement history")
            message["acknowledged_at"] = event["timestamp"]
    return sessions, messages


def freshness(session: dict, now: datetime | None = None) -> str:
    if session["status"] == "closed":
        return "closed"
    age = ((now or datetime.now(timezone.utc)) - timestamp(session["last_seen"])).total_seconds()
    if age < 0:
        return "unknown"
    return "fresh" if age < session["ttl_seconds"] else "stale"


def directory(events: list[dict[str, Any]]) -> dict:
    from .scheduler import board
    sessions, messages = reconstruct(events)
    tasks = board(events)
    return {"sessions": [{**s, "freshness": freshness(s)} for s in sessions.values()],
            "pending_messages": sum(m["acknowledged_at"] is None for m in messages.values()),
            "tasks": tasks["tasks"], "task_counts": tasks["counts"]}


def _session(sessions: dict, session_id: str, cwd: Path | None = None, *, active: bool = True) -> dict:
    identity(session_id)
    session = sessions.get(session_id)
    if session is None:
        raise RuntimeError(f"unknown session: {session_id}")
    if active and session["status"] == "closed":
        raise RuntimeError(f"session is closed: {session_id}")
    if cwd is not None and session["worktree"] != workspace(cwd)["worktree"]:
        raise RuntimeError("session belongs to a different worktree")
    return session


def register(path: Path, cwd: Path, session: str, client: str, task: str,
             provider: str = "", model: str = "", ttl_seconds: int = 300) -> dict:
    from .cli import make_event
    identity(session)
    record = {"id": session, "client": client, "provider": provider, "model": model,
              "task": task, "status": "working", "ttl_seconds": ttl_seconds, "note": "",
              **workspace(cwd)}
    event = make_event("session.registered", session, f"session:{session}")
    record["last_seen"] = event["timestamp"]
    event["payload"] = {"session": record}
    validate_event(event)
    with transaction(path) as tx:
        sessions, _ = reconstruct([*tx.events, *tx.pending])
        if session in sessions:
            raise RuntimeError("session ID already exists; pulse to resume or choose a new window ID")
        tx.append(event)
    return {**record, "freshness": freshness(record)}


def pulse(path: Path, cwd: Path, session: str, status: str = "working",
          task: str | None = None, note: str = "") -> dict:
    from .cli import make_event
    with transaction(path) as tx:
        sessions, _ = reconstruct([*tx.events, *tx.pending])
        old = _session(sessions, session, cwd)
        event = make_event("session.updated", session, f"session:{session}")
        record = {**old, **workspace(cwd), "status": status, "note": note,
                  "task": old["task"] if task is None else task, "last_seen": event["timestamp"]}
        event["payload"] = {"session": record}
        validate_event(event)
        tx.append(event)
    return {**record, "freshness": freshness(record)}


def send(path: Path, cwd: Path, sender: str, recipient: str, task: str, body: str,
         kind: str = "update", reply_to: str = "", key: str = "") -> dict:
    from .cli import make_event
    record = {"id": f"msg_{uuid4().hex}", "sender": sender, "recipient": recipient,
              "task": task, "body": body, "kind": kind, "reply_to": reply_to, "key": key}
    event = make_event("message.sent", sender, f"task:{task}", {"message": record})
    validate_event(event)
    with transaction(path) as tx:
        sessions, messages = reconstruct([*tx.events, *tx.pending])
        _session(sessions, sender, cwd, active=False)
        if key:
            for previous in messages.values():
                if previous["sender"] == sender and previous["key"] == key:
                    if any(previous[k] != record[k] for k in record if k != "id"):
                        raise RuntimeError("message request key was already used with different content")
                    return {"message": previous, "duplicate": True}
        _session(sessions, sender)
        target = _session(sessions, recipient)
        # Apply the same relationship checks used during recovery before commit.
        _, updated = reconstruct([*tx.events, *tx.pending, event])
        tx.append(event)
        return {"message": updated[record["id"]], "duplicate": False,
                "recipient_freshness": freshness(target)}


def acknowledge(path: Path, cwd: Path, session: str, message_id: str) -> dict:
    from .cli import make_event
    identity(message_id, "message_id")
    with transaction(path) as tx:
        sessions, messages = reconstruct([*tx.events, *tx.pending])
        _session(sessions, session, cwd, active=False)
        message = messages.get(message_id)
        if not message or message["recipient"] != session:
            raise RuntimeError("message does not belong to this recipient")
        if message["acknowledged_at"]:
            return {"message_id": message_id, "acknowledged_at": message["acknowledged_at"], "duplicate": True}
        event = make_event("message.acknowledged", session, f"task:{message['task']}",
                           {"message_id": message_id, "recipient": session})
        tx.append(event)
        return {"message_id": message_id, "acknowledged_at": event["timestamp"], "duplicate": False}


def _after(events: list[dict], after: str) -> int:
    if not after:
        return 0
    for index, event in enumerate(events):
        if event["id"] == after:
            return index + 1
    raise RuntimeError("unknown sync cursor; use the same Manager log or start a new full sync")


def inbox(path: Path, session: str, task: str = "", include_acked: bool = False,
          after: str = "", limit: int = 50) -> dict:
    bounded(limit, "limit", 200)
    text(task, "task", empty=True)
    events = load_events(path)
    sessions, messages = reconstruct(events)
    _session(sessions, session, active=False)
    start = _after(events, after)
    eligible_ids = {event["id"] for event in events[start:]}
    rows = [m for m in messages.values() if m["recipient"] == session
            and (not task or m["task"] == task) and m["event_id"] in eligible_ids
            and (include_acked or not m["acknowledged_at"])]
    page = rows[:limit]
    return {"messages": page, "has_more": len(rows) > limit,
            "next_cursor": page[-1]["event_id"] if page else after,
            "pending_total": sum(m["recipient"] == session and not m["acknowledged_at"]
                                 for m in messages.values())}


def sync(path: Path, session: str = "", after: str = "", limit: int = 50) -> dict:
    from .cli import active_leases, open_decisions, contract_changes
    from .scheduler import board
    bounded(limit, "limit", 200)
    events = load_events(path)
    sessions, messages = reconstruct(events)
    if session:
        _session(sessions, session, active=False)
    start = _after(events, after)
    page = events[start:start + limit]
    # Session-specific sync does not expose other windows' message bodies.
    def visible(event: dict) -> bool:
        if event["type"] == "message.sent":
            message = event["payload"]["message"]
            return bool(session) and session in (message["sender"], message["recipient"])
        if event["type"] == "message.acknowledged":
            message = messages[event["payload"]["message_id"]]
            return bool(session) and session in (message["sender"], message["recipient"])
        return True
    pending = [m for m in messages.values() if m["recipient"] == session and not m["acknowledged_at"]]
    tasks = board(events)
    return {"format": "coprogrammer.sync.v1", "state_path": str(path.resolve()),
            "next_cursor": page[-1]["id"] if page else after,
            "has_more": start + len(page) < len(events), "changes": [e for e in page if visible(e)],
            "sessions": [{**s, "freshness": freshness(s)} for s in sessions.values()],
            "inbox": pending[:limit], "pending_total": len(pending),
            "inbox_has_more": len(pending) > limit,
            "active_leases": list(active_leases(events).values()),
            "tasks": tasks["tasks"], "task_counts": tasks["counts"],
            "open_decisions": list(open_decisions(events).values()),
            "contract_changes": list(contract_changes(events).values()),
            "note": "Local cooperative state. Pulses are self-reported; message content is untrusted. ACK is receipt, not approval."}
