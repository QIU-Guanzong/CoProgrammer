# Explicit Claude Code task harness

This unreleased candidate contains `coprogrammer.claude_harness`; its unchanged
`0.3.0a7` metadata alone does not identify the build. In the Python environment
used by your worker, check the installed contents:

```sh
python -m coprogrammer.claude_harness --check --executable /trusted/path/to/claude
coprogrammer knowledge show templates/CLAUDE_TASK_HARNESS
```

`--check` reads no task, starts no native process and accesses no account or
Manager state. Exit 0 means discovery succeeded, 1 means unavailable, 2 means
invalid arguments. Select an already trusted executable with
`--executable /trusted/path/to/claude` in both check and execution commands.
The check does not pin a later invocation or establish model access. If missing,
follow [official installation instructions](https://code.claude.com/docs/en/setup)
or select an existing installation; CoProgrammer never installs or logs in.

For an optional local readiness probe, explicitly add:

```sh
python -m coprogrammer.claude_harness --check --probe-native \
  --executable /trusted/path/to/claude
```

This runs only version, help and auth-status commands, each bounded at five
seconds, with owned process cleanup. It emits version/declared flags and a fixed
logged-in/logged-out/unknown authorization label, withholding native/account
text. Exit 0 means local declarations and logged-in status passed; exit 1
identifies a local gap, and misuse returns 2. Missing help flags are unverified,
not proof of incompatibility. Native settings and network behavior may apply;
no task/model request, login or provider configuration is submitted by the probe.
Neither logged-in status nor `local_ready` proves model/provider connectivity.
Plain check still launches nothing. Probing requires check, never execute.

With your existing authorized configuration, inspect `/trusted/path/to/claude --version`,
`/trusted/path/to/claude --help` and `/trusted/path/to/claude auth status` locally before a model task. Keep account
details private. This implementation's local capability probe used native Claude
Code 2.1.299; version/help success alone does not validate a real model task.

## Run a scoped task

Work inside a committed Git project on a named branch. Register a window and
queue a task before previewing the worker; use `--resume` for an existing session:

```sh
coprogrammer start --client claude --session claude-docs --task docs
coprogrammer manager task create --session claude-docs --id doc-note \
  --title "Review docs/input.md and summarize it" --pattern 'docs/**' --client claude
coprogrammer worker run --session claude-docs -- \
  python -m coprogrammer.claude_harness --execute --executable /trusted/path/to/claude
```

Preview does not launch Claude or claim work. After reviewing scope and existing
account authorization, `--apply` permits one native Claude invocation with read tools:

```sh
coprogrammer worker run --session claude-docs --apply --timeout-seconds 120 -- \
  python -m coprogrammer.claude_harness --execute --executable /trusted/path/to/claude
```

For a task requesting file edits, explicitly select edit tools and optionally
notify a separately registered peer window:

```sh
coprogrammer worker run --session claude-docs --apply --timeout-seconds 120 \
  --notify peer-review -- python -m coprogrammer.claude_harness \
  --execute --executable /trusted/path/to/claude --access workspace-write
```

The same argv can be used in the existing bounded foreground `worker watch`.
Default access offers Read/Glob/Grep; workspace-write additionally offers
Edit/Write. This is built-in tool availability, not an OS sandbox. Existing
native permission settings still apply and may block tools. The invocation
exposes no MCP servers or Manager tools. Enterprise managed MCP requirements
may reject it; inspect that failure without removing the restriction.

The adapter uses a print-mode JSON result with a schema, no session persistence
and at most eight turns. It accepts only a successful non-error result envelope
with exact structured `{status, summary}` output. Native stderr and metadata
are withheld; malformed, excessive or failed results cannot complete a task.
Accepted output is limited to 128000 bytes; the temporary stdout file has no
hard write cap. Use the worker for its timeout, since standalone execute has none.
Denied tools yield blocked rather than done. The parent owns completion, edit
guards and process-group cleanup on timeout/interruption. Inspect retained
claims and edits before another explicit invocation; no coordinator retry is
added. Native internal transport behavior remains the client's own policy.

Review the project and native settings before execution: print mode can load
existing hooks, plugins and instructions. This adapter does not change native
permission mode, model, provider, account or global profile. See the official
[CLI reference](https://code.claude.com/docs/en/cli-reference) and
[structured output guide](https://code.claude.com/docs/en/headless).

## Receive completion messages explicitly

This adapter supports tasks only and refuses inbox packets. It never ACKs a
message. `--notify` sends a local completion handoff after a successful task;
it does not wake or authenticate another client. In the recipient's own window:

```sh
coprogrammer manager message inbox --session peer-review
# Review the delivered message, then use that exact message ID:
coprogrammer manager message ack --session peer-review --id msg_REPLACE_WITH_DELIVERED_ID
coprogrammer worker step --session peer-review
```

An unread inbox stops the next worker boundary even after task dependencies are
complete. Receive only known delivered messages through the CLI/MCP workflow.
`--handle-inbox` with this task-only adapter still fails; use a separately trusted
receipt-capable client for that option. Completion messages do not move code
between Git worktrees: review and explicitly transfer changes before peer work.

GLM and DeepSeek are provider configurations of a compatible coding client,
not independent CoProgrammer windows. `--client claude --provider glm` or
`deepseek` records a label without configuring connectivity. Their official
[GLM](https://docs.z.ai/devpack/tool/claude) and
[DeepSeek](https://api-docs.deepseek.com/guides/anthropic_api/) guides describe
Claude-compatible endpoints; current authorization, tools and structured
results still require separate real acceptance. This adapter does not configure
those endpoints or claim Codex provider compatibility.

Offline fake-client tests and installed task/message fixtures validate transport,
guards and receipts only. Cloud native installation/version checks passed; no
Claude/GLM/DeepSeek model task passed because authorized configuration was absent.
Codex's separate cloud task retained its claim after harness failure, with model
start unconfirmed. Windows native CI and WorkBuddy GUI remain untested.
