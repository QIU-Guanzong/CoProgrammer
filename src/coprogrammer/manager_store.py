"""Locked, atomic Manager event storage shared by cooperating local processes.

The lock file is separate from the log so replacing the log cannot invalidate
another writer's lock. Transactions validate the complete log before mutation;
commits use a same-directory temporary file so failed writes leave it intact.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
_LOCAL = threading.local()
DEFAULT_LOCK_TIMEOUT = 10.0


def _reject_nonfinite(value: str) -> None:
    raise ValueError("non-finite JSON numbers are not allowed")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _reject_nonfinite(value)
    return number


def _validate_event(event: Any, line_number: int) -> None:
    label = f"invalid event log entry at line {line_number}"
    if not isinstance(event, dict):
        raise RuntimeError(f"{label}: expected object")
    for name in ("id", "type", "timestamp", "actor", "subject"):
        if not isinstance(event.get(name), str) or not event[name]:
            raise RuntimeError(f"{label}: expected nonempty {name}")
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label}: expected object payload")
    if event["type"].startswith("task."):
        from .scheduler import validate_event
        try:
            validate_event(event)
        except RuntimeError as exc:
            raise RuntimeError(f"{label}: {exc}") from exc
    if event["type"] in ("session.registered", "session.updated", "message.sent", "message.acknowledged"):
        from .collaboration import validate_event
        try:
            validate_event(event)
        except RuntimeError as exc:
            raise RuntimeError(f"{label}: {exc}") from exc
    record_field = {
        "agent.heartbeat": "heartbeat",
        "decision.requested": "decision",
        "contract.change.proposed": "contract_change",
    }.get(event["type"])
    # Older events can omit these records; reducers already use an empty object
    # in that case. Explicit nonobjects must not poison later status queries.
    if record_field is not None and record_field in payload:
        record = payload[record_field]
        if not isinstance(record, dict):
            raise RuntimeError(f"{label}: expected object {record_field}")
        identity = "agent" if record_field == "heartbeat" else "id"
        if identity in record and not isinstance(record[identity], str):
            raise RuntimeError(f"{label}: expected string {record_field}.{identity}")
    if (event["type"] == "decision.recorded" and "decision_id" in payload
            and not isinstance(payload["decision_id"], str)):
        raise RuntimeError(f"{label}: expected string decision_id")
    if event["type"] in ("lease.requested", "lease.granted"):
        lease = payload.get("lease")
        if not isinstance(lease, dict):
            raise RuntimeError(f"{label}: expected lease object")
        scope = lease.get("scope")
        if (not isinstance(lease.get("id"), str) or not lease["id"]
                or not isinstance(lease.get("holder"), str) or not lease["holder"]
                or not isinstance(scope, dict)
                or scope.get("kind") not in ("path", "contract", "test_surface", "integration_branch")
                or not isinstance(scope.get("patterns"), list)
                or not scope["patterns"]
                or any(not isinstance(p, str) or not p for p in scope["patterns"])):
            raise RuntimeError(f"{label}: malformed lease scope or identity")
        if "expires_at" in lease:
            try:
                expires = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
                if expires.tzinfo is None:
                    raise ValueError("timezone required")
            except (AttributeError, TypeError, ValueError) as exc:
                raise RuntimeError(f"{label}: invalid lease expires_at") from exc
    elif event["type"] == "lease.released":
        if not isinstance(payload.get("lease_id"), str) or not payload["lease_id"]:
            raise RuntimeError(f"{label}: expected lease_id")


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line, parse_constant=_reject_nonfinite, parse_float=_finite_float)
                except (ValueError, RecursionError) as exc:
                    raise RuntimeError(f"invalid event log JSON at line {number}: {exc}") from exc
                _validate_event(event, number)
                events.append(event)
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"cannot read Manager event log {path}: {exc}") from exc
    return events


class EventTransaction:
    def __init__(self, path: Path):
        self.path = path
        self.events = _read(path)
        self.pending: list[dict[str, Any]] = []
        self.failed = False

    def append(self, event: dict[str, Any]) -> None:
        line_number = len(self.events) + len(self.pending) + 1
        _validate_event(event, line_number)
        # Snapshot mutable inputs before callers update a requested lease to active.
        try:
            snapshot = json.loads(json.dumps(event, ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError, RecursionError) as exc:
            raise RuntimeError(f"invalid event log JSON at line {line_number}: {exc}") from exc
        self.pending.append(snapshot)

    def commit(self) -> None:
        if self.failed:
            raise RuntimeError("Manager transaction aborted by a nested operation")
        if not self.pending:
            return
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=f".{self.path.name}.", delete=False) as handle:
                temporary = handle.name
                for event in [*self.events, *self.pending]:
                    handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except (OSError, TypeError, ValueError, RecursionError) as exc:
            raise RuntimeError(f"cannot commit Manager event log {self.path}: {exc}") from exc
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)


def _lock(handle: Any, deadline: float) -> None:
    while True:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except (BlockingIOError, OSError) as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError("timed out waiting for Manager event lock") from exc
            time.sleep(0.02)


def _unlock(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def transaction(path: Path, timeout: float = DEFAULT_LOCK_TIMEOUT) -> Iterator[EventTransaction]:
    path = path.resolve()
    key = str(path)
    active = getattr(_LOCAL, "active", {})
    if key in active:
        current = active[key]
        try:
            yield current
        except BaseException:
            current.failed = True
            raise
        return
    with _LOCKS_GUARD:
        guard = _LOCKS.setdefault(key, threading.RLock())
    deadline = time.monotonic() + timeout
    if not guard.acquire(timeout=timeout):
        raise RuntimeError("timed out waiting for Manager thread lock")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_name(path.name + ".lock").open("a+b") as handle:
            # Windows permits locking beyond EOF. Bootstrap writes before the
            # byte lock can conflict with another owner; keep even a new lock
            # file empty and acquire ownership before accessing Manager state.
            _lock(handle, deadline)
            try:
                current = EventTransaction(path)
                active[key] = current
                _LOCAL.active = active
                try:
                    yield current
                    current.commit()
                finally:
                    active.pop(key, None)
            finally:
                _unlock(handle)
    except OSError as exc:
        raise RuntimeError(f"cannot access Manager state {path}: {exc}") from exc
    finally:
        guard.release()


def append_event(path: Path, event: dict[str, Any]) -> None:
    with transaction(path) as current:
        current.append(event)


def load_events(path: Path) -> list[dict[str, Any]]:
    with transaction(path) as current:
        return [*current.events, *current.pending]
