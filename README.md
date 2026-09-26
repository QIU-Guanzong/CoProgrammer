# CoProgrammer

**Coordinate coding agents. Make each branch easier to review.**

CoProgrammer is an open-source protocol and toolkit for teams working with
multiple coding agents. It records who is changing what, surfaces overlapping
work, and turns branch changes into reviewable digests and integration plans.

Use **Codex, Claude Code, or GitHub Copilot** for development, **GitHub** for PR
review, and optionally **Claude, GLM, or DeepSeek** for a second opinion on a
specific set of commits. Maintainers decide what reaches `main`.

中文：让多个编程助手共享任务边界和协作状态，把分支改动整理为可审阅的摘要与集成计划。
[中文接入指南](docs/MULTI_PLATFORM_QUICKSTART.md) ·
[Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)

> **0.2.0a1 source preview.** The multi-platform upgrade is available in
> [PR #1](https://github.com/QIU-Guanzong/CoProgrammer/pull/1).
> Client configuration generators and provider adapters are implemented;
> live client/provider verification is still pending. Use the source setup below.

## When it helps

Suppose Codex is changing an API while Claude Code updates its callers in
another worktree. Both branches may pass their own tests while disagreeing on
the interface. A clean Git merge alone does not resolve that disagreement.

CoProgrammer gives the team a shared record:

| During the work | What reviewers can inspect |
| --- | --- |
| Define a task and its allowed paths | Intent, scope and shared contracts |
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

Requires **Python 3.10+** and **Git**. Start with a local digest; no model key is
needed.

```sh
git clone --branch codex/multi-platform-upgrade https://github.com/QIU-Guanzong/CoProgrammer.git
cd CoProgrammer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

coprogrammer config validate
coprogrammer digest --base origin/main --head HEAD
coprogrammer integrations doctor
```

On Windows, create the environment with `python -m venv .venv` and activate it
in PowerShell with `.venv/Scripts/Activate.ps1`. The clone command above selects
the upgrade branch explicitly. For your own project, keep this environment
active, change to that project's checkout, and use its base branch.

`digest` produces a local Markdown report. `doctor` checks local tools,
credential-variable presence and the shared state location; it does not verify
an authenticated connection.
Add `--language zh-CN` to generate Chinese digests.

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
forecasts, leases, heartbeats and contract proposals. Git worktrees share the
repository's local coordination log by default.

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
| [Multi-platform quickstart](docs/MULTI_PLATFORM_QUICKSTART.md) | Codex, Claude, Copilot, GitHub and model-provider setup |
| [Coordination lifecycle](docs/COORDINATION_LIFECYCLE.md) | Before, during and after coding |
| [Configuration](docs/CONFIGURATION.md) | Protected paths, language and project policy |
| [GitHub Actions](docs/GITHUB_ACTIONS.md) | PR digests and workflow setup |
| [Codex plugin](docs/PLUGIN_QUICKSTART.md) | Five reusable collaboration skills |
| [Architecture](docs/ARCHITECTURE.md) | Components and artifact boundaries |
| [Research landscape](docs/RESEARCH_LANDSCAPE.md) | Prior art and research questions |
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
