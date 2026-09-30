"""An offline, executable tour of the existing coordination APIs.

The public entry point isolates Git configuration in a child process. The
scenario uses real repositories and Manager events, not mocked client results.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from . import collaboration as co, scheduler as sc
from .manager_store import load_events


def _require(condition: bool, explanation: str) -> None:
    if not condition:
        raise RuntimeError(f"Demo verification failed: {explanation}")


def _denied(path: Path, operation: Callable, expected: str) -> dict:
    before = path.read_bytes()
    try:
        operation()
    except RuntimeError as exc:
        if expected not in str(exc):
            raise
        _require(path.read_bytes() == before, "a rejected operation changed the event log")
        return {"rejection": str(exc), "event_log_unchanged": True}
    raise RuntimeError(f"Demo verification failed: expected rejection containing {expected!r}")


def _run_scenario(root: Path) -> dict:
    """Execute inside an owned temporary directory; used by the isolated child."""
    from .cli import active_leases, event_log_path, run_git

    repo, codex, claude = (root / name for name in ("repository", "codex", "claude"))
    repo.mkdir()
    hooks = root / "empty-hooks"
    hooks.mkdir()

    def git(*args: str, cwd: Path = repo) -> str:
        return run_git(["-c", f"core.hooksPath={hooks}", "-c", "commit.gpgSign=false",
                        "-c", "user.name=CoProgrammer Demo",
                        "-c", "user.email=demo@example.invalid", *args], cwd)

    git("init", "--template=", "-b", "main")
    git("commit", "--allow-empty", "-m", "Offline demo fixture")
    git("worktree", "add", "-b", "demo/codex", str(codex))
    git("worktree", "add", "-b", "demo/claude", str(claude))

    steps: list[dict] = []

    def passed(step_id: str, title: str, detail: str, **evidence) -> None:
        steps.append({"id": step_id, "status": "passed", "title": title,
                      "detail": detail, "evidence": evidence})

    workspaces = [co.workspace(cwd) for cwd in (codex, claude)]
    _require([w["worktree"] for w in workspaces] == [str(codex), str(claude)],
             "sessions must use the two temporary linked worktrees")
    _require([w["branch"] for w in workspaces] == ["demo/codex", "demo/claude"],
             "each worktree must have its own named branch")
    _require(bool(workspaces[0]["head"]) and workspaces[0]["head"] == workspaces[1]["head"],
             "both worktrees must start at the same real commit")
    paths = [event_log_path(cwd) for cwd in (repo, codex, claude)]
    _require(paths[0] == paths[1] == paths[2] == repo / ".coprogrammer" / "events.jsonl",
             "all worktrees must discover one shared temporary Manager log")
    path = paths[0]
    roots = [str(Path(part.removeprefix("worktree ")).resolve()) for part in
             git("worktree", "list", "--porcelain", "-z").split("\0")
             if part.startswith("worktree ")]
    _require(set(roots) == {str(repo), str(codex), str(claude)},
             "Git must list the main checkout and both linked worktrees")
    _require(not git("remote"), "the demo repository must have no remotes")
    passed("worktrees", "Create two Git worktrees",
           "Two branches share one repository and one Manager event log.",
           linked_worktrees=2, git_worktree_count=len(roots), shared_manager_log=True,
           branches=[w["branch"] for w in workspaces], initial_head=workspaces[0]["head"],
           remotes=[])

    co.register(path, codex, "demo-codex", "codex", "offline-demo")
    co.register(path, claude, "demo-claude", "claude", "offline-demo")
    sessions, _ = co.reconstruct(load_events(path))
    _require(set(sessions) == {"demo-codex", "demo-claude"}, "both session records must exist")
    passed("sessions", "Register local session records",
           "Codex and Claude are routing labels in this demo; no client or model is launched.",
           sessions=[{"id": s["id"], "client": s["client"], "branch": s["branch"],
                      "provider": s["provider"], "model": s["model"]} for s in sessions.values()])

    sc.create(path, codex, "demo-codex", "api", "Prepare API handoff", ["src/**"], clients=["codex"])
    sc.create(path, codex, "demo-codex", "docs", "Document the API", ["docs/**"],
              depends_on=["api"], clients=["claude"])
    sc.create(path, codex, "demo-codex", "review", "Review the shared API scope", ["src/api.py"],
              clients=["claude"])

    def task(task_id: str) -> dict:
        return next(t for t in sc.board(load_events(path))["tasks"] if t["id"] == task_id)

    _require(task("docs")["blocked_reasons"] == ["unfinished_dependencies"],
             "documentation must wait for the API task")
    blocked = _denied(path, lambda: sc.claim(path, claude, "demo-claude", "docs"),
                      "unfinished dependencies")
    passed("dependencies", "Block unfinished dependencies",
           "Claude cannot claim documentation until the API task is finished.",
           task_id="docs", depends_on=task("docs")["depends_on"],
           blocked_reasons=task("docs")["blocked_reasons"], **blocked)

    upstream = sc.claim(path, codex, "demo-codex", "api")
    leases = active_leases(load_events(path))
    _require(upstream["status"] == "claimed" and upstream["branch"] == "demo/codex"
             and leases[upstream["lease_id"]]["holder"] == "demo-codex",
             "claim must bind the task, branch and active path lease")
    passed("claim", "Claim work with a lease",
           "The API claim belongs to the Codex session and its Git branch.",
           task_id=upstream["id"], claim_id=upstream["claim_id"], lease_id=upstream["lease_id"],
           branch=upstream["branch"], active_leases=len(leases))

    before = path.read_bytes()
    guarded = sc.guard(path, codex, "demo-codex", "api", upstream["claim_id"], ["src/api.py"])
    _require(guarded["allowed"] is True and path.read_bytes() == before,
             "an allowed guard must be read-only")
    outside = _denied(path, lambda: sc.guard(path, codex, "demo-codex", "api",
                      upstream["claim_id"], ["docs/api.md"]), "outside task scope")
    passed("guard", "Check the planned file scope",
           "The guard allows src/api.py and rejects a documentation path outside the claim.",
           allowed_files=guarded["files"], allowed=guarded["allowed"], **outside)

    conflict = _denied(path, lambda: sc.claim(path, claude, "demo-claude", "review"),
                       "path lease conflict")
    _require(task("review")["blocked_reasons"] == ["path_lease_conflict"],
             "the independent review task must be blocked only by the overlapping lease")
    passed("conflict", "Reject overlapping work",
           "A different worktree cannot claim src/api.py while Codex holds src/**.",
           task_id="review", blocked_reasons=task("review")["blocked_reasons"], **conflict)

    body = "API scope checked. Wait for task api to finish before claiming docs."
    sent = co.send(path, codex, "demo-codex", "demo-claude", "api", body,
                   kind="handoff", key="demo-api-handoff")
    before = path.read_bytes()
    received = co.inbox(path, "demo-claude")
    _require(len(received["messages"]) == received["pending_total"] == 1
             and received["messages"][0]["id"] == sent["message"]["id"]
             and received["messages"][0]["body"] == body and path.read_bytes() == before,
             "reading the handoff must preserve its contents and leave it pending")
    retry = co.send(path, codex, "demo-codex", "demo-claude", "api", body,
                    kind="handoff", key="demo-api-handoff")
    _require(retry["duplicate"] is True and retry["message"]["id"] == sent["message"]["id"]
             and path.read_bytes() == before, "retrying the same handoff must not duplicate it")
    passed("handoff", "Send and read a durable handoff",
           "Reading preserves the pending message; retrying the same request stores no duplicate.",
           message_id=sent["message"]["id"], kind=sent["message"]["kind"],
           pending_after_read=received["pending_total"], duplicate_retry=retry["duplicate"],
           event_log_unchanged_by_read_and_retry=True)

    acknowledgement = co.acknowledge(path, claude, "demo-claude", sent["message"]["id"])
    pending = co.inbox(path, "demo-claude")["pending_total"]
    _require(bool(acknowledgement["acknowledged_at"]) and pending == 0,
             "explicit recipient acknowledgement must clear the pending message")
    passed("acknowledgement", "Acknowledge the handoff",
           "The recipient explicitly acknowledges receipt; this does not approve code.",
           message_id=acknowledgement["message_id"],
           acknowledged_at=acknowledgement["acknowledged_at"], pending_messages=pending)

    sc.finish(path, codex, "demo-codex", "api", upstream["claim_id"],
              "Demo coordination checks complete; no application implementation is claimed.")
    _require(task("api")["status"] == "done" and task("docs")["ready"] is True
             and task("review")["ready"] is True and not active_leases(load_events(path)),
             "finishing the API task must release its lease and unblock waiting work")
    passed("unblock", "Finish the upstream task",
           "Completing the API task releases its lease and makes both waiting tasks ready.",
           upstream_status=task("api")["status"], downstream_ready=task("docs")["ready"],
           review_ready=task("review")["ready"], active_leases=0)

    for task_id, filename in (("docs", "docs/api.md"), ("review", "src/api.py")):
        claimed = sc.claim(path, claude, "demo-claude", task_id)
        checked = sc.guard(path, claude, "demo-claude", task_id, claimed["claim_id"], [filename])
        completed = sc.finish(path, claude, "demo-claude", task_id, claimed["claim_id"],
                              "Demo claim and scope checks complete; no code approval is implied.")
        _require(checked["allowed"] is True and completed["status"] == "done",
                 f"Claude must claim, guard and finish {task_id}")
        passed(f"finish_{task_id}", f"Complete the {task_id} task",
               "Claude claims the now-ready task, checks its scope and records completion.",
               task_id=task_id, branch=claimed["branch"], guarded_files=checked["files"],
               task_status=completed["status"], claim_id=claimed["claim_id"])

    co.pulse(path, codex, "demo-codex", "closed")
    co.pulse(path, claude, "demo-claude", "closed")
    final = co.sync(path, "demo-claude")
    _require(final["task_counts"] == {"queued": 0, "claimed": 0, "done": 3}
             and final["pending_total"] == 0 and final["active_leases"] == []
             and len(final["sessions"]) == 2
             and all(s["status"] == "closed" for s in final["sessions"]),
             "final state must contain three completed tasks and no pending work")
    return {"status": "passed", "steps": steps,
            "summary": {"completed_tasks": final["task_counts"]["done"],
                        "session_records": len(final["sessions"]),
                        "closed_sessions": sum(s["status"] == "closed" for s in final["sessions"]),
                        "active_leases": len(final["active_leases"]),
                        "pending_messages": final["pending_total"],
                        "event_count": len(load_events(path))},
            "limitations": ["Codex and Claude are local routing labels; no client connection or model call is tested.",
                            "Leases and guards are cooperative checks, not filesystem access controls.",
                            "Task completion and message acknowledgement do not approve, merge or validate application code."]}


def run_demo() -> dict:
    """Run the offline tour and return verified, JSON-serializable observations.

    No repository or global Git configuration is changed. A child process keeps
    Git environment/configuration overrides isolated from both the user's Git
    setup and other threads. Every temporary file is removed before return,
    including on failure. Unexpected API/Git errors propagate as RuntimeError.
    """
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
                "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
                "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    worker = ("import json; from pathlib import Path; "
              "from coprogrammer.demo import _run_scenario; "
              "print(json.dumps(_run_scenario(Path.cwd()), ensure_ascii=False))")
    with tempfile.TemporaryDirectory(prefix="coprogrammer-demo-") as temporary:
        root = Path(temporary).resolve()
        try:
            result = subprocess.run([sys.executable, "-c", worker], cwd=root, env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Offline demo could not run: {exc}") from exc
        if result.returncode:
            raise RuntimeError(f"Offline demo failed: {result.stderr.strip() or 'worker exited without a report'}")
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Offline demo returned an invalid report") from exc
        _require(isinstance(report, dict) and report.get("status") == "passed",
                 "the scenario must return a successful report")
    _require(not root.exists(), "the temporary directory must be removed")
    report["cleanup"] = {"temporary_directory_removed": True}
    return report
