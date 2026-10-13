# Native runtime checks and an explicit harness work loop

Requires **0.3.0a5+**. Use a virtual environment and an already committed Git
project. Native clients still need their normal installation, account and trust.

## Install and check OpenClaw

```sh
python -m pip install --pre --upgrade coprogrammer
coprogrammer setup --client openclaw --edition full --include-content
# After reviewing the plan:
coprogrammer setup --client openclaw --edition full --apply
coprogrammer integrations verify --client openclaw
```

The verifier reports missing/conflicting installation files, discovers the actual packaged stdio tools/resources, then
uses an installed `openclaw` to validate an isolated temporary profile and probe
the MCP server. It reports native discovery separately from model connection.
Native diagnostics are not copied into reports. It does not read authentication
stores, call a model or repair your global settings.

For embedded OpenClaw, setup creates
`.coprogrammer-kit/openclaw/profile.json` with `agents.defaults.workspace` and
`mcp.servers.coprogrammer`. To run OpenClaw with it, set `OPENCLAW_CONFIG_PATH`
to that absolute file path and `OPENCLAW_STATE_DIR` to a project-local ignored
runtime directory. Configure the model through your normal authorized account
flow; this isolated profile deliberately contains no account data. The older
node recipe remains for explicit node integration.

Official references: [MCP configuration](https://docs.openclaw.ai/gateway/config-extensions),
[native MCP probe](https://docs.openclaw.ai/cli/mcp/registry).

## WorkBuddy project discovery

```sh
coprogrammer setup --client workbuddy --edition full --include-content
coprogrammer setup --client workbuddy --edition full --apply
coprogrammer integrations verify --client workbuddy
```

Version a5 installs Skills in `.codebuddy/skills/` and MCP in
`.workbuddy/mcp.json`, following the current official
[project configuration guide](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)
and [MCP guide](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide).
Open the actual project in WorkBuddy and complete its normal trust flow.
The verifier checks the CoProgrammer transport only; it cannot assert WorkBuddy
GUI discovery. Older a4 import kits remain untouched. A conflicting existing
native config requires manual integration; no global MCP settings are rewritten.

## Execute a trusted agent harness

Register one session per worktree and queue a task as in the
[automatic collaboration guide](AUTOMATIC_COLLABORATION.md). A harness command
consumes one UTF-8 JSON object on stdin and returns one JSON object on stdout:

```sh
coprogrammer worker run --session harness-review -- python /path/to/your_harness.py
coprogrammer worker run --session harness-review --apply --notify docs-window \
  -- python /path/to/your_harness.py
```

Preview never starts the command or claims work. Applying pulses the session,
checks inbox/decisions, claims or renews eligible work, and invokes the explicitly
chosen command without a shell. A worktree lock prevents two runner invocations
from executing there at once. The runner then guards actual changes, finishes the
original claim and sends the selected local handoffs.

Task input has `format: coprogrammer.harness-task.v1`, `kind: task`, the session,
workspace and claimed task. Return `{"status":"done","summary":"..."}` or
`{"status":"blocked","summary":"..."}`. Execution is not a code review or
permission boundary; the command uses its own permissions. A bad reply, failed
command, timeout or scope violation retains the claim and edits for inspection.
There is no implicit retry or rollback of external process side effects.

### Receive messages inside the harness

```sh
coprogrammer worker run --session harness-review --apply --handle-inbox \
  -- python /path/to/your_harness.py
```

By default pending messages stop execution. With this explicit option, the
command receives `kind: inbox` and the delivered message records, and may return
`{"status":"received","summary":"...","acknowledge":["DELIVERED_ID"]}`.
Only its explicit delivered IDs are acknowledged, atomically. The handler may
not change project content; receipt does not approve instructions or transfer
ownership. This call handles the inbox only; call the runner again to claim
work. Undelivered IDs, invalid output and project edits leave messages pending.
Ignored files and transient edits restored between checks remain outside the
content check, as with other local check receipts.

Use a bounded foreground loop in your harness if desired; the package does not
install a daemon, a login hook or a platform chat bridge. No runner is exposed as
an MCP arbitrary-command tool.

## A reproducible fixture, with no model bill

In a disposable project, register a harness session and queue a task covering
`docs/**`, then use the bundled deterministic fixture:

```sh
coprogrammer worker run --session harness-review --apply --handle-inbox \
  -- python -m coprogrammer.example_harness
```

The fixture receives inbox records or creates `docs/runner-fixture.txt`. It is
not an AI model. Replace it with your own actual runtime after checking your
account and permissions.

## Current native evidence

On 2026-10-13, installed OpenClaw 2026.6.8 accepted an isolated profile, discovered
all six workspace Skills and discovered the MCP catalog. Its actual
`SessionMcpRuntime` performed session registration, task creation, claim and
completion with a local handoff in real worktrees. Edits and call selection were
driven by the test controller; no model was invoked. The harness runner receives
that handoff, records a receipt and completes the downstream fixture.

WorkBuddy 5.7.7 was obtained from the official download history and its application
signature verified. UI inspection timed out; further WorkBuddy GUI testing was
deferred at the user's request. The local OpenClaw provider lacked configured
credentials and Claude CLI was not logged in. These receipts establish native
transport and coordination behavior, not autonomous model completion, WorkBuddy
GUI connection or installation success on every user's computer.
