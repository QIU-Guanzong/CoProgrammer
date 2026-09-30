"""Cooperative task dispatch across local client windows sharing a Manager log.

Claims reserve path leases atomically. Tokens fence stale owners; lease expiry
never hands work to another window without an explicit creator reclaim. These
checks coordinate cooperating clients, rather than preventing filesystem writes.
"""
from __future__ import annotations

import fnmatch
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import collaboration as co
from .manager_store import transaction

EVENT_TYPES = ("task.created", "task.claimed", "task.renewed", "task.finished",
               "task.released", "task.reclaimed")
FIELDS = {"id", "title", "creator", "patterns", "depends_on", "clients", "created_at",
          "updated_at", "status", "session", "claim_id", "lease_id", "worktree", "branch", "summary"}
IMMUTABLE = ("id", "title", "creator", "patterns", "depends_on", "clients", "created_at")
CLAIM_FIELDS = ("session", "claim_id", "lease_id", "worktree", "branch")


def _strings(value: Any, name: str, *, required: bool = False) -> list[str]:
    if (not isinstance(value, list) or len(value) > 128 or (required and not value)
            or any(not isinstance(v, str) or not v.strip() for v in value)):
        raise RuntimeError(f"invalid {name}: expected {'nonempty ' if required else ''}list of strings")
    if len(set(value)) != len(value):
        raise RuntimeError(f"duplicate {name}")
    return value


def _patterns(value: Any) -> list[str]:
    from .cli import normalize_path_pattern
    return [normalize_path_pattern(co.text(v, "pattern", 4096))
            for v in _strings(value, "patterns", required=True)]


def validate_event(event: dict[str, Any]) -> None:
    kind, payload = event["type"], event.get("payload", {})
    if kind not in EVENT_TYPES:
        return
    record = payload.get("task")
    if set(payload) != {"task"} or not isinstance(record, dict) or set(record) != FIELDS:
        raise RuntimeError("invalid task record")
    co.timestamp(event["timestamp"])
    for name in ("id", "creator"):
        co.identity(record[name], name)
    co.text(record["title"], "title", 2000)
    for dependency in _strings(record["depends_on"], "depends_on"):
        co.identity(dependency, "dependency")
    if record["id"] in record["depends_on"]:
        raise RuntimeError("task cannot depend on itself")
    clients = _strings(record["clients"], "clients")
    for client in clients:
        co.text(client, "client", 256)
        if client != client.strip().casefold():
            raise RuntimeError("task clients must be normalized")
    if _patterns(record["patterns"]) != record["patterns"]:
        raise RuntimeError("task patterns must be normalized")
    if len(set(record["patterns"])) != len(record["patterns"]):
        raise RuntimeError("duplicate patterns")
    for name in ("created_at", "updated_at"):
        co.timestamp(record[name])
    if (record["updated_at"] != event["timestamp"]
            or co.timestamp(record["created_at"]) > co.timestamp(record["updated_at"])
            or event["subject"] != f"task:{record['id']}"):
        raise RuntimeError("task timestamp or subject mismatch")
    if record["status"] not in ("queued", "claimed", "done"):
        raise RuntimeError("invalid task status")
    for name in CLAIM_FIELDS:
        co.text(record[name], name, 4096, empty=record["status"] == "queued" or name == "branch")
    co.text(record["summary"], "summary", 16000, empty=True)
    if record["status"] == "queued":
        if any(record[name] != "" for name in CLAIM_FIELDS):
            raise RuntimeError("queued task cannot retain a claim")
    else:
        for name in ("session", "claim_id", "lease_id"):
            co.identity(record[name], name)
        if record["branch"] == "HEAD":
            raise RuntimeError("task claims require a named Git branch; detached HEAD is unsupported")
    expected_status = {"task.created": "queued", "task.claimed": "claimed", "task.renewed": "claimed",
                       "task.finished": "done", "task.released": "queued", "task.reclaimed": "queued"}[kind]
    if record["status"] != expected_status:
        raise RuntimeError("task event status mismatch")
    if kind in ("task.created", "task.reclaimed") and event["actor"] != record["creator"]:
        raise RuntimeError("task creator mismatch")
    if kind in ("task.claimed", "task.renewed", "task.finished") and event["actor"] != record["session"]:
        raise RuntimeError("task owner mismatch")
    if kind in ("task.finished", "task.released", "task.reclaimed"):
        co.text(record["summary"], "summary", 16000)


