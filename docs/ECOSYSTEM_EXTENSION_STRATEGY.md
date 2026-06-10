# Ecosystem Extension Strategy

Last updated: 2026-06-04

This document defines how CoProgrammer should research external tools and use
MCP servers, Codex skills, Codex plugins, GitHub automation, and open-source
libraries to cover the full AI-assisted development lifecycle.

For the lifecycle itself, see `docs/COORDINATION_LIFECYCLE.md`.

## Problem

AI coding agents can create branches, pull requests, and local patches faster
than maintainers can preserve direction, synchronize work, and integrate
changes safely. No single existing extension surface fixes this end to end.

The right design is a layered system:

| Need | Best Surface |
| --- | --- |
| Durable team rules | `AGENTS.md`, `.coprogrammer.json`, protocol docs |
| Repeatable agent workflow | Codex skill |
| Shared installation across a team | Codex plugin |
| Live repo state and external tools | MCP server |
| GitHub-native PR checks and comments | GitHub Action or GitHub App |
| Deterministic code analysis or patching | Open-source code intelligence libraries |
| Human decisions and audit history | Manager Plane events and decision records |

## Research Method

Research should start from failure modes, not from tool hype.

1. Pick a failure mode from `docs/FAILURE_TAXONOMY.md`.
2. Map the failure mode to one lifecycle stage.
3. Search for prior art that already solves part of that stage.
4. Classify the source as protocol, runtime, PR automation, patch engine,
   static analysis, dashboard, or research reference.
5. Verify the project through primary sources: official docs, official GitHub
   repo, specification, or paper.
6. Evaluate against the CoProgrammer object model: policy, lease, heartbeat,
   contract, decision, digest, integration plan, integration record.
7. Decide whether to borrow, integrate, wrap, monitor, or reject.

### Evaluation Matrix

| Criterion | Question |
| --- | --- |
| Lifecycle fit | Does it help before coding, during coding, after PR, or feedback? |
| Object fit | Does it map cleanly to leases, decisions, contracts, digests, or records? |
| Determinism | Can it produce stable output without relying on LLM improvisation? |
| Integration cost | Can it run locally or in CI without heavy infrastructure? |
| Security model | Does it need tokens, repo write access, browser access, or secrets? |
| Output format | Can findings become JSON, SARIF, PR comments, or Manager events? |
| Maintenance | Is it active, documented, licensed, and usable without vendor lock-in? |
| Differentiation | Does it strengthen CoProgrammer's semantic integration layer rather than turn it into a generic code reviewer? |

## Extension Surface Decision Tree

Use the smallest surface that matches the job.

### AGENTS.md

Use for stable repository instructions:

- project purpose;
- validation commands;
- protected workflow reminders;
- how agents should request leases and record decisions.

Do not store live state here. Live coordination belongs in Manager events.

### Codex Skill

Use a skill when the team needs a repeatable workflow that an agent should
follow reliably.

CoProgrammer should eventually provide repo or plugin skills such as:

- `coprogrammer-project-covenant`: create or audit `AGENTS.md`,
  `.coprogrammer.json`, CODEOWNERS, and protocol docs.
- `coprogrammer-task-brief`: turn a human request into a scoped task brief.
- `coprogrammer-active-sync`: check Manager status, request leases, propose
  contract changes, and record heartbeats.
- `coprogrammer-pr-digest-review`: read a branch digest and produce
  preserve/drop/rebuild/defer decisions.
- `coprogrammer-integration-plan`: convert an approved digest into a minimal
  integration plan.

Skills are best for process discipline. They should call CLI commands and MCP
tools, but they should not be the database of record.

### Codex Plugin

Use a plugin when CoProgrammer needs distribution, team installation, bundled
skills, bundled MCP configuration, app mappings, or lifecycle hooks.

The first useful plugin should package:

- the skills above;
- an optional CoProgrammer Manager MCP server;
- marketplace metadata;
- setup instructions for the GitHub Action;
- policy defaults for safe approvals.

