"""Optional local retry observations; called only while the runner lock is held."""
from __future__ import annotations

from . import collaboration as co, workspace as ws


def _digest(cwd):
    try:
        return ws.snapshot(cwd)["content"]["sha256"]
    except (OSError, RuntimeError, ValueError):
        raise RuntimeError("Retry protection could not observe stable project content; inspect local files, snapshot limits and the original run before another invocation.") from None


def _previous(tx, session, claim):
    previous = None
    for event in tx.events:
        if event["type"] not in ("retry.started", "retry.finished"):
            raise RuntimeError("Retry protection found an unfamiliar local record; inspect the original run before continuing.")
        value = event.get("payload")
        try:
            if set(value) != {"session", "claim_id", "content_sha256"}:
                raise ValueError
            co.identity(value["session"])
            co.identity(value["claim_id"])
            if not isinstance(value["content_sha256"], str) or not ws.HASH.fullmatch(value["content_sha256"]):
                raise ValueError
        except (KeyError, TypeError, ValueError, RuntimeError):
            raise RuntimeError("Retry protection found an invalid local record; inspect the original run before continuing.") from None
        if value["session"] == session and value["claim_id"] == claim:
            previous = event
    return previous


def _record(tx, kind, session, claim, content):
    from .cli import make_event
    tx.append(make_event(kind, session, "worker-retry", {
        "session": session, "claim_id": claim, "content_sha256": content}))


def begin(tx, cwd, session, task, newly_claimed):
    """Compare before recording; stopped checks never replace the old baseline."""
    # The record itself must not become part of the content it protects.
    root = ws.root(cwd)
    if tx.path.resolve().is_relative_to(root):
        relative = tx.path.resolve().relative_to(root).as_posix()
        if (ws.git(root, "ls-files", "--", relative).strip()
                or not ws.git(root, "check-ignore", "--no-index", "--", relative, optional=True).strip()):
            raise RuntimeError("Retry protection requires its run state to be Git-ignored or outside the worktree; inspect the selected state directory.")
    previous = _previous(tx, session, task["claim_id"])
    if previous is None and not newly_claimed:
        return "retry_baseline_missing", "This claim has no protected end snapshot. Inspect its original run and edits; enabling protection now cannot reconstruct an earlier baseline. No command was launched."
    if previous is not None and previous["type"] != "retry.finished":
        return "retry_attempt_incomplete", "The previous protected attempt has no confirmed end snapshot. Inspect its processes, claim and edits before deciding how to continue. No command was launched."
    content = _digest(cwd)
    if previous is not None and previous["payload"]["content_sha256"] != content:
        return "retry_content_changed", "Project content changed since the previous protected attempt ended. Inspect git status and preserve or reconcile your edits before explicitly deciding to continue. No command was launched; no baseline was replaced."
    _record(tx, "retry.started", session, task["claim_id"], content)
    # Persist before any child can write. An exception/cancellation thereafter
    # leaves this marker, rather than silently accepting uncertain end content.
    tx.commit()
    return None


def finish(tx, cwd, session, task):
    _record(tx, "retry.finished", session, task["claim_id"], _digest(cwd))