def _live(leases: dict, moment: datetime) -> dict:
    from .cli import lease_expiry
    return {key: lease for key, lease in leases.items()
            if (expiry := lease_expiry(lease)) is None or expiry > moment}


def _lease_matches(task: dict, lease: dict | None) -> bool:
    return bool(lease and lease.get("holder") == task["session"]
                and lease.get("task") == task["id"]
                and lease.get("scope") == {"kind": "path", "patterns": task["patterns"]})


def _ready_session(sessions: dict, session: str, cwd: Path | None = None,
                   moment: datetime | None = None) -> dict:
    record = co._session(sessions, session, cwd)
    if record["status"] not in ("working", "idle") or co.freshness(record, moment) != "fresh":
        raise RuntimeError("task operations require a fresh working or idle session; pulse first")
    return record


def _reconstruct(events: list[dict[str, Any]], *, collaboration_validated: bool = False) -> tuple[dict, dict]:
    # Validate collaboration history even if a malformed event is unrelated to
    # the requested task. Then replay immutable session identities at each event.
    # A combined snapshot has already validated this exact event sequence. The
    # flag is private and scoped to that call, never cached across transactions.
    if not collaboration_validated:
        co.reconstruct(events)
    tasks: dict[str, dict] = {}
    sessions: dict[str, dict] = {}
    leases: dict[str, dict] = {}
    tokens: set[str] = set()
    for event in events:
        kind, payload = event["type"], event.get("payload", {})
        if kind in ("session.registered", "session.updated"):
            sessions[payload["session"]["id"]] = payload["session"]
        elif kind == "lease.granted":
            leases[payload["lease"]["id"]] = payload["lease"]
        elif kind == "lease.released":
            leases.pop(payload["lease_id"], None)
        if kind not in EVENT_TYPES:
            continue
        validate_event(event)
        task = dict(payload["task"])
        previous = tasks.get(task["id"])
        moment = co.timestamp(event["timestamp"])
        actor = _ready_session(sessions, event["actor"], moment=moment)
        live = _live(leases, moment)
        if kind == "task.created":
            if previous or task["created_at"] != task["updated_at"] or task["summary"]:
                raise RuntimeError("invalid duplicate task creation history")
            if any(dep not in tasks for dep in task["depends_on"]):
                raise RuntimeError("task dependencies must already exist")
        else:
            if not previous or any(previous[key] != task[key] for key in IMMUTABLE):
                raise RuntimeError("invalid task identity or immutable fields in history")
            if moment < co.timestamp(previous["updated_at"]):
                raise RuntimeError("task history runs backwards")
            if kind == "task.claimed":
                if previous["status"] != "queued" or task["claim_id"] in tokens:
                    raise RuntimeError("invalid task claim history")
                _ready_session(sessions, event["actor"], moment=moment)
                if (any(tasks[dep]["status"] != "done" for dep in task["depends_on"])
                        or (task["clients"] and actor["client"].strip().casefold() not in task["clients"])):
                    raise RuntimeError("task dependencies or client restriction not satisfied")
                if task["worktree"] != actor["worktree"] or task["summary"]:
                    raise RuntimeError("invalid task worktree or claim summary")
                if any(t["status"] == "claimed" and (t["session"] == task["session"]
                       or t["worktree"] == task["worktree"]) for t in tasks.values()):
                    raise RuntimeError("session or worktree already owns a claimed task")
                tokens.add(task["claim_id"])
            else:
                if previous["status"] != "claimed":
                    raise RuntimeError("task history requires an existing claim")
                if kind == "task.reclaimed":
                    if previous["lease_id"] in live:
                        raise RuntimeError("cannot reclaim a task with an active lease")
                else:
                    if event["actor"] != previous["session"]:
                        raise RuntimeError("task history actor is not claim owner")
                    _ready_session(sessions, event["actor"], moment=moment)
                    if kind != "task.released" and any(previous[k] != task[k] for k in CLAIM_FIELDS):
                        raise RuntimeError("task claim identity changed in history")
                    if kind == "task.renewed" and task["summary"] != previous["summary"]:
                        raise RuntimeError("task renewal changed summary")
            if kind != "task.reclaimed":
                claimed = task if kind == "task.claimed" else previous
                if not _lease_matches(claimed, live.get(claimed["lease_id"])):
                    raise RuntimeError("task claim has no matching active lease in history")
                if _conflicts(claimed, {key: lease for key, lease in live.items()
                                       if key != claimed["lease_id"]}):
                    raise RuntimeError("task claim has conflicting leases in history")
        tasks[task["id"]] = task
    return tasks, sessions