Plugins are the team distribution unit. Skills are the workflow authoring unit.

### MCP Server

Use MCP when agents need live access to shared state or external systems.

CoProgrammer Manager should expose:

| MCP Primitive | CoProgrammer Use |
| --- | --- |
| Tools | Request lease, release lease, create heartbeat, propose contract, record decision, create digest, create integration plan. |
| Resources | Active leases, open decisions, latest heartbeats, contract board, branch digest, integration record. |
| Prompts | Task brief review, digest review, integration plan review. |
| Elicitation | Ask a maintainer for a structured decision when a tool cannot proceed safely. |
| Notifications | Notify clients when leases, decisions, or contract board entries change. |

MCP is the agent-to-tool and agent-to-state layer. It should not replace
CoProgrammer's repository object model.

### A2A Bridge

Use A2A later when CoProgrammer must coordinate with opaque external agents
that already speak an agent-to-agent protocol.

Near-term rule:

> MCP first for tools and Manager state. A2A later for cross-vendor agent
> delegation.

A2A should not become the core source of truth. If an external agent reports a
decision, CoProgrammer should still persist it as a Manager decision record.

### GitHub Action

Use GitHub Actions for low-friction adoption:

- branch digest on PR open/synchronize;
- config and schema validation;
- artifact upload;
- stable PR comments;
- optional soft/hard policy gates.

Actions are easiest to install but weaker than a GitHub App for identity,
long-lived state, and richer checks.

### GitHub App

Use a GitHub App when the product needs richer PR lifecycle behavior:

- webhooks across repositories;
- stable bot identity;
- Checks API integration;
- issue and PR creation;
- review comments and annotations;
- installation-scoped permissions.

The GitHub App should consume Manager state and publish review artifacts. It
should not directly merge noisy agent branches.

## Full-Cycle Product Architecture

```text
Before coding
  AGENTS.md + .coprogrammer.json + task brief skill
  -> project covenant and scoped work package

During coding
  CoProgrammer Manager MCP server + CLI
  -> heartbeats, leases, contract board, decision queue

After PR
  GitHub Action/App + branch digest + policy findings
  -> preserve/drop/rebuild/defer decisions

Integration
  integration-plan skill + deterministic patch engines
  -> minimal integration branch from latest main

Feedback
  integration record + protocol update proposal
  -> better task briefs, protected paths, and validation rules
```

## Open-Source Library Map

### Protocol and Interop

| Project | Use |
| --- | --- |
| Model Context Protocol SDKs | Build the Manager MCP server in Python or TypeScript. |
| GitHub MCP Server | Reference for GitHub operations exposed through MCP. |
| Playwright MCP | Optional browser QA surface for validating web apps after integration. |
| A2A SDKs | Later bridge for cross-agent delegation, not first MVP. |

### PR Reporting and GitHub Automation

| Project | Use |
| --- | --- |
| reviewdog | Borrow diff-aware diagnostic reporting and multi-reporter design. |
| Danger JS | Borrow policy-as-code PR hygiene patterns. |
| Probot | Candidate framework for a future GitHub App. |
| SARIF / GitHub Code Scanning | Candidate output for machine-readable findings. |

### Deterministic Analysis and Patch Primitives

| Project | Use |
| --- | --- |
| tree-sitter | Parse many languages and build code structure summaries. |
| ast-grep | Structural search, rewrite, lint, and codemod rules across languages. |
| OpenRewrite | Recipe-based semantic transformations, especially Java/JVM and config ecosystems. |
| Comby | Lightweight structural search and replace for many languages. |
| Grit | Declarative code migrations and search/replace workflows. |
| jscodeshift | JavaScript/TypeScript codemods. |
| ts-morph | TypeScript AST analysis and targeted transformations. |
| Semgrep | Policy and security rules that can feed CoProgrammer findings. |

### Desired-State and Integration Patterns

