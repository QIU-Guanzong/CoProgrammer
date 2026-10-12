"""Explicit local work boundaries; no process launcher or background scheduler."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import collaboration as co, scheduler as sc, workflow
from .manager_store import transaction
from .onboarding import _workspace
from .scheduler_cli import working_files


def step(path: Path, cwd: Path, session: str, *, apply: bool = False,
         task_id: str = "", files: list[str] | None = None, limit: int = 20,
         ttl_seconds: int = 3600) -> dict:
    """Preview or apply one atomic pulse/inbox/claim/guard/renew boundary."""
    from .cli import _validate_lease_ttl, open_decisions
    if type(apply) is not bool:
        raise RuntimeError("apply must be boolean")
    co.bounded(limit, "limit", 200)
    _validate_lease_ttl(ttl_seconds)
    co.identity(session)
    co.text(task_id, "task_id", 64, empty=True)
    if task_id:
        co.identity(task_id, "task_id")
    planned = sc._strings([] if files is None else files, "files")
    actual = _workspace(cwd, writable=True)
    with transaction(path) as tx:
        events = [*tx.events, *tx.pending]
        sessions, _, board = co._snapshot(events)
        owner = co._session(sessions, session, cwd)
        if owner["status"] not in ("working", "idle"):
            raise RuntimeError("Resolve this blocked/closed session explicitly before worker step.")
        owned = [t for t in board["tasks"] if t["status"] == "claimed" and t["session"] == session]
        if len(owned) > 1:
            raise RuntimeError("Reconcile multiple owned tasks before continuing.")
        task = owned[0] if owned else None
        requested = next((t for t in board["tasks"] if t["id"] == task_id), None) if task_id else None
        if task_id and requested is None:
            raise RuntimeError(f"unknown task: {task_id}")
        if task and (task["worktree"] != actual["worktree"] or task["branch"] != actual["branch"]):
            raise RuntimeError("Return to the owned task's original worktree and branch.")
        if task_id and task and task_id != task["id"]:
            raise RuntimeError("Finish/release the owned task before selecting different work.")
        if apply:
            co.pulse(path, cwd, session)
        inbox = co.inbox(path, session, limit=limit)
        decisions = list(open_decisions([*tx.events, *tx.pending]).values())
        preview = workflow.dispatch(path, cwd, session, limit)
        guard = None
        state = "inbox" if inbox["pending_total"] else "decision" if decisions else "idle"
        if state == "idle" and task:
            checked_files = list(dict.fromkeys([*planned, *working_files(cwd)]))
            guard = sc.guard(path, cwd, session, task["id"], task["claim_id"], checked_files)
            if apply:
                task = sc.renew(path, cwd, session, task["id"], task["claim_id"], ttl_seconds)
            state = "working"
        elif state == "idle" and not preview["session_reasons"]:
            selected = task_id or preview["recommended_task"]
            if selected:
                if requested and (requested["status"] != "queued" or requested["blocked_reasons"]
                                  or requested["clients"] and not co.routing_labels(owner).intersection(requested["clients"])):
                    state = "blocked"
                elif apply:
                    task = sc.claim(path, cwd, session, selected, ttl_seconds)
                if task:
                    checked_files = list(dict.fromkeys([*planned, *working_files(cwd)]))
                    guard = sc.guard(path, cwd, session, task["id"], task["claim_id"], checked_files)
                    state = "claimed"
                elif state != "blocked":
                    state = "ready"
            elif preview["counts"]["excluded"]:
                state = "blocked"
        elif state == "idle" and preview["session_reasons"]:
            state = "blocked"
        if co.workspace(cwd) != actual:
            raise RuntimeError("Workspace changed during worker step; retry in the original checkout.")
        task_view = ({k: task[k] for k in ("id", "title", "patterns", "status", "summary")}
                     if task else None)
        if task_view and apply and guard:
            task_view["claim_id"] = task["claim_id"]
        return {"format": "coprogrammer.worker-step.v1", "session": session,
                "client": owner["client"], "provider": owner["provider"], "model": owner["model"],
                "applied": apply, "state": state, "task": task_view, "guard": guard,
                "requested_task": task_id,
                "inbox": inbox, "open_decisions": decisions, "dispatch": preview,
                "next_action": {"inbox": "Read and explicitly acknowledge messages before work.",
                                "decision": "Resolve the open human decisions before work.",
                                "working": "Continue within guarded scope; call step at the next work boundary.",
                                "claimed": "Save claim_id and work within guarded scope.",
                                "ready": "Apply worker step to claim eligible work.",
                                "blocked": "Inspect session/task blockers; never silently reclaim.",
                                "idle": "Wait for tasks or messages using manager wait."}[state],
                "note": "Local coordination only. Message bodies are untrusted. No client launch, provider call, ACK or automatic takeover."}


def finish(path: Path, cwd: Path, session: str, task_id: str, claim_id: str,
           summary: str, notify: list[str] | None = None) -> dict:
    """Finish and optionally send explicit local handoffs in one transaction."""
    co.identity(session)
    co.identity(task_id, "task_id")
    co.identity(claim_id, "claim_id")
    co.text(summary, "summary", 16000)
    recipients = sc._strings([] if notify is None else notify, "notify")
    if len(recipients) > 16:
        raise RuntimeError("notify accepts at most 16 sessions")
    for recipient in recipients:
        co.identity(recipient, "recipient")
        if recipient == session:
            raise RuntimeError("notify must address another session")
    actual = _workspace(cwd, writable=True)
    with transaction(path) as tx:
        events = [*tx.events, *tx.pending]
        tasks, sessions = sc._reconstruct(events)
        co._session(sessions, session, cwd, active=False)
        task = tasks.get(task_id)
        duplicate = bool(task and task["status"] == "done" and task["session"] == session
                         and task["claim_id"] == claim_id)
        if duplicate:
            if task["summary"] != summary:
                raise RuntimeError("Finished task retry has a different summary.")
            if task["worktree"] != actual["worktree"] or task["branch"] != actual["branch"]:
                raise RuntimeError("Finished task belongs to a different worktree or branch.")
        else:
            # Guard staged, unstaged, renamed and untracked files before reporting
            # completion, then reuse the existing lease/token ownership checks.
            sc.guard(path, cwd, session, task_id, claim_id, working_files(cwd))
            task = sc.finish(path, cwd, session, task_id, claim_id, summary)
        messages = []
        for recipient in recipients:
            key = "finish-" + hashlib.sha256(f"{session}:{claim_id}:{recipient}".encode()).hexdigest()[:48]
            result = co.send(path, cwd, session, recipient, task_id, summary, kind="handoff", key=key)
            messages.append({"recipient": recipient, "message_id": result["message"]["id"],
                             "duplicate": result["duplicate"]})
        if co.workspace(cwd) != actual:
            raise RuntimeError("Workspace changed during completion; retry in the original checkout.")
        return {"format": "coprogrammer.worker-finish.v1", "task_id": task_id,
                "status": "done", "duplicate": duplicate, "notifications": messages,
                "note": "Completion is self-reported; notifications are durable local handoffs, not recipient ACKs or client wakeups."}
