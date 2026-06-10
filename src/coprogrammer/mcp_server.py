"""Zero-dependency MCP (Model Context Protocol) stdio server.

Exposes the CoProgrammer Manager Plane and digest tooling as MCP tools so any
MCP client (Claude Code, Codex, Cursor, Cowork, ...) can coordinate
multi-agent work without shelling out to the CLI.

Transport: newline-delimited JSON-RPC 2.0 over stdio, per the MCP spec.
No third-party dependencies; reuses cli.py internals.

Run:
    python -m coprogrammer mcp serve [--cwd .] [--state-dir .coprogrammer]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import cli

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "coprogrammer", "version": "0.1.0"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "digest_branch",
        "description": (
            "Generate a CoProgrammer branch digest (intent, changed files, "
            "commits, contract/architecture risk signals, protected-path "
            "matches, risk level) for a base..head range or the working tree."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "default": "origin/main"},
                "head": {"type": "string", "default": "HEAD"},
                "working_tree": {"type": "boolean", "default": False},
                "language": {"type": "string", "enum": ["en", "zh-CN"]},
            },
        },
    },
    {
        "name": "manager_status",
        "description": (
            "Show reconstructed Manager Plane state: active leases, open "
            "decisions, contract changes, and latest agent heartbeats."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "manager_forecast",
        "description": (
            "Forecast conflicts before PR time: overlapping agent leases, "
            "breaking/unknown contract proposals, protected-path pressure, "
            "and optionally which changed files collide with other agents."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "changed_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Changed file paths to check.",
                }
            },
        },
    },
    {
        "name": "lease_request",
        "description": (
            "Request an advisory workspace lease for path patterns before "
            "editing. Overlapping leases automatically open a decision."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "holder": {"type": "string"},
                "patterns": {"type": "array", "items": {"type": "string"}},
                "kind": {
                    "type": "string",
                    "enum": list(cli.LEASE_KINDS),
                    "default": "path",
                },
                "task": {"type": "string", "default": ""},
            },
            "required": ["holder", "patterns"],
        },
    },
    {
        "name": "heartbeat",
        "description": "Publish an agent heartbeat (current task and status).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "task": {"type": "string"},
            },
            "required": ["agent", "task"],
        },
    },
    {
        "name": "contract_propose",
        "description": (
            "Propose a shared contract change (api/schema/database/...) so "
            "other agents see it before merge time. Breaking changes open a "
            "human decision automatically."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "proposer": {"type": "string"},
                "kind": {"type": "string", "enum": list(cli.CONTRACT_KINDS)},
                "name": {"type": "string"},
                "summary": {"type": "string"},
                "compatibility": {
                    "type": "string",
                    "enum": list(cli.CONTRACT_COMPATIBILITY),
                    "default": "unknown",
                },
            },
            "required": ["proposer", "kind", "name", "summary"],
        },
    },
]


class ManagerContext:
    def __init__(self, cwd: Path, state_dir: str):
        self.cwd = cwd
        self.state_dir = state_dir

    @property
    def log_path(self) -> Path:
        return cli.event_log_path(self.cwd, self.state_dir)

    def events(self) -> list[dict[str, Any]]:
        return cli.load_events(self.log_path)

    def config(self) -> dict[str, Any]:
        return cli.load_config(self.cwd)


def tool_digest_branch(ctx: ManagerContext, args: dict[str, Any]) -> str:
    base = args.get("base", "origin/main")
    head = args.get("head", "HEAD")
    if args.get("working_tree"):
        files = cli.get_working_tree_changed_files(base, ctx.cwd)
        commits: list[str] = []
        head_label = "working-tree"
    else:
        files = cli.get_changed_files(base, head, ctx.cwd)
        commits = cli.get_commits(base, head, ctx.cwd)
        head_label = head
    config = ctx.config()
    language = cli.resolve_language(args.get("language") or config.get("language"))
    return cli.render_digest(
        base=base,
        head=head_label,
        files=files,
        commits=commits,
        language=language,
        config=config,
    )


def tool_manager_status(ctx: ManagerContext, args: dict[str, Any]) -> str:
    events = ctx.events()
    return json.dumps(
        {
            "event_count": len(events),
            "active_leases": list(cli.active_leases(events).values()),
            "open_decisions": list(cli.open_decisions(events).values()),
            "contract_changes": list(cli.contract_changes(events).values()),
            "latest_heartbeats": cli.latest_heartbeats(events),
        },
        indent=2,
        ensure_ascii=False,
    )


def tool_manager_forecast(ctx: ManagerContext, args: dict[str, Any]) -> str:
    report = cli.forecast_report(
        ctx.events(), ctx.config(), args.get("changed_files")
    )
    return json.dumps(report, indent=2, ensure_ascii=False)


def tool_lease_request(ctx: ManagerContext, args: dict[str, Any]) -> str:
    path = ctx.log_path
    events = ctx.events()
    lease = cli.new_lease(
        args["holder"],
        args.get("kind", "path"),
        list(args["patterns"]),
        args.get("task", ""),
    )
    cli.append_event(
        path,
        cli.make_event("lease.requested", args["holder"], "repo:mcp", {"lease": lease}),
    )
    conflicts = cli.find_lease_conflicts(lease, cli.active_leases(events))
    if conflicts:
        decision = cli.new_decision(
            question=(
                f"Should {args['holder']} proceed with "
                f"{', '.join(args['patterns'])} despite active lease overlap?"
            ),
            context=json.dumps(
                {"requested_lease": lease, "conflicting_leases": conflicts},
                ensure_ascii=False,
                sort_keys=True,
            ),
            related_artifacts=[lease["id"], *[c["id"] for c in conflicts]],
        )
        cli.append_event(
            path,
            cli.make_event(
                "decision.requested", "manager", "repo:mcp", {"decision": decision}
            ),
        )
        return json.dumps(
            {
                "granted": False,
                "lease": lease,
                "conflicts": conflicts,
                "decision_requested": decision["id"],
            },
            indent=2,
            ensure_ascii=False,
        )
    lease["status"] = "active"
    cli.append_event(
        path,
        cli.make_event("lease.granted", "manager", "repo:mcp", {"lease": lease}),
    )
    return json.dumps({"granted": True, "lease": lease}, indent=2, ensure_ascii=False)


def tool_heartbeat(ctx: ManagerContext, args: dict[str, Any]) -> str:
    heartbeat = cli.new_heartbeat(args["agent"], args["task"])
    cli.append_event(
        ctx.log_path,
        cli.make_event(
            "agent.heartbeat", args["agent"], "repo:mcp", {"heartbeat": heartbeat}
        ),
    )
    return json.dumps(heartbeat, indent=2, ensure_ascii=False)


def tool_contract_propose(ctx: ManagerContext, args: dict[str, Any]) -> str:
    path = ctx.log_path
    change = cli.new_contract_change(
        proposer=args["proposer"],
        kind=args["kind"],
        name=args["name"],
        summary=args["summary"],
        compatibility=args.get("compatibility", "unknown"),
    )
    cli.append_event(
        path,
        cli.make_event(
            "contract.change.proposed",
            args["proposer"],
            "repo:mcp",
            {"contract_change": change},
        ),
    )
    result: dict[str, Any] = {"contract_change": change}
    if change["compatibility"] == "breaking":
        decision = cli.new_decision(
            question=f"Should breaking contract change proceed: {args['name']}?",
            context=json.dumps(change, ensure_ascii=False, sort_keys=True),
            related_artifacts=[change["id"]],
            risk="high",
        )
        cli.append_event(
            path,
            cli.make_event(
                "decision.requested", "manager", "repo:mcp", {"decision": decision}
            ),
        )
        result["decision_requested"] = decision["id"]
    return json.dumps(result, indent=2, ensure_ascii=False)


TOOL_HANDLERS = {
    "digest_branch": tool_digest_branch,
    "manager_status": tool_manager_status,
    "manager_forecast": tool_manager_forecast,
    "lease_request": tool_lease_request,
    "heartbeat": tool_heartbeat,
    "contract_propose": tool_contract_propose,
}


def handle_request(ctx: ManagerContext, request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        try:
            text = handler(ctx, params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as exc:  # noqa: BLE001 - report tool failure to client
            result = {
                "content": [{"type": "text", "text": f"error: {exc}"}],
                "isError": True,
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    if request_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
    return None


def serve(cwd: Path, state_dir: str, stdin=None, stdout=None) -> int:
    """Serve newline-delimited JSON-RPC over stdio until EOF."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    ctx = ManagerContext(cwd, state_dir)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "parse error"},
            }
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
            continue
        response = handle_request(ctx, request)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
