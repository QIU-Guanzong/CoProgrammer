"""Only read operations are exposed; command execution remains explicit CLI."""
from pathlib import Path

from . import collaboration, evidence, workflow, workspace


def declarations(string_schema):
    identity = {"type": "string", "pattern": collaboration.ID_PATTERN, "minLength": 1, "maxLength": 64}
    local_path = string_schema(4096)
    base = {**string_schema(512), "default": "HEAD"}
    rows = []

    def add(name, description, properties, required):
        rows.append({"name": name, "description": description,
                     "inputSchema": {"type": "object", "properties": properties,
                                     "required": required, "additionalProperties": False}})

    add("workspace_snapshot", "Read bounded Git content fingerprint, revisions, sanitized repository identity and dirty paths; no fetch or writes.", {"base": base}, [])
    add("task_dispatch", "Preview eligible tasks for this session/client/worktree. No claim, pulse or worker launch; claim rechecks atomically.", {
        "session": identity, "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20}}, ["session"])
    add("manager_handoff", "Read portable task context with version/revisions, content and optional local check statuses. Omits claim tokens, message bodies and machine paths; no ownership transfer.", {
        "session": identity, "task_id": identity, "base": base,
        "checks": {"type": "array", "items": local_path, "maxItems": 16}}, ["session", "task_id"])
    add("handoff_check", "Compare a local JSON handoff with this clone; alignment is not approval or a cross-computer lease. Does not import state or contact another agent.", {
        "path": local_path, "base": string_schema(512)}, ["path"])
    add("check_verify", "Verify a bounded local check record against current content and environment. Optional command arguments are hashed, never executed. Records are unauthenticated.", {
        "path": local_path, "command": {"type": "array", "items": string_schema(4096, allow_empty=True), "minItems": 1, "maxItems": 128},
        "max_age_seconds": {"type": "integer", "minimum": 1, "maximum": 604800, "default": 86400}}, ["path"])
    return rows


def dispatch(name, ctx, args):
    if name == "workspace_snapshot":
        return workspace.snapshot(ctx.cwd, args.get("base", "HEAD"))
    if name == "task_dispatch":
        return workflow.dispatch(ctx.log_path, ctx.cwd, args["session"], args.get("limit", 20))
    if name == "manager_handoff":
        return workflow.handoff(ctx.log_path, ctx.cwd, args["session"], args["task_id"],
                                args.get("base", "HEAD"), [ctx.cwd / Path(p) for p in args.get("checks", [])])
    if name == "handoff_check":
        return workflow.compare(ctx.cwd, ctx.cwd / Path(args["path"]), args.get("base"))
    return evidence.verify(ctx.cwd, ctx.cwd / Path(args["path"]), args.get("command"),
                           max_age_seconds=args.get("max_age_seconds", 86400))
