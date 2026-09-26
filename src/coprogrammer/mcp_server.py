"""Zero-dependency MCP (Model Context Protocol) stdio server.

Exposes the CoProgrammer Manager Plane and digest tooling as MCP tools so any
MCP client (Claude Code, Codex, Cursor, Cowork, ...) can coordinate
multi-agent work without shelling out to the CLI.

Transport: bounded newline-delimited JSON-RPC 2.0 over stdio. This implements
the synchronous tools subset of MCP 2024-11-05, 2025-03-26, 2025-06-18 and
2025-11-25, with version negotiation and version-appropriate tool results.
It does not advertise HTTP, resources, prompts, tasks, or a 2026 protocol.
For compatibility with the original local client, empty initialization params
and calls before initialization remain accepted. Notifications never run tools.
No third-party dependencies; reuses the CLI's Manager operations.

Run:
    python -m coprogrammer mcp serve [--cwd .] [--state-dir .coprogrammer]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from . import cli
from . import __version__

SUPPORTED_PROTOCOL_VERSIONS = (
    "2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25",
)
PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[-1]
SERVER_INFO = {"name": "coprogrammer", "version": __version__}
MAX_REQUEST_BYTES = 1024 * 1024


def string_schema(max_length: int = 256, *, allow_empty: bool = False) -> dict[str, Any]:
    return {
        "type": "string",
        "minLength": 0 if allow_empty else 1,
        "maxLength": max_length,
        "pattern": r"^[^\x00]*$" if allow_empty else r"^(?=[\s\S]*\S)[^\x00]*$",
    }


TTL_SCHEMA = {"type": "integer", "minimum": 1, "maximum": 604800, "default": 3600}
REF_SCHEMA = {
    **string_schema(512),
    "pattern": r"^(?!-)[^\x00\r\n]+$",
}
REVIEW_LABEL_SCHEMA = {
    "type": "string", "minLength": 1, "maxLength": 64,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "review_summary",
        "description": (
            "Compare named local review artifacts against one base/head pair. "
            "Report missing, stale, partial and conflicting evidence in a draft; "
            "no provider calls, file writes, identity certification or merge approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {**REF_SCHEMA, "default": "origin/main"},
                "head": {**REF_SCHEMA, "default": "HEAD"},
                "reviews": {
                    "type": "array", "maxItems": 16,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "label": REVIEW_LABEL_SCHEMA,
                            "path": {**string_schema(4096), "description": "Local JSON artifact; relative to the server project directory."},
                        },
                        "required": ["label", "path"],
                    },
                },
                "expected": {"type": "array", "items": REVIEW_LABEL_SCHEMA, "maxItems": 16},
            },
        },
    },
    {
        "name": "digest_branch",
        "description": (
            "Generate a branch digest draft with changed files, commits, "
            "path-based risk signals and protected-path matches. Intent and "
            "integration decisions remain review prompts for a human or agent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {**REF_SCHEMA, "default": "origin/main"},
                "head": {**REF_SCHEMA, "default": "HEAD"},
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
                    "items": string_schema(4096),
                    "maxItems": 1000,
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
                "holder": string_schema(),
                "patterns": {
                    "type": "array", "items": string_schema(4096),
                    "minItems": 1, "maxItems": 128,
                },
                "kind": {
                    "type": "string",
                    "enum": list(cli.LEASE_KINDS),
                    "default": "path",
                },
                "task": {**string_schema(8000, allow_empty=True), "default": ""},
                "ttl_seconds": TTL_SCHEMA,
            },
            "required": ["holder", "patterns"],
        },
    },
    {
        "name": "lease_release",
        "description": "Release an advisory workspace lease held by the named actor.",
        "inputSchema": {
            "type": "object",
            "properties": {"lease_id": string_schema(), "actor": string_schema()},
            "required": ["lease_id", "actor"],
        },
    },
    {
        "name": "lease_renew",
        "description": "Renew an active advisory lease held by the named actor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lease_id": string_schema(), "actor": string_schema(),
                "ttl_seconds": TTL_SCHEMA,
            },
            "required": ["lease_id", "actor"],
        },
    },
    {
        "name": "heartbeat",
        "description": "Publish an agent heartbeat (current task and status).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": string_schema(),
                "task": string_schema(8000),
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
                "proposer": string_schema(),
                "kind": {"type": "string", "enum": list(cli.CONTRACT_KINDS)},
                "name": string_schema(1024),
                "summary": string_schema(16000),
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

READ_ONLY_TOOLS = {"digest_branch", "manager_status", "manager_forecast", "review_summary"}
for _tool in TOOLS:
    _tool["inputSchema"]["additionalProperties"] = False
    _tool["annotations"] = {
        "readOnlyHint": _tool["name"] in READ_ONLY_TOOLS,
        "destructiveHint": _tool["name"] == "lease_release",
        "idempotentHint": _tool["name"] in READ_ONLY_TOOLS,
        "openWorldHint": False,
    }
TOOL_SCHEMAS = {tool["name"]: tool["inputSchema"] for tool in TOOLS}


class ManagerContext:
    def __init__(self, cwd: Path, state_dir: str | None = None):
        self.cwd = cwd
        self.state_dir = state_dir
        self.protocol_version = PROTOCOL_VERSION

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


def tool_review_summary(ctx: ManagerContext, args: dict[str, Any]) -> str:
    from .review_summary import build_summary

    cwd = ctx.cwd.resolve()
    reviews = {}
    for item in args.get("reviews", []):
        if item["label"] in reviews:
            raise RuntimeError("Duplicate reviewer label")
        reviews[item["label"]] = cwd / item["path"]
    report = build_summary(cwd, args.get("base", "origin/main"),
                           args.get("head", "HEAD"), reviews, args.get("expected", []))
    return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)


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
    result = cli.request_lease(
        path=ctx.log_path,
        holder=args["holder"],
        kind=args.get("kind", "path"),
        patterns=args["patterns"],
        task=args.get("task", ""),
        subject="repo:mcp",
        ttl_seconds=args.get("ttl_seconds", 3600),
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


def tool_lease_release(ctx: ManagerContext, args: dict[str, Any]) -> str:
    result = cli.release_lease(
        path=ctx.log_path, lease_id=args["lease_id"], actor=args["actor"],
        subject="repo:mcp",
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


def tool_lease_renew(ctx: ManagerContext, args: dict[str, Any]) -> str:
    result = cli.renew_lease(
        path=ctx.log_path, lease_id=args["lease_id"], actor=args["actor"],
        ttl_seconds=args.get("ttl_seconds", 3600), subject="repo:mcp",
    )
    return json.dumps(result, indent=2, ensure_ascii=False)


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
    "review_summary": tool_review_summary,
    "digest_branch": tool_digest_branch,
    "manager_status": tool_manager_status,
    "manager_forecast": tool_manager_forecast,
    "lease_request": tool_lease_request,
    "lease_release": tool_lease_release,
    "lease_renew": tool_lease_renew,
    "heartbeat": tool_heartbeat,
    "contract_propose": tool_contract_propose,
}


def validate_value(value: Any, schema: dict[str, Any], field: str = "arguments") -> None:
    """Validate the JSON Schema keywords used by this server's own tool schemas.

    This is deliberately not a general-purpose JSON Schema implementation.
    Keep schemas and this validator in sync when adding a new keyword.
    """
    expected = schema.get("type")
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "boolean": type(value) is bool,
    }
    if expected and not matches.get(expected, False):
        raise ValueError(f"{field} must be {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{field} must be one of {', '.join(map(str, schema['enum']))}")
    if expected == "object":
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                raise ValueError(f"{field}.{name} is required")
        for name, item in value.items():
            if name in properties:
                validate_value(item, properties[name], f"{field}.{name}")
            elif schema.get("additionalProperties") is False:
                raise ValueError(f"{field} has unknown field: {str(name)[:80]}")
    elif expected == "array":
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{field} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{field} has too many items")
        for index, item in enumerate(value):
            validate_value(item, schema.get("items", {}), f"{field}[{index}]")
    elif expected == "string":
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"{field} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{field} is too long")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{field} must contain valid Unicode") from exc
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(f"{field} has an invalid format")
    elif expected == "integer":
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{field} must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{field} must be at most {schema['maximum']}")


def rpc_error(request_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0", "id": request_id,
        "error": {"code": code, "message": message},
    }


PARAM_SCHEMAS = {
    "initialize": {
        "type": "object",
        "properties": {
            "protocolVersion": string_schema(32),
            "capabilities": {"type": "object"},
            "clientInfo": {
                "type": "object", "required": ["name", "version"],
                "properties": {"name": string_schema(), "version": string_schema()},
            },
            "_meta": {"type": "object"},
        },
        "additionalProperties": False,
    },
    "ping": {
        "type": "object", "properties": {"_meta": {"type": "object"}},
        "additionalProperties": False,
    },
    "tools/list": {
        "type": "object",
        "properties": {"cursor": string_schema(), "_meta": {"type": "object"}},
        "additionalProperties": False,
    },
    "tools/call": {
        "type": "object", "required": ["name"],
        "properties": {
            "name": string_schema(128), "arguments": {"type": "object"},
            "_meta": {"type": "object"},
        },
        "additionalProperties": False,
    },
}


def handle_request(ctx: ManagerContext, request: Any) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return rpc_error(None, -32600, "invalid request: expected a JSON object")
    method = request.get("method")
    request_id = request.get("id")
    valid_id = type(request_id) is int or (
        isinstance(request_id, str) and len(request_id) <= 256
    )
    # MCP does not use null IDs, unlike general JSON-RPC. Never reflect an
    # invalid ID into a response or dispatch its potentially mutating method.
    if "id" in request and not valid_id:
        return rpc_error(None, -32600, "invalid request id: expected a string or integer")
    if isinstance(request_id, str):
        try:
            request_id.encode("utf-8")
        except UnicodeEncodeError:
            return rpc_error(None, -32600, "invalid request id: expected valid Unicode")
    if (request.get("jsonrpc") != "2.0" or not isinstance(method, str)
            or not method or len(method) > 128 or "result" in request or "error" in request):
        return rpc_error(request_id if valid_id else None, -32600, "invalid request envelope")
    if "id" not in request:
        # Notifications cannot receive results. In particular, do not turn a
        # tools/call notification into an unauditable, fire-and-forget mutation.
        return None
    params = request.get("params", {})
    if not isinstance(params, dict):
        return rpc_error(request_id, -32602, "params must be an object")
    schema = PARAM_SCHEMAS.get(method)
    if schema is None:
        return rpc_error(request_id, -32601, f"method not found: {method}")
    try:
        validate_value(params, schema, "params")
    except ValueError as exc:
        return rpc_error(request_id, -32602, str(exc))

    if method == "initialize":
        requested_version = params.get("protocolVersion", PROTOCOL_VERSION)
        ctx.protocol_version = (
            requested_version if requested_version in SUPPORTED_PROTOCOL_VERSIONS
            else PROTOCOL_VERSION
        )
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {
                "protocolVersion": ctx.protocol_version,
                "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO,
                "instructions": (
                    "Before editing, read manager_status, request a path lease and check granted. "
                    "Renew leases during work and release them when done. Publish heartbeats and "
                    "propose shared contract changes early. Leases coordinate cooperating clients; "
                    "they are not access controls. Digest findings and model advice do not approve "
                    "integration. Use review_summary to compare named artifacts on the chosen commits; "
                    "missing and conflicting evidence stays visible. Protected contracts, architecture "
                    "and final integration need human review."
                ),
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        if "cursor" in params:
            return rpc_error(request_id, -32602, "unknown cursor: tools fit in one page")
        tools = TOOLS
        if ctx.protocol_version == "2024-11-05":
            tools = [{key: value for key, value in tool.items() if key != "annotations"}
                     for tool in TOOLS]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    name = params["name"]
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return rpc_error(request_id, -32602, f"unknown tool: {name}")
    arguments = params.get("arguments", {})
    try:
        validate_value(arguments, TOOL_SCHEMAS[name])
        text = handler(ctx, arguments)
        result = {"content": [{"type": "text", "text": text}], "isError": False}
        if name != "digest_branch" and ctx.protocol_version in (
            "2025-06-18", "2025-11-25",
        ):
            structured = json.loads(text)
            if isinstance(structured, dict):
                result["structuredContent"] = structured
    except Exception as exc:  # noqa: BLE001 - report tool failure, keep serving
        result = {
            "content": [{"type": "text", "text": f"error: {exc}"}],
            "isError": True,
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def reject_non_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON constant: {value}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def serve(cwd: Path, state_dir: str | None = None, stdin=None, stdout=None) -> int:
    """Serve bounded UTF-8 JSON-RPC lines, discarding an oversized line in full.

    Text readline is character-bounded first, then checked against the byte
    limit, so a single request never needs an unbounded allocation. The rest
    of an oversized physical line is drained without parsing any of its parts.
    """
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    ctx = ManagerContext(cwd, state_dir)
    while True:
        line = stdin.readline(MAX_REQUEST_BYTES + 1)
        if not line:
            break
        try:
            oversized = len(line.encode("utf-8")) > MAX_REQUEST_BYTES
        except UnicodeEncodeError:
            oversized = len(line) > MAX_REQUEST_BYTES
            response = rpc_error(None, -32700, "parse error: invalid Unicode")
        else:
            response = None
        if oversized:
            while not line.endswith("\n"):
                line = stdin.readline(min(MAX_REQUEST_BYTES + 1, 65536))
                if not line:
                    break
            response = rpc_error(None, -32600, "request exceeds maximum line size")
        elif response is None:
            if not line.strip():
                continue
            try:
                request = json.loads(
                    line, parse_constant=reject_non_json_constant,
                    object_pairs_hook=unique_object,
                )
            except (ValueError, RecursionError):
                response = rpc_error(None, -32700, "parse error")
            else:
                try:
                    response = handle_request(ctx, request)
                except Exception:  # noqa: BLE001 - isolate unexpected request failures
                    response = rpc_error(None, -32603, "internal error while handling request")
        if response is not None:
            # ASCII escapes preserve valid UTF-8 output even for a malformed
            # client's surrogate-containing identifier or an OS error string.
            try:
                encoded = json.dumps(response, ensure_ascii=True, allow_nan=False)
            except (TypeError, ValueError, RecursionError):
                encoded = json.dumps(rpc_error(None, -32603, "response could not be serialized"))
            stdout.write(encoded + "\n")
            stdout.flush()
    return 0
