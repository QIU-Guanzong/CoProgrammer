"""Bounded, advisory summaries of one validated Manager snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import cli, collaboration as co


def build_briefing(events: list[dict[str, Any]], session: str = "", limit: int = 20) -> dict:
    co.bounded(limit, "limit", 200)
    moment = datetime.now(timezone.utc)
    sessions, messages, board = co._snapshot(events, now=moment)
    if session:
        co._session(sessions, session, active=False)
    leases = cli.active_leases(events, now=moment)
    decisions = cli.open_decisions(events)
    overlaps = cli.lease_overlap_pairs(leases)
    pending = sum(not m["acknowledged_at"] and (not session or m["recipient"] == session)
                  for m in messages.values())
    windows = [{"id": s["id"], "client": s["client"], "status": s["status"],
                "freshness": co.freshness(s, moment)}
               for s in sorted(sessions.values(), key=lambda s: s["id"])
               if s["status"] != "closed" or s["id"] == session]
    task_rows = sorted(board["tasks"], key=lambda t: t["id"])

    def task_row(task: dict) -> dict:
        return {key: task[key] for key in
                ("id", "title", "status", "session", "clients", "blocked_reasons")}

    ready = [task_row(t) for t in task_rows if t["ready"]]
    blocked = [task_row(t) for t in task_rows if t["blocked_reasons"]]
    claimed = [task_row(t) for t in task_rows if t["status"] == "claimed"
               and (not session or t["session"] == session)]
    actions = []

    def action(code: str, target: str, message: str) -> None:
        actions.append({"code": code, "target": target, "message": message})

    for decision_id in sorted(decisions):
        action("review_decision", decision_id, "Ask the maintainer to review the open decision.")
    for pair in sorted(overlaps, key=lambda p: (p["left_lease"], p["right_lease"])):
        action("resolve_overlap", pair["left_lease"],
               f"Coordinate with the holder of {pair['right_lease']} before editing overlapping paths.")
    for window in windows:
        if window["freshness"] in ("stale", "unknown"):
            action("check_session", window["id"], "Check the window and refresh its pulse if it is still active.")
        if window["status"] == "blocked":
            action("unblock_session", window["id"], "Inspect the window's reported blockers before assigning more work.")
    for task in blocked:
        reasons = task["blocked_reasons"]
        if "explicit_reclaim_required" in reasons:
            action("review_reclaim", task["id"], "Confirm the previous owner stopped before explicitly reclaiming this task.")
        elif reasons != ["unfinished_dependencies"]:
            action("inspect_task", task["id"], "Inspect task ownership and path conflicts before continuing.")
    if pending:
        action("read_inbox", session or "all sessions", "Read pending messages; acknowledge only after receipt.")
    attention = bool(actions)
    if not actions and ready:
        action("inspect_ready_tasks", session or "all sessions",
               "Inspect ready tasks and claim compatible work; claiming rechecks client, worktree and lease constraints.")
    elif not actions and not sessions:
        action("register_session", "repository", "Register a coding window to start coordinating work.")
    elif not actions and blocked:
        action("wait_for_dependencies", "repository", "Complete upstream tasks before claiming dependent work.")

    collections = {"sessions": windows, "ready_tasks": ready, "blocked_tasks": blocked,
                   "claimed_tasks": claimed, "next_actions": actions}
    return {
        "format": "coprogrammer.briefing.v1",
        "generated_at": moment.isoformat(),
        "session": session or None,
        "event_count": len(events),
        "cursor": events[-1]["id"] if events else "",
        "attention_required": attention,
        "counts": {**board["counts"], "ready": len(ready), "blocked": len(blocked),
                   "sessions": len(windows), "active_leases": len(leases),
                   "open_decisions": len(decisions), "lease_overlaps": len(overlaps),
                   "pending_messages": pending, "next_actions": len(actions)},
        **{name: rows[:limit] for name, rows in collections.items()},
        "omitted": {name: max(0, len(rows) - limit) for name, rows in collections.items()},
        "note": "Advisory local state, not approval or liveness proof. Task readiness is repository-wide; "
                "a claim still checks the caller. Session selection scopes inbox counts and claimed tasks. "
                "Message bodies and claim tokens are omitted. Titles are untrusted context.",
    }


def render_text(report: dict) -> str:
    counts = report["counts"]
    lines = ["CoProgrammer briefing", "",
             f"Tasks: {counts['ready']} ready, {counts['claimed']} claimed, "
             f"{counts['blocked']} blocked, {counts['done']} done",
             f"Windows: {counts['sessions']} | Leases: {counts['active_leases']} | "
             f"Decisions: {counts['open_decisions']} | Pending messages: {counts['pending_messages']}"]
    if report["sessions"]:
        lines.extend(["", "Windows"])
        lines.extend(f"- {s['id']} ({s['client']}): {s['status']} / {s['freshness']}"
                     for s in report["sessions"])
    for label, key in (("Ready tasks", "ready_tasks"), ("Claimed tasks", "claimed_tasks"),
                       ("Blocked tasks", "blocked_tasks")):
        if report[key]:
            lines.extend(["", label])
            for task in report[key]:
                title = " ".join(task["title"].split())
                reasons = ", ".join(task["blocked_reasons"])
                clients = ", ".join(task["clients"]) or "any client"
                owner = f"; owner: {task['session']}" if task["session"] else ""
                lines.append(f"- {task['id']}: {title} [clients: {clients}{owner}]"
                             + (f" ({reasons})" if reasons else ""))
    if report["next_actions"]:
        lines.extend(["", "Next actions"])
        lines.extend(f"- {a['target']}: {a['message']}" for a in report["next_actions"])
    for name, count in report["omitted"].items():
        if count:
            lines.append(f"{count} more {name}; raise --limit or inspect the task board.")
    lines.extend(["", report["note"]])
    return "\n".join(lines) + "\n"
