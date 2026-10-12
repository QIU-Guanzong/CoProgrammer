# CoProgrammer

**Teamwork for coding agents.**

Shared tasks, file boundaries and durable handoffs for **Codex, Claude Code and
GitHub Copilot** working in the same Git repository.

[![CI](https://github.com/QIU-Guanzong/CoProgrammer/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/QIU-Guanzong/CoProgrammer/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-black)](LICENSE)

[简体中文](README.zh-CN.md) · [Try it](#try-the-preview) ·
[Two-window walkthrough](docs/GETTING_STARTED.md) ·
[Connect your client](docs/knowledge/README.md) · [Releases](https://github.com/QIU-Guanzong/CoProgrammer/releases)

## The problem

Codex is changing an API. Claude is updating its callers. Both need to know who
owns the files, when the upstream task is finished, and what happened before a
window restarted. Separate Git branches keep edits apart; the collaboration
still needs shared state.

CoProgrammer records **who owns a task, which paths it covers, what blocks it,
and what the next window needs to know**. Your coding tools write the code;
CoProgrammer coordinates their work through a local CLI and MCP server.

| Without a shared record | With CoProgrammer |
| --- | --- |
| Two windows try to claim overlapping work | Atomic task claims check owners, worktrees and path leases. |
| A worker starts before an upstream task finishes | Dependencies keep the task blocked until its prerequisite is done. |
| A handoff disappears in a terminal | Messages and explicit receipts persist across restarts. |
| A passing test refers to yesterday's files | Check receipts detect changed content, command, runtime or age. |
| Another computer has a different checkout | A portable handoff compares package version, HEAD, base and file content. |

## Try the preview

Requires **Python 3.10+** and **Git 2.36+**. Use an active Python virtual environment.
There are no runtime Python dependencies or model keys needed for the demo.

```sh
python -m pip install --pre --upgrade coprogrammer
coprogrammer demo
```

The demo creates two real Git worktrees, runs task claims, dependency and overlap
checks, sends a handoff, acknowledges it and completes the tasks. It checks each
result and cleans up the temporary project. No coding client or model is launched.

An excerpt from an actual run:

```text
[passed] Create two Git worktrees: Two branches share one repository and one Manager event log.
[passed] Block unfinished dependencies: Claude cannot claim documentation until the API task is finished.
[passed] Reject overlapping work: A different worktree cannot claim src/api.py while Codex holds src/**.
```

[What the demo checks →](docs/DEMO.md)

## Use it in your project

The `start` and `status` entry points require **0.3.0a2+**. Start in a committed Git
checkout on a named branch. Each coding window should use its own Git worktree.
Add `.coprogrammer/` to your project's `.gitignore` to keep local runtime state
out of commits.

```sh
# In the worktree used by Codex
coprogrammer start --client codex --session codex-api --task api-v2
coprogrammer status --session codex-api

# In the separate worktree used by Claude Code
coprogrammer start --client claude --session claude-ui --task api-v2
coprogrammer status --session claude-ui
```

`start` registers this window and previews client setup. It does not launch a
coding tool or install configuration. Add `--dry-run` to preview registration;
use `--resume` to explicitly refresh the same registered window after a break.
Status reads never refresh sessions. Default session freshness lasts five minutes.

In the Codex worktree, create a scoped task and inspect the next action:

```sh
coprogrammer manager task create --session codex-api --id api-v2   --title 'Update the API' --pattern 'src/api/**' --client codex
coprogrammer status --session codex-api
coprogrammer manager task claim --session codex-api --id api-v2
```

Claims return an ownership token. Use it with the existing guard and finish
commands; the [two-window walkthrough](docs/GETTING_STARTED.md) covers dependency
setup, messages, receipts and completion. Status distinguishes repository-wide
readiness from work eligible for the selected window.

### Connect Codex, Claude Code or Copilot

Preview the project-local Skills, Markdown guidance and MCP configuration:

```sh
coprogrammer setup --client codex --include-content
```

Review the output, then explicitly create missing files:

```sh
coprogrammer setup --client codex --apply
```

Use `claude` or `copilot` for those clients. Existing project instructions are
preserved; differing Skills or MCP configuration are reported as conflicts.
Reload the client and follow its normal project/MCP trust flow. Generated
configuration alone does not establish a connection.

MCP exposes the same local workflows. `workspace_status` provides the combined
status view; `task_dispatch` previews eligible tasks. The packaged plugin
contains six Skills, and the CLI serves twelve read-only Markdown resources.
[Client setup](docs/knowledge/README.md) · [Plugin installation](docs/PLUGIN_QUICKSTART.md)

## What else can it do?

| Need | Entry point |
| --- | --- |
| Inspect work and blockers | `coprogrammer status`; [status guide](docs/GETTING_STARTED.md) |
| Send and acknowledge handoffs | `manager message`; [communication guide](docs/AGENT_RUNTIME_INTEROP.md) |
| Check file scope before edits | `manager task guard`; [scheduling guide](docs/MULTI_PLATFORM_QUICKSTART.md) |
| Detect stale test results | `check run` / `check verify`; [check receipts](docs/VALIDATION_EVIDENCE.md) |
| Continue on another computer | `manager handoff` / `workspace compare`; [portable handoffs](docs/WORKSPACE_HANDOFF.md) |
| Review a branch for integration | `digest` / `integration-plan`; [CLI reference](docs/GETTING_STARTED.md#prepare-a-pr) |
| Request a second opinion | Explicit Claude, GLM or DeepSeek review; [multi-platform guide](docs/MULTI_PLATFORM_QUICKSTART.md) |

## How it fits

Use CoProgrammer when you already run coding agents and need shared ownership,
communication and review evidence across their worktrees. It complements your
existing coding tools and GitHub review process.

[gstack](https://github.com/garrytan/gstack) provides opinionated development and
review workflows; [Beads](https://github.com/gastownhall/beads) provides persistent
agent work tracking; [Gas Town](https://github.com/gastownhall/gastown) manages
multi-agent workspaces and orchestration. CoProgrammer focuses on local task
ownership, path coordination, durable handoffs and inspectable integration
artifacts through a small Python CLI/MCP package.
[Comparison and design choices →](docs/research/onboarding-2026-10-12.md)

Local worktrees share a Manager. Independent clones have separate Managers:
portable handoffs compare context and do not transfer a global lease. Path
leases are cooperative checks, not filesystem permissions. Check records are
unauthenticated local evidence. PR approval and merging follow your project's
normal rules. The demo does not establish native client or live provider connectivity.

## Contribute or get help

[Report a reproducible problem](https://github.com/QIU-Guanzong/CoProgrammer/issues) ·
[Propose an integration](https://github.com/QIU-Guanzong/CoProgrammer/discussions) ·
[Contributor guide](CONTRIBUTING.md)

Good first contributions include a small client setup example, a clearer error
message or a regression for a real worktree conflict. Include the command,
version, expected result and actual result; remove private code and credentials.
If CoProgrammer helps your team, a star helps others discover it.

For source development:

```sh
git clone https://github.com/QIU-Guanzong/CoProgrammer.git
cd CoProgrammer
python -m pip install -e .
python -m unittest discover -s tests
```

[MIT license](LICENSE). Preview software; feedback and concrete bug reports are welcome.