def _append(tx: Any, kind: str, actor: str, task: dict) -> dict:
    from .cli import make_event
    event = make_event(kind, actor, f"task:{task['id']}")
    # A second-rounded timestamp can appear before a lease that expired during
    # that same second, making a legitimate reclaim fail its later replay.
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    record = {**task, "updated_at": event["timestamp"]}
    if kind == "task.created":
        record["created_at"] = event["timestamp"]
    event["payload"] = {"task": record}
    validate_event(event)
    _reconstruct([*tx.events, *tx.pending, event])
    tx.append(event)
    return record


def create(path: Path, cwd: Path, session: str, task_id: str, title: str,
           patterns: list[str], depends_on: list[str] | None = None,
           clients: list[str] | None = None) -> dict:
    task = {"id": task_id, "title": title, "creator": session, "patterns": _patterns(patterns),
            "depends_on": [] if depends_on is None else depends_on,
            "clients": [v.strip().casefold() for v in _strings([] if clients is None else clients, "clients")],
            "created_at": "", "updated_at": "", "status": "queued", "summary": "",
            **{key: "" for key in CLAIM_FIELDS}}
    with transaction(path) as tx:
        tasks, sessions = _reconstruct([*tx.events, *tx.pending])
        _ready_session(sessions, session, cwd)
        co.identity(task_id, "task_id")
        if task_id in tasks:
            raise RuntimeError("task ID already exists")
        for dep in _strings(task["depends_on"], "depends_on"):
            if dep not in tasks:
                raise RuntimeError("task dependencies must already exist")
        return _append(tx, "task.created", session, task)


def _conflicts(task: dict, leases: dict) -> list[str]:
    from .cli import lease_scopes_overlap
    scope = {"kind": "path", "patterns": task["patterns"]}
    return [key for key, lease in leases.items() if lease_scopes_overlap(scope, lease["scope"])]


