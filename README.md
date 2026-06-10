# CoProgrammer

CoProgrammer is an open protocol and toolkit for multi-agent software
development in the AI coding era.

CoProgrammer 同时支持中文团队协作场景：PR 分支消化报告可以用
`zh-CN` 输出，也可以通过仓库变量切回英文。

The project starts from one practical belief:

> AI-era merging is not only a text conflict problem. It is a semantic
> integration problem.

When several humans and AI agents work in parallel, the hard part is no longer
choosing one side of a merge conflict. The hard part is understanding what each
branch learned, preserving the useful insight, discarding noise, and rebuilding
the smallest safe patch on top of the current main branch.

## Where CoProgrammer Sits

CoProgrammer is **not** another parallel-agent orchestrator. It is the missing
layer between orchestrators and the merge queue:

```text
UPSTREAM      agent runtimes & orchestrators
              (Conductor, Sculptor, Vibe Kanban, Claude Squad,
               Codex, Copilot Cloud Agent, OpenHands, ...)
              → produce parallel branches
                      │
COPROGRAMMER  integration & governance layer
              protocol → telemetry → conflict forecast →
              branch digest → integration plan →
              minimal patch → integration record → policy update
                      │
DOWNSTREAM    landing infrastructure
              (Merge Queue / Merge Trains / Mergify / Graphite,
               CI, CODEOWNERS, branch protection)
```

Orchestrators solve "run N agents in parallel without stepping on each other."
CoProgrammer solves "when N branches come back, decide what deserves to reach
`main`, and rebuild it safely under main-branch constraints." See
`docs/ORCHESTRATOR_INTEGRATION.md` for concrete hookup recipes.

## Core Loop

CoProgrammer organizes collaboration as a continuous loop:

1. **Protocol before coding**: define main-branch principles, module
   boundaries, shared contracts, protected files, and agent permissions.
2. **Telemetry during coding**: agents publish heartbeats, contract changes,
   current file ownership, experiments, and blockers.
3. **Digest after coding**: a feature branch is summarized by intent, core
   contribution, noise, contract changes, risks, and integration plan.
4. **Semantic integration**: instead of directly merging a large AI branch, an
   integration patch is rebuilt from latest `main` under main-branch
   constraints.
5. **Validation and feedback**: tests, contract checks, owner review, and merge
   records update the protocol for the next cycle.

## Repository Map

```text
.
├── docs/                 Research route, framework, and MVP design
├── protocols/            Human-readable collaboration protocols
├── research/             Structured research leads and prior-art data
├── schemas/              JSON schemas for machine-readable agent artifacts
├── templates/            Task, heartbeat, digest, and integration templates
├── src/coprogrammer/     First CLI scaffold
├── tests/                Unit tests for the CLI scaffold
├── AGENTS.md             Minimal stable instructions for coding agents
├── .coprogrammer.json    Project policy config
└── .github/              PR template, issue templates, CI, and PR digest workflow
```

Start with:

- `docs/COORDINATION_LIFECYCLE.md` for the before/during/after collaboration
  loop: project covenant, Manager Plane synchronization, and post-PR semantic
  integration;
- `docs/ECOSYSTEM_EXTENSION_STRATEGY.md` for the research method and MCP,
  skill, plugin, GitHub automation, and open-source library integration plan;
- `docs/PLUGIN_QUICKSTART.md` for installing and using the repo-local
  CoProgrammer Codex plugin;
- `docs/COMPREHENSIVE_RESEARCH_PLAN.md` for the research program and six-week sprint;
- `docs/RESEARCH_UPDATE_2026-05-25.md` for the latest Manager Plane evidence update;
- `docs/RESEARCH_PROTOCOL.md` for how to capture and evaluate research leads;
- `docs/FAILURE_TAXONOMY.md` for the failure modes CoProgrammer targets;
- `docs/RESEARCH_LANDSCAPE.md` for current tool landscape and gaps;
- `docs/OPEN_SOURCE_SCAN.md` for adjacent open-source projects and reusable features;
- `docs/FEATURE_GAP_MATRIX.md` for product-level comparison;
- `docs/DISCUSSIONS.md` for discussion categories and research intake;
- `docs/ARCHITECTURE.md` for the system architecture;
- `docs/MANAGER_PLANE.md` for the cloud/self-hosted control plane hypothesis;
- `docs/MANAGER_API_SKETCH.md` for the first Manager API surface;
- `docs/EVENT_LOG_PROTOTYPE.md` for the local Manager Plane prototype;
- `docs/AGENT_RUNTIME_INTEROP.md` for integrating with Codex, Copilot, OpenHands, and other runtimes;
- `docs/CONTEXT_FILE_STRATEGY.md` for keeping `AGENTS.md` small and structured state separate;
- `docs/INTEGRATION_PATCH_DESIGN.md` for the minimal-patch reconstruction design;
- `docs/MODEL_ROUTING_POLICY.md` for routing simple work to `codex-5.3` and high-risk work to review;
- `docs/HIGH_STAR_PROJECT_SCAN_2026-05-26.md` for high-star project patterns to borrow;
- `docs/FRAMEWORK.md` for the research framework;
- `docs/ORCHESTRATOR_INTEGRATION.md` for feeding Conductor, Sculptor, Vibe
  Kanban, and cloud-agent branches into CoProgrammer;