| Project | Use |
| --- | --- |
| Sourcegraph Batch Changes | Borrow desired-state spec, preview, apply, and reconciliation patterns. |
| Renovate | Borrow dashboard issue and confidence metadata ideas. |
| Prow/Tide or merge queues | Delegate final merge ordering and retesting. |

## Recommended Implementation Order

### Step 1: Research Intake and Evidence

Add a normalized research lead schema extension:

- source URL;
- project category;
- lifecycle stage;
- failure modes addressed;
- CoProgrammer object mapping;
- license;
- integration decision: borrow, integrate, wrap, monitor, reject.

This makes research cumulative instead of conversational.

### Step 2: Findings Format

Define `schemas/finding.schema.json` before adding more PR bot behavior.

Finding types should include:

- protected path hit;
- missing manifest;
- lease collision;
- contract drift;
- architecture drift;
- validation mismatch;
- integration decision required.

The same finding should be renderable as terminal output, PR comment, GitHub
Check annotation, SARIF-like artifact, or Manager dashboard item.

### Step 3: Manager MCP Server

Expose the current local Manager Plane through MCP:

- `request_lease`;
- `release_lease`;
- `record_heartbeat`;
- `propose_contract_change`;
- `list_open_decisions`;
- `record_decision`;
- `get_status`.

Use the existing JSONL event log first. Move to SQLite or Postgres only after
the object model stabilizes.

### Step 4: Repo Skills

Create `.agents/skills/` workflows inside this repository for dogfooding:

- project covenant audit;
- task brief creation;
- active synchronization check;
- PR digest review;
- integration plan review.

These skills should call `python -m coprogrammer ...` commands and read the
same templates that external users will receive later.

### Step 5: Plugin Packaging

Package the skills and optional MCP server into a repo-local plugin marketplace
entry. This gives the project a realistic distribution path without requiring a
public marketplace on day one.

### Step 6: GitHub App or Action Upgrade

Keep the GitHub Action for simple adoption. Add a GitHub App only when the
product needs richer checks, installation identity, or cross-repo state.

### Step 7: Deterministic Patch Engine Adapters

Add patch primitive adapters after integration plans are real:

1. manual placeholder;
2. git apply;
3. ast-grep or Comby structural rewrite;
4. jscodeshift or ts-morph for TypeScript;
5. OpenRewrite for JVM/config migrations;
6. LLM patch only when deterministic primitives cannot express the change.

## What Not To Build First

- Do not start with a generic agent chat room.
- Do not start with A2A as the core product model.
- Do not build a merge queue.
- Do not build a generic AI PR reviewer before the digest/integration object
  model is strong.
- Do not hide live state in `AGENTS.md` or long prompt files.
- Do not let MCP tools perform destructive repository writes without explicit
  policy and approval gates.

## Source Checklist

Research entries should prefer these primary sources:

- official docs or specification;
- official GitHub repository;
- license file;
- release history;
- security model;
- examples or SDK quickstarts;
- integration examples with GitHub Actions, GitHub Apps, MCP, or CI.

Useful starting points:

- [Model Context Protocol architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP official SDKs](https://modelcontextprotocol.io/docs/sdk)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Playwright MCP](https://playwright.dev/docs/getting-started-mcp)
- [A2A protocol specification](https://github.com/a2aproject/A2A/blob/main/docs/specification.md)
- [OpenAI Codex use cases](https://developers.openai.com/codex/explore/)
- [reviewdog](https://github.com/reviewdog/reviewdog)
- [Danger JS](https://danger.systems/js/)
- [Probot](https://github.com/probot/probot)
- [Sourcegraph Batch Changes](https://sourcegraph.com/docs/batch-changes)
- [OpenRewrite](https://docs.openrewrite.org/)
- [Comby](https://comby.dev/)
- [ast-grep](https://ast-grep.github.io/)
- [tree-sitter](https://github.com/tree-sitter/tree-sitter)
- [jscodeshift](https://github.com/facebook/jscodeshift)
- [ts-morph](https://ts-morph.com/)
- [Semgrep](https://semgrep.dev/docs/)