def claim(path: Path, cwd: Path, session: str, task_id: str = "", ttl_seconds: int = 3600) -> dict:
    from .cli import active_leases, request_lease, _validate_lease_ttl
    _validate_lease_ttl(ttl_seconds)
    co.text(task_id, "task_id", 64, empty=True)
    if task_id:
        co.identity(task_id, "task_id")
    with transaction(path) as tx:
        events = [*tx.events, *tx.pending]
        tasks, sessions = _reconstruct(events)
        owner = _ready_session(sessions, session, cwd)
        actual = co.workspace(cwd)
        if actual["branch"] == "HEAD":
            raise RuntimeError("task claims require a named Git branch; detached HEAD is unsupported")
        if any(t["status"] == "claimed" and (t["session"] == session or t["worktree"] == actual["worktree"])
               for t in tasks.values()):
            raise RuntimeError("session or worktree already owns a claimed task; finish, release or reclaim it first")
        if task_id and task_id not in tasks:
            raise RuntimeError(f"unknown task: {task_id}")
        leases = active_leases(events)
        for task in tasks.values():
            if task_id and task["id"] != task_id:
                continue
            reasons = []
            if task["status"] != "queued":
                reasons.append("task is not queued")
            if any(tasks[dep]["status"] != "done" for dep in task["depends_on"]):
                reasons.append("unfinished dependencies")
            if task["clients"] and owner["client"].strip().casefold() not in task["clients"]:
                reasons.append("client is not eligible")
            if _conflicts(task, leases):
                reasons.append("path lease conflict")
            if reasons:
                if task_id:
                    raise RuntimeError("cannot claim task: " + "; ".join(reasons))
                continue
            result = request_lease(path, session, "path", task["patterns"], task["id"],
                                   f"task:{task['id']}", ttl_seconds)
            if not result["granted"]:
                raise RuntimeError("path lease conflict")
            return _append(tx, "task.claimed", session,
                           {**task, "status": "claimed", "session": session,
                            "claim_id": f"claim_{uuid4().hex}", "lease_id": result["lease"]["id"],
                            "worktree": actual["worktree"], "branch": actual["branch"], "summary": ""})
        raise RuntimeError("no ready compatible queued task")


def _owned(events: list, cwd: Path, session: str, task_id: str, claim_id: str) -> dict:
    from .cli import active_leases
    co.identity(task_id, "task_id")
    co.identity(claim_id, "claim_id")
    tasks, sessions = _reconstruct(events)
    _ready_session(sessions, session, cwd)
    task = tasks.get(task_id)
    if not task or task["status"] != "claimed" or task["session"] != session or task["claim_id"] != claim_id:
        raise RuntimeError("task claim token is no longer owned by this session")
    actual = co.workspace(cwd)
    if actual["branch"] == "HEAD":
        raise RuntimeError("task claims require a named Git branch; detached HEAD is unsupported")
    if task["worktree"] != actual["worktree"] or task["branch"] != actual["branch"]:
        raise RuntimeError("task claim belongs to a different worktree or branch")
    leases = active_leases(events)
    if not _lease_matches(task, leases.get(task["lease_id"])):
        raise RuntimeError("task lease expired or missing; creator must explicitly reclaim")
    if _conflicts(task, {key: lease for key, lease in leases.items() if key != task["lease_id"]}):
        raise RuntimeError("task lease conflicts with another active lease")
    return task


def renew(path: Path, cwd: Path, session: str, task_id: str, claim_id: str,
          ttl_seconds: int = 3600) -> dict:
    from .cli import renew_lease
    with transaction(path) as tx:
        task = _owned([*tx.events, *tx.pending], cwd, session, task_id, claim_id)
        renew_lease(path, task["lease_id"], session, ttl_seconds, f"task:{task_id}")
        return _append(tx, "task.renewed", session, task)


def _end(path: Path, cwd: Path, session: str, task_id: str, claim_id: str,
         summary: str, *, done: bool) -> dict:
    from .cli import release_lease
    co.text(summary, "summary", 16000)
    with transaction(path) as tx:
        task = _owned([*tx.events, *tx.pending], cwd, session, task_id, claim_id)
        record = {**task, "status": "done" if done else "queued", "summary": summary}
        if not done:
            record.update({key: "" for key in CLAIM_FIELDS})
        result = _append(tx, "task.finished" if done else "task.released", session, record)
        release_lease(path, task["lease_id"], session, f"task:{task_id}")
        return result


def finish(path: Path, cwd: Path, session: str, task_id: str, claim_id: str, summary: str) -> dict:
    return _end(path, cwd, session, task_id, claim_id, summary, done=True)


def release(path: Path, cwd: Path, session: str, task_id: str, claim_id: str, summary: str) -> dict:
    return _end(path, cwd, session, task_id, claim_id, summary, done=False)


