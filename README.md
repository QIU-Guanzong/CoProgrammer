# CoProgrammer

**Shared tasks, file leases and handoffs for Codex, Claude Code and Copilot.**

CoProgrammer coordinates coding agents working in separate Git worktrees.
Claim scoped tasks atomically, spot blocked work, exchange durable handoffs,
and turn branch changes into reviewable digests through a local CLI and MCP
server. Python 3.10+, Git 2.36+, no runtime Python dependencies.

Use **Codex, Claude Code, or GitHub Copilot** for development, **GitHub** for PR
review, and optionally **Claude, GLM, or DeepSeek** for a second opinion on a
specific set of commits. Maintainers decide what reaches `main`.

[简体中文](README.zh-CN.md) · [Run the demo](#try-the-preview) ·
[Connect a client](docs/knowledge/README.md) ·
[Ecosystem comparison](docs/research/ecosystem-2026-09-30.md) ·
[Contributing](CONTRIBUTING.md) · [MIT](LICENSE)

> **0.2.0a1 source preview.** The multi-platform upgrade is available in
> [PR #1](https://github.com/QIU-Guanzong/CoProgrammer/pull/1).
> Client configuration generators and provider adapters are implemented;
> live client/provider verification is still pending. Use the source setup below.

## New in this source update

- **One-command offline demo:** two real Git worktrees exercise claims,
  dependency and path guards, message receipt and task completion. No model key.
- **One collaboration briefing:** ready work, blockers, stale windows, open
  decisions and next actions, available through both CLI and MCP.
- **Less repeated state replay:** status views reuse validation within a
  snapshot, while transactions and standalone history checks stay intact.
  See the [reproducible benchmark](docs/upgrade-2026-09-30/performance.md).
- **A complete Chinese entrypoint** and a [six-project research update](docs/research/ecosystem-2026-09-30.md)
  explaining the choices behind this increment.

## When it helps

Suppose Codex is changing an API while Claude Code updates its callers in
another worktree. Both branches may pass their own tests while disagreeing on
the interface. A clean Git merge alone does not resolve that disagreement.

CoProgrammer gives the team a shared record:

| During the work | What reviewers can inspect |
| --- | --- |
| Define a task and its allowed paths | Intent, scope and shared contracts |
| Register each coding window | Client, task, worktree, branch and pulse freshness |
| Claim ready work and its path lease together | One owner per task and worktree, dependency and client checks |
| Check the claim before edits and commit | Current token, branch, lease and permitted paths |
| Exchange task messages and acknowledge receipt | Durable handoffs, replies and pending inboxes across restarts |
| Request an advisory lease and publish heartbeats | Current ownership, overlap and blockers |
| Generate a branch digest | Changed files, commits, protected paths and risk signals |
| Request optional model review | Suggestions tied to exact commits and captured diff evidence |
| Compare named review artifacts | Missing, stale, duplicate or partial reviews, risk notes and file-level disagreements |
| Prepare an integration plan | What to preserve, drop, rebuild or defer, plus required human decisions |

```text
Task scope → shared work state → branch digest → integration plan
                                                       ↓
                                      maintainer review + project CI
```

The local CLI, MCP server and GitHub Action use the same core. Leases coordinate
cooperating agents; they do not lock files. Integration plans remain drafts:
patch application, approval and merging stay with your existing review process.

## Try the preview

Requires **Python 3.10+** and **Git 2.36+**. Start with the offline demo; no model key
is needed.

```sh
git clone --branch codex/multi-platform-upgrade https://github.com/QIU-Guanzong/CoProgrammer.git
cd CoProgrammer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

coprogrammer demo
```

On Windows, create the environment with `python -m venv .venv` and activate it
in PowerShell with `.venv/Scripts/Activate.ps1`. The clone command above selects
the upgrade branch explicitly. For your own project, keep this environment
active, change to that project's checkout, and use its base branch.

The demo creates and cleans up a temporary repository and two worktrees. It
exercises the actual coordination code; the Codex/Claude names are local
session labels, not connected coding clients. Use `coprogrammer demo --json`
for step-by-step evidence. See [what the demo checks](docs/DEMO.md).

Then inspect your own repository:

```sh
coprogrammer integrations doctor
coprogrammer manager briefing
coprogrammer digest --base origin/main --head HEAD
```

`doctor` checks local tools and credential-variable presence without contacting
providers. `briefing` summarizes current local coordination. `digest` produces
a Markdown report; add `--language zh-CN` for Chinese output. Choose your own
repository's base branch when it differs from `origin/main`.

## Read the room before editing

```sh
coprogrammer manager briefing --session codex-api
coprogrammer manager briefing --json --limit 20 --fail-on-attention
```

Register the session first (below), or omit `--session` for a repository-wide
summary. The briefing explains blocked tasks and suggests the next checks.
Its MCP equivalent is `manager_briefing`. Message bodies and claim tokens are
omitted; counts remain complete when rows are truncated. A ready task still
needs a successful claim. [Briefing semantics and exit codes](docs/BRIEFING.md).

## Where it fits

CoProgrammer connects independent coding windows to the project's existing
review process. It complements tools that manage specifications, task memory
or terminal sessions.

| Your need | Start here |
| --- | --- |
| Exercise coordination before configuring any client | `coprogrammer demo` |
| Resume work and understand blockers | `coprogrammer manager briefing` |
| Add Skills, project instructions and MCP configuration | `coprogrammer setup --client codex` (preview) |
| Reserve a scoped task across worktrees | `coprogrammer manager task claim` |
| Review what changed and what evidence is missing | `digest` and `review-summary` |

The [source-backed comparison](docs/research/ecosystem-2026-09-30.md) covers
Beads, MCP Agent Mail, Overstory, agent-deck, GitHub Spec Kit and LangGraph,
including current maintenance and license observations. It is a comparison,
not a claim that those tools are installed or interoperable out of the box.

## Connect your tools

| Tool or service | Available in the preview |
| --- | --- |
| Codex | Native TOML configuration for the local MCP server |
| Claude Code | Project MCP configuration for the same coordination tools |
| GitHub Copilot in VS Code | Native MCP configuration |
| GitHub | Read-only PR handoff with base/head commits; branch digest Action |
| Claude API, GLM, DeepSeek | Optional structured review through explicit provider calls |

From the project you want to coordinate, generate the configuration for your
client:

```sh
coprogrammer integrations config --client codex
# Other clients: --client claude or --client copilot

coprogrammer manager lease request --holder codex-api --pattern 'src/api/**'
coprogrammer manager heartbeat --agent codex-api --task 'Update API response'
coprogrammer manager status
```

Configuration is printed for you to add to the client; existing settings are
not overwritten. The local MCP server exposes branch digests, status, conflict
forecasts, leases, heartbeats, contract proposals, window sessions, task dispatch,
discussions and bounded change waiting. Git worktrees share the repository's
local coordination log by default.

## Coordinate two coding windows

To add reusable workflows and project guidance before starting the windows:

```sh
coprogrammer knowledge list
coprogrammer setup --client codex --include-content  # preview only
coprogrammer setup --client codex --apply
```

Use `claude` or `copilot` for those clients. Setup includes six Skills,
Markdown instructions and task/handoff templates, plus native MCP configuration.
It creates missing files, preserves existing project instructions, and refuses
conflicting skills, generated documents or MCP settings. Use `--no-mcp` when
keeping existing configuration and integrating the server separately.

The MCP server also exposes twelve bundled Markdown resources and two prompt
templates for task briefs and handoffs. Resources are read-only catalog entries;
prompts prepare document context and do not execute tasks. Setup does not prove
the client connected. See the [setup and knowledge guide](docs/knowledge/README.md)
for native paths, conflict handling and connection verification.

After installing the preview, run each block in that window's existing Git
worktree. Each window gets a unique session ID, even if both use the same client.

```sh
# Window A: Codex, API worktree
coprogrammer manager session register --session codex-api --client codex --task API-42

# Window B: Claude Code, UI worktree
coprogrammer manager session register --session claude-ui --client claude --task API-42
```

From window A, save a handoff; from window B, read it:

```sh
# Window A
coprogrammer manager message send --from codex-api --to claude-ui \
  --task API-42 --kind handoff --key api-handoff-v1 \
  --body 'API changes are ready for review. Check the caller and report the checks you ran.'

# Window B
coprogrammer manager sync --session claude-ui
coprogrammer manager message inbox --session claude-ui --task API-42
# Replace msg_... with the returned message ID.
coprogrammer manager message ack --session claude-ui --id msg_...
```

Use `session pulse` to report progress or blockers, and `manager sync --after
evt_...` to resume from the previous `next_cursor`. Unacknowledged messages remain
in the inbox after restart. Identical sends with the same sender and `--key`
return the original message. Replies use `--reply-to msg_...`.

These operations also have MCP tools. Sessions carry optional provider/model
labels, so an OpenCode or other MCP-capable client using GLM or DeepSeek can use
the same workflow. Labels do not verify a provider connection. Freshness measures
explicit pulses, not whether a process is alive. Messages are local and pulled
by clients; they do not wake or inject text into another window. Receipt never
approves code or transfers a lease. See the [full workflow and limits](docs/collaboration/README.md)
and [comparison with Agent Mail, agent-deck, Overstory and Claude Teams](docs/collaboration/research.md).

## Dispatch work without conflicting owners

In a registered window, create a task with its allowed paths and optional
dependencies or client labels. A worker claims a compatible ready task:

```sh
coprogrammer manager task create --session codex-api --id api-v2 \
  --title 'Update the API response' --pattern 'src/api/**' --client codex
coprogrammer manager task claim --session codex-api --id api-v2
# Save the returned claim_id and substitute it below.
coprogrammer manager task guard --session codex-api --id api-v2 \
  --claim claim_... --file src/api/routes.py
coprogrammer manager task board
```

Claiming atomically reserves the paths. Competing tasks, unfinished dependencies,
stale windows and another task in the same worktree block the claim. Use separate
worktrees for parallel development. Before committing, run the guard with
`--working-tree` to check staged, unstaged and untracked nonignored paths,
including both sides of renames. Renew long-running claims with `task renew`.

Use `task finish` with an accurate work summary to release the lease, or
`task release` to requeue. An expired claim needs explicit creator recovery;
it never silently moves to a new owner. Guards are cooperative checks and do
not intercept arbitrary writes. Completion does not certify tests or approval.

After draining `manager sync`, use `manager wait --session claude-ui --after
evt_...` for a bounded wait, and `manager message thread --session claude-ui
--task api-v2` for the task conversation. See the
[complete CLI/MCP workflow, recovery and platform limits](docs/scheduling/README.md).

## Request and compare model reviews

To preview an optional review request locally:

```sh
coprogrammer review --provider deepseek --model YOUR_MODEL_ID \
  --base origin/main --head HEAD
```

Replace `YOUR_MODEL_ID` with an available model from your provider. Review
commands contact the provider only when you add `--send`; this sends the
captured diff and may incur provider charges. Model advice is distinct from a
maintainer approval. See the [multi-platform guide](docs/MULTI_PLATFORM_QUICKSTART.md)
for credentials, request limits, client setup and draft plan generation.

After saving review artifacts, compare them locally against the same commits:

```sh
coprogrammer review-summary --base origin/main --head HEAD \
  --review claude=.coprogrammer/claude-review.json \
  --review glm=.coprogrammer/glm-review.json \
  --expect deepseek --format markdown
```

Missing files and expected reviewers stay visible. The summary checks recorded
evidence, preserves risks and conflicting recommendations, and never calls a
provider or selects a winning review. Reviewer identity and independence are
not authenticated. The same read-only operation is available through the
`review_summary` MCP tool. See the [review summary guide](docs/review-summary/README.md).

## Build a shared workflow

Assign roles by task, independently of which model or client performs them.
Each handoff should name the goal, scope, base/head commits, checks actually
run, unresolved questions and next owner. Keep review disagreements visible.

We draw on [gstack](https://github.com/garrytan/gstack)'s explicit planning,
review and verification stages, alongside GitHub's maintainer review model.
For CoProgrammer, that means portable artifacts and checks tied to the code
being reviewed. See the [design notes and sources](docs/github-intro/collaboration-notes.md)
and [contributor handoff checklist](CONTRIBUTING.md#handoff-and-review).

## Documentation

| Start here | Purpose |
| --- | --- |
| [Offline demo](docs/DEMO.md) | A repeatable two-worktree example without credentials |
| [Collaboration briefing](docs/BRIEFING.md) | Ready work, blockers, bounded output and CLI/MCP semantics |
| [Chinese introduction](README.zh-CN.md) | Installation, demonstration and everyday use in Chinese |
| [Multi-platform quickstart](docs/MULTI_PLATFORM_QUICKSTART.md) | Codex, Claude, Copilot, GitHub and model-provider setup |
| [Coordination lifecycle](docs/COORDINATION_LIFECYCLE.md) | Before, during and after coding |
| [Multi-window collaboration](docs/collaboration/README.md) | Sessions, task inboxes, acknowledgements and resumable CLI/MCP sync |
| [Task scheduling and communication](docs/scheduling/README.md) | Atomic claims, dependency routing, edit guards, recovery, waits and discussions |
| [Skills, MCP and Markdown](docs/knowledge/README.md) | Project setup, packaged knowledge catalog and MCP resources/prompts |
| [Collaboration research](docs/collaboration/research.md) | Current open-source approaches and the implementation choices they informed |
| [Configuration](docs/CONFIGURATION.md) | Protected paths, language and project policy |
| [GitHub Actions](docs/GITHUB_ACTIONS.md) | PR digests and workflow setup |
| [Agent Plugins and Claude Code](docs/PLUGIN_QUICKSTART.md) | Installable package for Codex-compatible clients and Claude Code |
| [Architecture](docs/ARCHITECTURE.md) | Components and artifact boundaries |
| [Research landscape](docs/RESEARCH_LANDSCAPE.md) | Prior art and research questions |
| [Latest ecosystem research](docs/research/ecosystem-2026-09-30.md) | Six adjacent projects and the changes they informed |
| [Portable distribution research](docs/RESEARCH_UPDATE_2026-09-27.md) | Plugin packaging and content-bound evidence |
| [Evaluation plan](docs/EVAL_PLAN.md) | How we intend to measure integration quality |
| [Acknowledgments](ACKNOWLEDGMENTS.md) | Sources, design influences and attribution |

The repository contains implemented tooling and research proposals. In design
documents, sections marked "future" describe planned work. A hosted Manager,
automatic patch reconstruction and automatic merging are outside this preview.

## Contribute

Useful contributions include reproducible coordination failures, client setup
reports, focused fixes and evidence from real PRs. Start with a small issue or
change that explains the problem, expected behavior and validation.

```sh
python -m unittest discover -s tests
coprogrammer config validate
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development rules and review
artifacts. Source code is under [MIT](LICENSE).
