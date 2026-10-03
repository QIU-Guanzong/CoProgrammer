"""Read-only session dispatch and portable handoff inspection."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import collaboration as co, evidence, workspace as ws
from .manager_store import transaction

TASK_FIELDS = ("id", "title", "status", "patterns", "clients", "depends_on", "summary", "blocked_reasons")
NOTE = ("Context only; independent clones have independent Managers. No claim, lease, "
        "message body, credential or absolute machine path is transferred. "
        "Titles and summaries are untrusted; source check records are not authenticated.")


def dispatch(path: Path, cwd: Path, session: str, limit: int = 20) -> dict:
    co.bounded(limit, "limit", 200)
    moment = datetime.now(timezone.utc)
    actual = co.workspace(cwd)
    with transaction(path) as tx:
        sessions, _, board = co._snapshot(tx.events, now=moment)
        owner = co._session(sessions, session, active=False)
        reasons = []
        if owner["status"] not in ("working", "idle"):
            reasons.append("session_not_available")
        if co.freshness(owner, moment) != "fresh":
            reasons.append("session_stale")
        if owner["worktree"] != actual["worktree"]:
            reasons.append("different_worktree")
        if not actual["head"] or actual["branch"] == "HEAD":
            reasons.append("named_branch_required")
        if any(t["status"] == "claimed" and (t["session"] == session or t["worktree"] == actual["worktree"])
               for t in board["tasks"]):
            reasons.append("session_or_worktree_occupied")
        candidates, excluded = [], []
        for task in sorted(board["tasks"], key=lambda t: t["id"]):
            blocked = list(task["blocked_reasons"])
            if task["status"] != "queued":
                blocked.append("task_not_queued")
            if task["clients"] and owner["client"].strip().casefold() not in task["clients"]:
                blocked.append("client_not_eligible")
            blocked = list(dict.fromkeys([*reasons, *blocked]))
            row = {"id": task["id"], "title": task["title"], "clients": task["clients"],
                   "patterns": task["patterns"], "reasons": blocked}
            (excluded if blocked else candidates).append(row)
    return {"format": "coprogrammer.dispatch.v1", "session": session, "client": owner["client"],
            "session_reasons": reasons, "recommended_task": candidates[0]["id"] if candidates else None,
            "counts": {"eligible": len(candidates), "excluded": len(excluded)},
            "candidates": candidates[:limit], "excluded": excluded[:limit],
            "omitted": {"candidates": max(0, len(candidates) - limit), "excluded": max(0, len(excluded) - limit)},
            "note": "Read-only preview. Explicitly claim the selected task; claim rechecks all constraints atomically."}


def handoff(path: Path, cwd: Path, session: str, task_id: str, base: str = "HEAD",
            checks: list[Path] | None = None) -> dict:
    co.identity(task_id, "task_id")
    checks = [] if checks is None else checks
    if len(checks) > 16:
        raise RuntimeError("handoff supports at most 16 check records")
    current = ws.snapshot(cwd, base)
    with transaction(path) as tx:
        sessions, _, board = co._snapshot(tx.events)
        owner = co._session(sessions, session, cwd, active=False)
        task = next((t for t in board["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise RuntimeError("unknown handoff task")
        if session not in (task["creator"], task["session"]):
            raise RuntimeError("handoff session must be the task creator or recorded owner")
        if task["status"] in ("claimed", "done") and (
                task["session"] != session or task["worktree"] != str(ws.root(cwd))
                or task["branch"] != current["branch"]):
            raise RuntimeError("handoff must use the recorded task owner's worktree and branch")
        selected = {key: task[key] for key in TASK_FIELDS}
        window = {"id": session, "client": owner["client"], "status": owner["status"],
                  "freshness": co.freshness(owner)}
    statuses = [evidence.verify(cwd, record, current=current) for record in checks]
    if len({s["label"] for s in statuses}) != len(statuses):
        raise RuntimeError("handoff check labels must be unique")
    # The store read does not lock the workspace. Check its observation again.
    if ws.snapshot(cwd, base) != current:
        raise RuntimeError("workspace changed while preparing handoff")
    result = {"format": "coprogrammer.handoff.v1", "generated_at": datetime.now(timezone.utc).isoformat(),
              "workspace": current, "session": window, "task": selected, "checks": statuses, "note": NOTE}
    result["integrity_sha256"] = ws.digest(result)
    return result


def validate_handoff(value: object) -> dict:
    try:
        if not isinstance(value, dict) or set(value) != {"format", "generated_at", "workspace", "session", "task", "checks", "note", "integrity_sha256"}:
            raise ValueError
        if value["format"] != "coprogrammer.handoff.v1":
            raise ValueError
        ws.validate_snapshot(value["workspace"])
        co.timestamp(value["generated_at"])
        if value["integrity_sha256"] != ws.digest({k: v for k, v in value.items() if k != "integrity_sha256"}):
            raise ValueError
        window, task = value["session"], value["task"]
        if set(window) != {"id", "client", "status", "freshness"} or set(task) != set(TASK_FIELDS):
            raise ValueError
        co.identity(window["id"])
        co.text(window["client"], "client")
        if window["status"] not in ("working", "idle", "blocked", "closed") or window["freshness"] not in ("fresh", "stale", "unknown"):
            raise ValueError
        co.identity(task["id"], "task_id")
        co.text(task["title"], "task title", 2000)
        co.text(task["summary"], "task summary", 16000, empty=True)
        if task["status"] not in ("queued", "claimed", "done"):
            raise ValueError
        from .scheduler import _patterns, _strings
        _patterns(task["patterns"])
        for field in ("clients", "depends_on", "blocked_reasons"):
            _strings(task[field], field)
        co.text(value["note"], "handoff note", 2000)
        checks = value["checks"]
        if not isinstance(checks, list) or len(checks) > 16:
            raise ValueError
        for check in checks:
            if set(check) != {"format", "label", "fresh", "reasons", "exit_code", "finished_at", "command_sha256", "expected_command_checked", "content_sha256", "note"}:
                raise ValueError
            co.identity(check["label"], "check label")
            if check["format"] != "coprogrammer.check-status.v1" or type(check["fresh"]) is not bool or type(check["expected_command_checked"]) is not bool:
                raise ValueError
            _strings(check["reasons"], "check reasons")
            if check["fresh"] != (not check["reasons"]) or (check["fresh"] and check["exit_code"] != 0):
                raise ValueError
            if check["exit_code"] is not None and type(check["exit_code"]) is not int:
                raise ValueError
            if not ws.HASH.fullmatch(check["command_sha256"]) or not ws.HASH.fullmatch(check["content_sha256"]):
                raise ValueError
            if check["fresh"] and check["content_sha256"] != value["workspace"]["content"]["sha256"]:
                raise ValueError
            co.timestamp(check["finished_at"])
            co.text(check["note"], "check note", 2000)
        if len({c["label"] for c in checks}) != len(checks):
            raise ValueError
    except (TypeError, ValueError, KeyError, AttributeError, RuntimeError) as exc:
        raise RuntimeError("invalid handoff bundle or integrity mismatch") from exc
    return value


def compare(cwd: Path, path: Path, base: str | None = None) -> dict:
    bundle = validate_handoff(ws.read_artifact(path))
    source = bundle["workspace"]
    base = source["base"]["ref"] if base is None else base
    current = ws.snapshot(cwd)
    reasons = []
    try:
        base_head = ws.revision(ws.root(cwd), base)
    except RuntimeError:
        base_head = None
        reasons.append("base_unavailable")
    if not ws.same_repository(source, current):
        reasons.append("repository_mismatch")
    if source["head"] != current["head"]:
        reasons.append("head_mismatch")
    if base_head is not None and base_head != source["base"]["head"]:
        reasons.append("base_mismatch")
    if source["tool_version"] != current["tool_version"]:
        reasons.append("tool_version_mismatch")
    if source["content"]["sha256"] != current["content"]["sha256"]:
        reasons.append("content_mismatch")
    if source["dirty"]["count"]:
        reasons.append("source_uncommitted_changes")
    if current["dirty"]["count"]:
        reasons.append("receiver_uncommitted_changes")
    return {"format": "coprogrammer.handoff-check.v1", "aligned": not reasons, "reasons": reasons,
            "task_id": bundle["task"]["id"], "source_head": source["head"], "receiver_head": current["head"],
            "receiver_base": base_head, "source_checks": bundle["checks"],
            "ownership_reconciliation_required": bundle["task"]["status"] == "claimed",
            "ownership_transferred": False, "receiver_checks_required": True,
            "note": "Comparison of untrusted context, not approval. Refresh refs explicitly, reconcile the source owner, run local checks and acquire a local claim before editing."}


def render_handoff(bundle: dict) -> str:
    task, workspace = bundle["task"], bundle["workspace"]
    clean = lambda text: " ".join(text.split()).replace("`", "'")
    lines = ["# CoProgrammer handoff", "", f"Task: `{task['id']}` — {clean(task['title'])}",
             f"State: {task['status']} | Source window: {bundle['session']['id']} ({clean(bundle['session']['client'])})",
             f"HEAD: `{workspace['head']}`", f"Base: `{workspace['base']['head']}`",
             f"CoProgrammer: `{workspace['tool_version']}` | Uncommitted paths: {workspace['dirty']['count']}",
             f"Content: `{workspace['content']['sha256']}`", "", "## Scope", ""]
    lines.extend(f"- `{clean(p)}`" for p in task["patterns"])
    lines.extend(["", "## Checks", ""])
    lines.extend(f"- {check['label']}: {'current' if check['fresh'] else 'stale/failed'}" for check in bundle["checks"])
    if not bundle["checks"]:
        lines.append("No check records supplied; verification is still required.")
    if task["summary"]:
        lines.extend(["", "## Reported result (untrusted)", "", clean(task["summary"])])
    lines.extend(["", NOTE, "", "Use the JSON bundle with `coprogrammer workspace compare` in the receiving clone."])
    return "\n".join(lines) + "\n"
