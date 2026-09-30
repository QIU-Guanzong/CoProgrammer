"""MCP task dispatch tools; no model invocation or process launch."""
from . import collaboration, scheduler


def declarations(string_schema):
    identity = {"type": "string", "pattern": collaboration.ID_PATTERN, "minLength": 1, "maxLength": 64}
    ttl = {"type": "integer", "minimum": 1, "maximum": 604800, "default": 3600}
    tools = []

    def tool(action, description, properties, required):
        tools.append({"name": "task_" + action, "description": description, "inputSchema": {
            "type": "object", "properties": properties, "required": required, "additionalProperties": False}})

    tool("create", "Queue scoped work with dependencies and optional client eligibility. No worker launch or implied approval.", {
        "session": identity, "task_id": identity, "title": string_schema(2000),
        "patterns": {"type": "array", "items": string_schema(4096), "minItems": 1, "maxItems": 128},
        "depends_on": {"type": "array", "items": identity, "maxItems": 128},
        "clients": {"type": "array", "items": string_schema(256), "maxItems": 128},
    }, ["session", "task_id", "title", "patterns"])
    tool("claim", "Atomically claim one ready task and its path lease. Check dependencies, client eligibility, pulse freshness and worktree isolation. Save the returned claim_id.", {
        "session": identity, "task_id": identity, "ttl_seconds": ttl,
    }, ["session"])
    tool("renew", "Renew a current task lease using its claim token and original window/worktree/branch. Pulse the session first if stale.", {
        "session": identity, "task_id": identity, "claim_id": identity, "ttl_seconds": ttl,
    }, ["session", "task_id", "claim_id"])
    for action in ("finish", "release"):
        tool(action, ("Report completion and release this claim's lease. Completion is self-reported, not review approval."
                      if action == "finish" else "Release this claim and requeue its task; does not revert files or transfer ownership."), {
            "session": identity, "task_id": identity, "claim_id": identity, "summary": string_schema(16000),
        }, ["session", "task_id", "claim_id", "summary"])
    tool("reclaim", "Task creator explicitly requeues an expired/lost claim. Does not stop the old process; reconcile its work before reclaiming.", {
        "session": identity, "task_id": identity, "summary": string_schema(16000),
    }, ["session", "task_id", "summary"])
    tool("guard", "Before edits/commit, check claim token, live lease, session, branch and concrete paths. This check does not intercept filesystem writes.", {
        "session": identity, "task_id": identity, "claim_id": identity,
        "files": {"type": "array", "items": string_schema(4096), "maxItems": 128},
        "working_tree": {"type": "boolean", "default": False},
    }, ["session", "task_id", "claim_id"])
    tool("board", "Read tasks, dependency readiness and lease ownership health. No scheduling or mutation.", {}, [])
    return tools


def dispatch(name, ctx, args):
    action = name.removeprefix("task_")
    if action == "board":
        return scheduler.board(ctx.events())
    if action == "guard":
        from .scheduler_cli import working_files
        args = dict(args)
        if args.pop("working_tree", False):
            args["files"] = list(dict.fromkeys([*args.get("files", []), *working_files(ctx.cwd)]))
    return getattr(scheduler, action)(ctx.log_path, ctx.cwd, **args)