def reclaim(path: Path, cwd: Path, session: str, task_id: str, summary: str) -> dict:
    from .cli import active_leases
    co.identity(task_id, "task_id")
    co.text(summary, "summary", 16000)
    with transaction(path) as tx:
        events = [*tx.events, *tx.pending]
        tasks, sessions = _reconstruct(events)
        _ready_session(sessions, session, cwd)
        task = tasks.get(task_id)
        if not task or task["creator"] != session or task["status"] != "claimed":
            raise RuntimeError("only the creator can reclaim a claimed task")
        if task["lease_id"] in active_leases(events):
            raise RuntimeError("cannot reclaim a task with an active lease")
        return _append(tx, "task.reclaimed", session, {**task, "status": "queued", "summary": summary,
                                                       **{key: "" for key in CLAIM_FIELDS}})


def guard(path: Path, cwd: Path, session: str, task_id: str, claim_id: str,
          files: list[str] | None = None) -> dict:
    from .cli import normalize_path_pattern
    planned = _strings([] if files is None else files, "files")
    with transaction(path) as tx:
        task = _owned([*tx.events, *tx.pending], cwd, session, task_id, claim_id)
        normalized = []
        root = Path(task["worktree"]).resolve()
        patterns = [unicodedata.normalize("NFC", p).casefold() for p in task["patterns"]]
        for name in planned:
            # Concrete file names are not lease-pattern syntax. On POSIX a
            # backslash is a literal filename character, so converting it to a
            # separator can approve a different, out-of-scope file.
            if "\\" in name:
                raise RuntimeError("guard files must use forward-slash repository-relative paths")
            relative = normalize_path_pattern(name)
            if any(char in relative for char in "*?["):
                raise RuntimeError("guard files must be literal repository-relative paths")
            try:
                resolved = (root / relative).resolve().relative_to(root).as_posix()
            except ValueError as exc:
                raise RuntimeError("guard file resolves outside the worktree") from exc
            folded = unicodedata.normalize("NFC", relative).casefold()
            if not any(fnmatch.fnmatchcase(folded, pattern) for pattern in patterns):
                raise RuntimeError(f"file is outside task scope: {name}")
            resolved_folded = unicodedata.normalize("NFC", resolved).casefold()
            if not any(fnmatch.fnmatchcase(resolved_folded, pattern) for pattern in patterns):
                raise RuntimeError(f"file resolves outside task scope: {name}")
            normalized.append(relative)
        return {"allowed": True, "task_id": task_id, "claim_id": claim_id,
                "lease_id": task["lease_id"], "files": normalized}


def board(events: list[dict[str, Any]]) -> dict:
    return _board(events)


def _board(events: list[dict[str, Any]], *, collaboration_validated: bool = False,
           now: datetime | None = None) -> dict:
    from .cli import active_leases
    tasks, sessions = _reconstruct(events, collaboration_validated=collaboration_validated)
    leases = active_leases(events) if now is None else active_leases(events, now=now)
    records = []
    counts = {"queued": 0, "claimed": 0, "done": 0}
    for task in tasks.values():
        reasons = []
        lease_status = "unclaimed"
        if task["status"] == "queued":
            if any(tasks[dep]["status"] != "done" for dep in task["depends_on"]):
                reasons.append("unfinished_dependencies")
            if _conflicts(task, leases):
                reasons.append("path_lease_conflict")
        elif task["status"] == "claimed":
            lease_status = "active" if _lease_matches(task, leases.get(task["lease_id"])) else "expired_or_missing"
            if lease_status != "active":
                reasons.append("explicit_reclaim_required")
            if _conflicts(task, {key: lease for key, lease in leases.items() if key != task["lease_id"]}):
                reasons.append("path_lease_conflict")
            owner = sessions[task["session"]]
            if co.freshness(owner, now) != "fresh" or owner["status"] not in ("working", "idle"):
                reasons.append("owner_unavailable")
        counts[task["status"]] += 1
        records.append({**task, "blocked_reasons": reasons, "lease_status": lease_status,
                        "ready": task["status"] == "queued" and not reasons})
    return {"tasks": records, "counts": counts}
