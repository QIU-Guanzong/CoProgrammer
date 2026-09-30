"""Portable read-only communication: bounded waiting and task conversations.

These operations read the same Manager as the CLI/MCP collaboration tools. They
never wake a client, acknowledge a message, renew a lease, or refresh a pulse.
An unacknowledged inbox item returns immediately even after its event was seen;
the recipient must explicitly acknowledge receipt before waiting for new work.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from . import collaboration as co
from .manager_store import load_events, transaction

MAX_WAIT_SECONDS = 25
POLL_SECONDS = 0.1


def _state(snapshot: dict) -> str:
    """Watch derived expiry state as well as persisted events.

    A lease can expire, a session can become stale, and a task claim can become
    unavailable without appending an event. Exclude cursors and unread counts so
    consuming hidden message pages does not itself look like a relevant change.
    """
    return json.dumps({key: snapshot.get(key, [])
                       for key in ("sessions", "active_leases", "tasks")},
                      sort_keys=True, ensure_ascii=True)


def wait(path: Path, session: str, after: str, timeout_seconds: float = 25,
         limit: int = 50) -> dict:
    """Wait for this session's messages or shared coordination changes.

    Start with a normal sync and drain its pages, then pass its next_cursor here.
    Each poll reads at most one event page. Hidden-only pages advance the global
    cursor but do not wake the caller; polling is paced even under unrelated
    traffic. A timeout can still have has_more=true; resume from next_cursor.
    Polling and lock acquisition share a monotonic deadline. Reading/validating
    the current log itself takes additional finite processing time.
    """
    co.identity(session)
    co.text(after, "after cursor", 256)
    co.bounded(limit, "limit", 200)
    if (type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or not 0 <= timeout_seconds <= MAX_WAIT_SECONDS):
        raise RuntimeError("timeout_seconds must be a finite number between 0 and 25")
    deadline = time.monotonic() + timeout_seconds
    baseline = None
    cursor = after
    while True:
        # Restrict lock contention to the same deadline. The nested sync read
        # reuses this transaction; no lock is held during the sleep below.
        remaining = max(0.0, deadline - time.monotonic())
        with transaction(path, timeout=remaining):
            snapshot = co.sync(path, session=session, after=cursor, limit=limit)
        current = _state(snapshot)
        if snapshot["changes"] or (baseline is not None and current != baseline):
            status = "changed"
        elif snapshot["pending_total"]:
            status = "pending"
        elif time.monotonic() >= deadline:
            status = "timeout"
        else:
            baseline = current
            cursor = snapshot["next_cursor"]
            time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))
            continue
        return {**snapshot, "wait_status": status, "cursor": snapshot["next_cursor"]}


def thread(path: Path, session: str, task: str, after: str = "",
           limit: int = 50) -> dict:
    """Read sent and received task messages, with their current ACK state.

    Pages follow original send-event order, not acknowledgement time. Sync/wait
    supply later acknowledgement events for messages in already-read pages.
    This is participant filtering within a trusted local store, not access
    control against callers that can read the underlying log.
    """
    co.identity(session)
    co.text(task, "task")
    co.text(after, "after cursor", 256, empty=True)
    co.bounded(limit, "limit", 200)
    events = load_events(path)
    sessions, messages = co.reconstruct(events)
    co._session(sessions, session, active=False)
    start = co._after(events, after)
    eligible = {event["id"] for event in events[start:]}
    conversation = [message for message in messages.values()
                    if message["task"] == task
                    and session in (message["sender"], message["recipient"])]
    rows = [message for message in conversation if message["event_id"] in eligible]
    page = rows[:limit]
    return {"format": "coprogrammer.thread.v1", "session": session, "task": task,
            "messages": page, "total": len(conversation), "has_more": len(rows) > limit,
            "next_cursor": page[-1]["event_id"] if page else after}
