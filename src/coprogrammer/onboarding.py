"""Small entry points over existing local sessions and task coordination."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

from . import briefing, collaboration as co, setup, workflow
from .manager_store import transaction


def _workspace(cwd: Path, *, writable: bool = False) -> dict:
    from .cli import run_git
    try:
        run_git(["rev-parse", "--show-toplevel"], cwd)
    except RuntimeError as exc:
        raise RuntimeError("Run this inside a Git checkout; use 'coprogrammer demo' to try it first.") from exc
    actual = co.workspace(cwd)
    if writable and (not actual["head"] or actual["branch"] == "HEAD"):
        raise RuntimeError("Start requires a committed checkout on a named branch.")
    return actual


def overview(path: Path, cwd: Path, session: str = "", limit: int = 20) -> dict:
    """One Manager snapshot; no pulse, claim, ACK, client launch or file install."""
    if session:
        co.identity(session)
    actual = _workspace(cwd)
    # A first read of an empty project need not create a runtime directory.
    with transaction(path) if path.exists() else nullcontext(None) as tx:
        events = [*tx.events, *tx.pending] if tx else []
        report = briefing.build_briefing(events, session, limit)
        dispatch = workflow.dispatch(path, cwd, session, limit) if session else None
    reasons = dispatch["session_reasons"] if dispatch else []
    attention = report["attention_required"] or any(
        r != "session_or_worktree_occupied" for r in reasons)
    if "session_or_worktree_occupied" in reasons and not report["claimed_tasks"]:
        attention = True
    return {"format": "coprogrammer.status.v1", "workspace": actual,
            "briefing": report, "dispatch": dispatch, "attention_required": attention}


def start(path: Path, cwd: Path, client: str, session: str, task: str | None = None,
          *, resume: bool = False, dry_run: bool = False) -> dict:
    """Register a window; explicitly resume only its matching local session."""
    if client not in setup.CLIENT_LAYOUTS:
        raise RuntimeError("client must be codex, claude, or copilot")
    co.identity(session)
    if task is not None:
        co.text(task, "task")
    actual = _workspace(cwd, writable=True)
    preview = setup.preview(Path(actual["worktree"]), client)
    # Actual writes always serialize, including the initial empty-log case.
    with transaction(path) if not dry_run or path.exists() else nullcontext(None) as tx:
        events = [*tx.events, *tx.pending] if tx else []
        sessions, _, board = co._snapshot(events)
        old = sessions.get(session)
        if resume:
            old = co._session(sessions, session, cwd)
            if old["client"].casefold() != client:
                raise RuntimeError("This session uses a different client; choose a new window ID.")
            if old["status"] not in ("working", "idle"):
                raise RuntimeError("Resolve the blocked session with 'manager session pulse' before resuming.")
            owned = [t for t in board["tasks"] if t["status"] == "claimed" and t["session"] == session]
            if any(t["branch"] != actual["branch"] or t["worktree"] != actual["worktree"] for t in owned):
                raise RuntimeError("Return to the claimed task's original worktree and branch before resuming.")
            selected_task = old["task"] if task is None else task
            if owned and selected_task != old["task"]:
                raise RuntimeError("Finish or release the current claim before changing the session task.")
        else:
            if old:
                raise RuntimeError("Session ID already exists; use --resume for this window or choose a new ID.")
            selected_task = session if task is None else task
        if co.workspace(cwd) != actual:
            raise RuntimeError("Workspace changed while preparing this window; retry.")
        if not dry_run:
            if resume:
                co.pulse(path, cwd, session, task=selected_task)
            else:
                co.register(path, cwd, session, client, selected_task)
    return {"format": "coprogrammer.start.v1", "session": session, "client": client,
            "task": selected_task, "workspace": actual, "applied": not dry_run,
            "operation": "resume" if resume else "register",
            "setup": {"missing": sum(f["status"] == "create" for f in preview["files"]),
                      "conflicts": preview["conflicts"], "connection": "not_checked",
                      "applied": False},
            "note": "Only local session state is updated. Client files are previewed, never installed; no agent is launched."}


def _line(value: str) -> str:
    return " ".join(value.split())


def render_start(report: dict) -> str:
    verb = "resumed" if report["operation"] == "resume" else "registered"
    lines = ["CoProgrammer — Teamwork for coding agents", "",
             f"Window: {report['session']} ({report['client']})",
             f"Branch: {_line(report['workspace']['branch'])}",
             f"Session: {verb}" if report["applied"] else f"Preview: would {report['operation']} this window",
             f"Client setup: {report['setup']['missing']} missing files, {len(report['setup']['conflicts'])} conflicts",
             "", "Next:", f"  coprogrammer status --session {report['session']}",
             f"  coprogrammer setup --client {report['client']} --include-content",
             "", "Review setup before applying it. Keep .coprogrammer/ out of commits.",
             report["note"]]
    return "\n".join(lines) + "\n"


def render_status(report: dict) -> str:
    brief = report["briefing"]
    counts = brief["counts"]
    dispatch = report["dispatch"]
    scope = "eligible for this window" if dispatch else "ready in repository"
    ready = dispatch["counts"]["eligible"] if dispatch else counts["ready"]
    lines = ["CoProgrammer — Teamwork for coding agents", "",
             f"Branch: {_line(report['workspace']['branch']) or '(no committed branch)'}",
             f"Tasks: {ready} {scope}, {counts['claimed']} claimed, {counts['blocked']} blocked, {counts['done']} done",
             f"Windows: {counts['sessions']} | Pending messages: {counts['pending_messages']}"]
    for row in brief["sessions"]:
        lines.append(f"- {row['id']} ({_line(row['client'])}): {row['status']} / {row['freshness']}")
    candidates = dispatch["candidates"] if dispatch else brief["ready_tasks"]
    if candidates:
        lines.extend(["", "Available work:"])
        lines.extend(f"- {t['id']}: {_line(t['title'])}" for t in candidates)
    if dispatch and dispatch["session_reasons"]:
        lines.extend(["", "Window checks: " + ", ".join(dispatch["session_reasons"])])
    for label, key in (("Owned work", "claimed_tasks"), ("Blocked work", "blocked_tasks")):
        if brief[key]:
            lines.extend(["", label + ":"])
            lines.extend(f"- {t['id']}: {_line(t['title'])}" +
                         (" (" + ", ".join(t['blocked_reasons']) + ")" if t['blocked_reasons'] else "")
                         for t in brief[key])
    lines.extend(["", "Next:"])
    actions = [a for a in brief["next_actions"] if a["code"] != "inspect_ready_tasks"]
    lines.extend(f"- {_line(a['target'])}: {a['message']}" for a in actions)
    if dispatch and dispatch["recommended_task"]:
        lines.append(f"  coprogrammer manager task claim --session {dispatch['session']} --id {dispatch['recommended_task']}")
    elif not brief["sessions"]:
        lines.append("  coprogrammer start --client codex --session my-window")
    elif not actions:
        lines.append("  coprogrammer manager task board")
    omitted = sum(brief["omitted"].values()) + (sum(dispatch["omitted"].values()) if dispatch else 0)
    if omitted:
        lines.append("More rows omitted; raise --limit or use --json to inspect counts.")
    lines.extend(["", "Local coordination only. Status does not refresh a window, claim work or acknowledge messages."])
    return "\n".join(lines) + "\n"


def command(args):
    import json
    from .cli import event_log_path
    from .workflow_cli import emit
    cwd = Path(args.cwd).resolve()
    path = event_log_path(cwd, args.state_dir)
    if args.onboarding_action == "start":
        report = start(path, cwd, args.client, args.session, args.task,
                       resume=args.resume, dry_run=args.dry_run)
        rendered = render_start(report)
    else:
        report = overview(path, cwd, args.session, args.limit)
        rendered = render_status(report)
    emit(json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else rendered)
    return int(args.onboarding_action == "status" and args.fail_on_attention and report["attention_required"])


def add_parsers(parsers):
    for action, help_text in (("start", "Register this coding window and show client setup next steps."),
                              ("status", "Show windows, work, blockers and next steps.")):
        parser = parsers.add_parser(action, help=help_text)
        parser.add_argument("--cwd", default=".")
        parser.add_argument("--state-dir", default=None)
        parser.add_argument("--json", action="store_true")
        if action == "start":
            parser.add_argument("--client", choices=setup.CLIENT_LAYOUTS, required=True)
            parser.add_argument("--session", required=True)
            parser.add_argument("--task")
            parser.add_argument("--resume", action="store_true", help="Explicitly refresh this window's existing session.")
            parser.add_argument("--dry-run", action="store_true", help="Preview without registering or refreshing the window.")
        else:
            parser.add_argument("--session", default="")
            parser.add_argument("--limit", type=int, default=20)
            parser.add_argument("--fail-on-attention", action="store_true")
        parser.set_defaults(func=command, onboarding_action=action)
