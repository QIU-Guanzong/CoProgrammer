"""Disposable CLI example: unknown returns, durable state, no mutation replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from coprogrammer import cli, collaboration, manager_store


# This hook exists only in the fixture subprocess, after a real atomic commit.
# It never patches the installed package or changes Manager transaction rules.
INTERRUPT_AFTER_COMMIT = """
import sys
from coprogrammer import cli, manager_store
event_type = sys.argv[1]
original = manager_store.EventTransaction.commit
interrupted = False
def commit(tx):
    global interrupted
    original(tx)
    if not interrupted and any(e['type'] == event_type for e in tx.pending):
        interrupted = True
        raise KeyboardInterrupt
manager_store.EventTransaction.commit = commit
raise SystemExit(cli.main(sys.argv[2:]))
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def scenario(root: Path) -> dict:
    project, peer = root / "project", root / "peer"
    project.mkdir()
    hooks = root / "empty-hooks"
    hooks.mkdir()
    # Ignore global/system Git configuration only inside these subprocesses.
    # No account, config file, hook or service in the caller's project is touched.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
               PYTHONPATH=str(Path(collaboration.__file__).resolve().parents[1]),
               PYTHONDONTWRITEBYTECODE="1")

    def run(argv: list[str], cwd: Path, expected: int = 0):
        completed = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        require(completed.returncode == expected, "Synthetic CLI returned an unexpected exit status")
        return completed.stdout

    def git(*args):
        return run(["git", "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgSign=false",
                    "-c", "user.name=Offline Fixture", "-c",
                    "user.email=fixture@example.invalid", *args], project)

    def query(cwd: Path, *args):
        return json.loads(run([sys.executable, "-m", "coprogrammer", *args, "--cwd", str(cwd)], cwd))

    git("init", "--template=", "-b", "demo/main")
    (project / ".gitignore").write_text(".coprogrammer/\n", encoding="utf-8")
    git("add", ".gitignore")
    git("commit", "-m", "Disposable inspection fixture")
    git("worktree", "add", "-b", "demo/peer", str(peer))
    require(not git("remote").strip(), "Fixture must have no remote")
    for cwd, session in ((project, "fixture-worker"), (peer, "fixture-peer")):
        query(cwd, "manager", "session", "register", "--session", session,
              "--client", "harness", "--task", "fixture-api")
    query(project, "manager", "task", "create", "--session", "fixture-worker",
          "--id", "fixture-api", "--title", "Offline documentation", "--pattern", "docs/**")
    path = cli.event_log_path(project)
    require(cli.event_log_path(peer) == path, "Linked worktrees must share the fixture Manager")

    def interrupted(cwd: Path, session: str, event_type: str, command: list[str], *options):
        argv = [sys.executable, "-c", INTERRUPT_AFTER_COMMIT, event_type, "worker", "run",
                "--cwd", str(cwd), "--session", session, "--apply", *options, "--", *command]
        report = json.loads(run(argv, cwd, expected=130))
        require(report["reason"] == "interrupted", "Expected an interruption receipt")
        require(report["exit_code"] == 0, "Expected the original fixture's successful exit")
        return report

    def inspect(cwd: Path, session: str):
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        reports = {
            "status": query(cwd, "status", "--session", session, "--json", "--limit", "200"),
            "board": query(cwd, "manager", "task", "board"),
            "leases": query(cwd, "manager", "leases", "--json"),
            "inbox": query(cwd, "manager", "message", "inbox", "--session", session,
                           "--task", "fixture-api", "--include-acked", "--limit", "200"),
            "thread": query(cwd, "manager", "message", "thread", "--session", session,
                            "--task", "fixture-api", "--limit", "200"),
            "preview": query(cwd, "worker", "step", "--session", session, "--limit", "200"),
        }
        require(hashlib.sha256(path.read_bytes()).hexdigest() == before,
                "Read-only inspection must preserve the exact event log")
        require(not reports["inbox"]["has_more"] and not reports["thread"]["has_more"],
                "Fixture messages must fit on one page")
        return reports

    finish_code = ("import pathlib,json;pathlib.Path('docs').mkdir(exist_ok=True);"
                   "pathlib.Path('docs/example.txt').write_text('Synthetic edit\\n');"
                   "p=pathlib.Path('.coprogrammer/finish-called');"
                   "p.write_text(str(int(p.read_text())+1) if p.exists() else '1');"
                   "print(json.dumps({'status':'done','summary':'Synthetic handoff'}))")
    finish = interrupted(project, "fixture-worker", "task.finished", [sys.executable, "-c", finish_code],
                         "--notify", "fixture-peer")
    require(finish["completion_status"] == "unknown", "Finish return must remain unknown")
    require(finish["claim_retained"] is None, "Do not invent retention after interrupted finish")
    completed = inspect(project, "fixture-worker")
    task = next(t for t in completed["board"]["tasks"] if t["id"] == "fixture-api")
    require(task["status"] == "done" and task["session"] == "fixture-worker"
            and task["worktree"] == str(project) and task["branch"] == "demo/main",
            "Inspect the exact original task and owner")
    require(completed["leases"] == [], "The completed fixture's single lease must be released")

    pending = inspect(peer, "fixture-peer")["inbox"]
    require(len(pending["messages"]) == 1 and pending["messages"][0]["acknowledged_at"] is None,
            "Completion notification must remain pending after reads")
    receipt_code = ("import json,sys,pathlib;x=json.load(sys.stdin);"
                    "pathlib.Path('.coprogrammer/receipt-called').parent.mkdir(exist_ok=True);"
                    "p=pathlib.Path('.coprogrammer/receipt-called');"
                    "p.write_text(str(int(p.read_text())+1) if p.exists() else '1');"
                    "print(json.dumps({'status':'received','summary':'Synthetic explicit receipt',"
                    "'acknowledge':[m['id'] for m in x['messages']]}))")
    receipt = interrupted(peer, "fixture-peer", "message.acknowledged", [sys.executable, "-c", receipt_code],
                          "--handle-inbox")
    require(receipt["receipt_status"] == "unknown", "ACK return must remain unknown")
    acknowledged = inspect(peer, "fixture-peer")["inbox"]
    require(len(acknowledged["messages"]) == 1 and acknowledged["messages"][0]["acknowledged_at"] is not None,
            "Inspect the exact message's durable receipt")
    events = manager_store.load_events(path)
    counts = {kind: sum(e["type"] == kind for e in events)
              for kind in ("task.claimed", "task.finished", "lease.released", "message.sent", "message.acknowledged")}
    require(all(count == 1 for count in counts.values()), "Fixture mutations must occur once, without replay")
    require((project / ".coprogrammer/finish-called").read_text() == "1"
            and (peer / ".coprogrammer/receipt-called").read_text() == "1", "Each harness must run once")
    return {"format": "coprogrammer.offline-inspection-example.v1", "model_calls": 0,
            "finish": {"exit_status": 130, "report_status": finish["completion_status"],
                       "inspected_task": {key: task[key] for key in ("id", "status", "session", "branch")}},
            "receipt": {"exit_status": 130, "report_status": receipt["receipt_status"],
                        "inspected_acknowledged_messages": 1},
            "active_leases_after_exact_task_done": 0,
            "harness_invocations": {"finish": 1, "receipt": 1},
            "inspection_preserved_event_log": True, "mutation_counts": counts,
            "decision": "Do not rerun either harness, finish or ACK to compensate for unknown returns."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a structured, token-free fixture summary.")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("This source-checkout fixture is validated on Linux; Windows native acceptance is not claimed.")
    with tempfile.TemporaryDirectory(prefix="coprogrammer-inspection-") as directory:
        result = scenario(Path(directory).resolve())
    result["temporary_project_removed"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          "Offline finish/ACK interruption inspected: durable outcomes confirmed, no mutations replayed; temporary project removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
