"""Explicit bounded foreground task processing over existing worker boundaries."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Callable

from . import channels, collaboration as co, runner
from .manager_store import load_events, transaction


def watch(path: Path, cwd: Path, session: str, command: list[str], *,
          apply: bool = False, timeout: int = 120, notify: list[str] | None = None,
          handle_inbox: bool = False, wait: bool = False, max_cycles: int = 20,
          duration: int = 300, poll_seconds: int = 5,
          progress: Callable[[dict], None] | None = None) -> dict:
    """Process ready work; optionally wait for peer tasks/messages in this process.

    No daemon, command retry, implicit ACK, lease takeover or Git checkpoint.
    A watch lock excludes duplicate watchers; run retains its execution lock so
    every child invocation is serialized while Manager communication stays free.
    """
    from .setup import _target

    co.bounded(max_cycles, "max_cycles", 100)
    co.bounded(duration, "duration_seconds", 600)
    co.bounded(poll_seconds, "poll_seconds", 25)
    if type(wait) is not bool or type(apply) is not bool:
        raise RuntimeError("apply and wait must be boolean")
    preview = runner.run(path, cwd, session, command, timeout=timeout,
                         notify=notify, handle_inbox=handle_inbox)
    report = {"format": "coprogrammer.watch.v1", "session": session, "applied": apply,
              "command_sha256": preview["command_sha256"], "state": "prepared",
              "cycles": 0, "completed_tasks": 0, "acknowledged_messages": 0,
              "limits": {"max_cycles": max_cycles, "duration_seconds": duration,
                         "poll_seconds": poll_seconds}, "last": preview,
              "note": "Foreground coordination only; supplied command is trusted. Completion is self-reported; no automatic retries, approval, commits or lease takeover."}
    if not apply:
        return report
    workspace = co.workspace(cwd)
    name = hashlib.sha256(workspace["worktree"].encode()).hexdigest()
    lock_path = _target(path.parent, f"watches/{name}.jsonl")
    _target(path.parent, f"watches/{name}.jsonl.lock")
    deadline = time.monotonic() + duration
    previous = None
    with transaction(lock_path, timeout=0.25):
        try:
            if progress is not None:
                progress({"format": "coprogrammer.watch-progress.v1", "cycle": 0,
                          "session": session, "state": "starting", "task_id": None,
                          "completed_tasks": 0, "acknowledged_messages": 0})
            for cycle in range(1, max_cycles + 1):
                remaining = int(deadline - time.monotonic())
                if remaining < 1:
                    report.update(state="stopped", reason="duration_limit")
                    break
                try:
                    report["cycles"] = cycle
                    result = runner.run(path, cwd, session, command, apply=True,
                                        timeout=min(timeout, remaining), notify=notify,
                                        handle_inbox=handle_inbox)
                except RuntimeError:
                    report.update(state="attention", reason="worker_boundary_failed",
                                  next_step="Inspect worker step and the original claim/edits before another invocation.")
                    break
                report.update(cycles=cycle, last=result)
                state = result.get("state", result["boundary"]["state"])
                if state == "done":
                    report["completed_tasks"] += 1
                if state == "received":
                    report["acknowledged_messages"] += result["acknowledged"]
                task = result["boundary"].get("task")
                event = {"format": "coprogrammer.watch-progress.v1", "cycle": cycle,
                         "session": session, "state": state,
                         "task_id": task["id"] if task else None,
                         "completed_tasks": report["completed_tasks"],
                         "acknowledged_messages": report["acknowledged_messages"]}
                signature = (state, event["task_id"], event["completed_tasks"], event["acknowledged_messages"])
                if progress is not None and signature != previous:
                    progress(event)
                previous = signature
                if state in ("done", "received"):
                    continue
                if state == "attention" or state in ("inbox", "decision"):
                    report.update(state="attention", reason=result.get("reason", state))
                    break
                if state not in ("idle", "blocked") or result["boundary"]["dispatch"]["session_reasons"]:
                    report.update(state="attention", reason="session_or_worktree_blocked")
                    break
                if not wait:
                    report.update(state="stopped", reason="no_ready_work")
                    break
                if cycle == max_cycles:
                    report.update(state="stopped", reason="cycle_limit")
                    break
                events = load_events(path)
                cursor = events[-1]["id"]
                remaining = max(0.0, deadline - time.monotonic())
                if remaining:
                    channels.wait(path, session, cursor, min(poll_seconds, remaining))
            else:
                report.update(state="stopped", reason="cycle_limit")
        except KeyboardInterrupt:
            report.update(state="stopped", reason="interrupted",
                          next_step="Inspect the original claim and edits before resuming.")
    return report
