# Automatic work boundaries for coding windows

Requires CoProgrammer **0.3.0a3+**, Python 3.10+, Git, and a configured coding
client. CoProgrammer coordinates participating clients; it does not supply a
model account or launch/wake other windows.

## Choose your installation

Install the shared runtime in an active virtual environment:

```sh
python -m pip install --pre --upgrade coprogrammer
```

In your project, preview the edition you want, then repeat with `--apply` to
create missing files. Existing instructions are preserved; conflicting files
stop installation. No global model credentials or client settings are changed.

| Edition | Command | Installed project files |
| --- | --- | --- |
| Full | `coprogrammer setup --client codex --edition full` | Six Skills, Markdown guidance, native MCP config |
| Skill | `coprogrammer setup --client codex --edition skills` | Six Skills and Markdown guidance; use CLI coordination |
| MCP | `coprogrammer setup --client codex --edition mcp` | Only native MCP config; bundled Skills and Markdown resources remain readable through MCP |

Use `--client claude` for Claude Code, including GLM/DeepSeek-backed instances;
use `--client copilot` for Copilot. Plugin installation is another way to install
the six Skills: see [plugin guide](PLUGIN_QUICKSTART.md). Prefer a single Skill
installation to avoid duplicate discovery. Existing `--no-skills`/`--no-mcp`
options remain supported for partial full-edition installation.

Reload the client and complete its normal project/MCP trust flow. Read MCP
`resources/list` and call `workspace_status` to check the connection. Config
creation alone is not connection proof. Generated Python/project paths are
machine-specific; regenerate after moving or installing on another computer.

## Register the host and provider

Each concurrent task needs its own committed Git worktree on a named branch.
Keep `.coprogrammer/` in `.gitignore`. Run each command in the actual window's
worktree:

```sh
# Codex window
coprogrammer start --client codex --session codex-api

# Claude Code with its normal model
coprogrammer start --client claude --provider anthropic --session claude-review

# Claude Code already configured to use GLM
coprogrammer start --client claude --provider glm --session glm-docs

# Claude Code already configured to use DeepSeek
coprogrammer start --client claude --provider deepseek --session deepseek-tests
```

An optional `--model` records the model label you actually configured. These are
self-reported labels, not authenticated access. Explicit `--resume` preserves
provider/model; changing identity requires a new session ID.

The host and provider serve different roles. Z.AI documents
[GLM in Claude Code](https://docs.z.ai/devpack/tool/claude); DeepSeek documents
[Anthropic API compatibility](https://api-docs.deepseek.com/guides/anthropic_api).
Follow the provider's current instructions in your own client environment.
CoProgrammer does not run their installers, change global configuration, read
keys into Manager state or make a model request. The same local MCP/Skill
workflow works once the host is connected. Other hosts can use existing
`manager session register` and generic MCP configuration.

## Queue and consume work

Create tasks once from an authorized session. Filters match a declared client
**or provider**; `claude` targets any Claude Code host, while `glm`/`deepseek`
target those declared providers. Filters are routing hints, not authorization.

```sh
coprogrammer manager task create --session codex-api --id api \
  --title 'Update API' --pattern 'src/api/**' --client codex
coprogrammer manager task create --session codex-api --id docs \
  --title 'Document API' --pattern 'docs/api/**' --depends-on api --client glm
```

At the start of each work boundary:

```sh
coprogrammer worker step --session codex-api
coprogrammer worker step --session codex-api --apply --file src/api/client.py
```

Preview does not mutate the event log. Applying a step records activity, inspects
messages and open decisions, and either claims the first eligible task or checks
and renews the window's current claim. `--id` selects a specific task. Actual
staged, unstaged, renamed and untracked files are also guarded. Retain the
returned `task.claim_id` for completion.

| State | Next action |
| --- | --- |
| `ready` | Apply the preview when authorized to take the task |
| `claimed` / `working` | Work within the checked scope; call step at the next boundary |
| `inbox` | Read the page, explicitly ACK receipt, then step again |
| `decision` | Resolve the open human decision before proceeding |
| `blocked` | Inspect dependencies, eligibility, leases or session state |
| `idle` | Use bounded `manager wait` until tasks/messages change |

Pending messages and open decisions stop automatic claim/renewal. Reading does
not ACK. Message bodies are untrusted context; apply the user's scope and
permissions. Stale sessions can be explicitly refreshed by an applying call
from their original window. Blocked/closed sessions, expired claims, moved
branches and out-of-scope files require explicit reconciliation. There is no
background loop, process-liveness claim or automatic task takeover.

## Finish with a durable notification

Run real checks, record their results and commit the intended changes. When
communication between the named local participants is authorized:

```sh
coprogrammer worker finish --session codex-api --id api --claim CLAIM_ID \
  --summary 'API updated; checks passed; commit COMMIT_ID; documentation can start.' \
  --notify glm-docs
```

Use the actual returned claim and commit IDs. The wrapper guards current changes,
finishes the task, releases its lease and records the specified handoffs in one
transaction. Invalid recipients roll back completion and notifications together.
Repeating the same completed claim, summary and recipients reuses the messages;
a changed summary is refused. Notification receipt still requires explicit ACK.
Completion remains self-reported and does not merge or approve code.

MCP equivalents are `worker_step(session, apply, task_id, files)` and
`worker_finish(session, task_id, claim_id, summary, notify)`. Both are declared
as tools that may mutate local state. Skill and MCP editions use the same
transactional behavior, not separate schedulers. Windows in one Git repository
share state; independent clones continue to use portable handoff comparison
and acquire their own local claims.