- `docs/STRATEGY_MEMO_2026-06-10.md` for the latest positioning and priority
  decisions;
- `docs/EVAL_PLAN.md` for the AgenticFlict-based evaluation plan;
- `ACKNOWLEDGMENTS.md` for the projects we learn from and how we credit them.

## Install (pick your surface)

CoProgrammer ships one core through several thin wrappers — use whichever
your stack already speaks (details: `docs/DISTRIBUTION_STRATEGY.md`):

**MCP server** (Claude Code, Codex, Cursor, any MCP client):

```json
{ "mcpServers": { "coprogrammer": {
    "command": "uvx", "args": ["coprogrammer", "mcp", "serve"] } } }
```

Tools exposed: `digest_branch`, `manager_status`, `manager_forecast`,
`lease_request`, `heartbeat`, `contract_propose`.

**Agent Skills** (SKILL.md open standard — Claude Code, Codex CLI, Gemini
CLI, Copilot, Cursor, 35+ tools): copy `plugins/coprogrammer/skills/*` into
your agent's skills directory.

**GitHub Action** (PR branch digest, zero setup):

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: QIU-Guanzong/CoProgrammer@v0
  with: { language: zh-CN }
```

**CLI**: `pipx install coprogrammer` (or from source:
`python -m pip install -e .`).

**Codex plugin**: `codex plugin marketplace add <this repo>` — see
`docs/PLUGIN_QUICKSTART.md`.

## First MVP

The first useful version is a **Branch Digest Bot**:

- reads a PR diff and commit history;
- detects contract-sensitive files and architecture risk signals;
- generates a branch digest draft;
- asks reviewers to approve an integration plan before merging;
- keeps direct AI-generated mega-branches out of `main`.

The first GitHub Actions version is included in
`.github/workflows/pr-digest.yml`. It generates `branch-digest.md`, uploads it
as an artifact, and updates a stable PR comment for same-repository PRs.

This repository already contains a minimal local CLI prototype:

```bash
python -m coprogrammer digest --base origin/main --head HEAD --output branch-digest.md
python -m coprogrammer digest --base origin/main --head HEAD --language zh-CN
python -m coprogrammer digest --base origin/main --working-tree
python -m coprogrammer config validate
python -m coprogrammer agents check
python -m coprogrammer manifest validate templates/change-manifest.json
python -m coprogrammer integration-plan validate templates/integration-plan.json
python -m coprogrammer heartbeat new --agent agent-a --task "Implement login API"
python -m coprogrammer manager lease request --holder agent-a --pattern "src/api/**"
python -m coprogrammer manager contract propose --proposer agent-a --kind api --name "POST /login" --summary "Add login endpoint"
python -m coprogrammer manager forecast --base origin/main --fail-on-conflict
python -m coprogrammer manager status
```

Language can also be controlled by `COPROGRAMMER_LANGUAGE=en|zh-CN`.

For local development:

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## Project Goals

- Create an open protocol for AI-assisted multi-agent collaboration.
- Make branch intent, contracts, and insights first-class artifacts.
- Reduce merge conflicts by forecasting ownership and contract collisions early.
- Preserve useful experiments without merging noisy generated code.
- Help reviewers inspect integration plans instead of massive raw diffs.

## Non-Goals

- CoProgrammer is not a replacement for Git, GitHub, GitLab, or CI.
- CoProgrammer does not blindly auto-merge AI output.
- CoProgrammer does not treat formatting churn, dependency upgrades, and feature
  logic as the same kind of change.

## Status

This is an early research and tooling scaffold. The current focus is:

1. protocol design;
2. branch digest format;
3. lightweight CLI;
4. GitHub Action integration;
5. project policy and risk scoring;
6. later: semantic integration bot and multi-agent orchestrator.
