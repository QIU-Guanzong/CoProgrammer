# Manager Plane

CoProgrammer should not depend on agents talking directly to each other.

The more reliable architecture is a persistent Manager Plane: a cloud or
self-hosted control plane that stores shared state, receives agent telemetry,
coordinates leases and decisions, and turns agent output into reviewable
integration artifacts.

## Why This Exists

Multi-agent development fails when agents share unstable context directly.

Agents are:

- too fast: they can rewrite many files before the team has evaluated the idea;
- too slow: shared context, review, and contract decisions lag behind their
  local work;
- too local: each agent sees a partial world and can continue from stale state.

The Manager Plane creates a single durable source of coordination truth.

## Paperclip Reference

Paperclip is the strongest current reference for this direction. It describes
itself as a human control plane for AI labor and a control plane for AI-run
companies. Its model includes org charts, goals, tasks, budgets, approvals,
heartbeats, governance, and bringing your own agent runtime.

The important lesson is not that CoProgrammer should become Paperclip. The
lesson is:

> Agents should report into a persistent organization layer instead of
> coordinating only through ad hoc conversations.

CoProgrammer applies that idea to software integration rather than general
company operations.

## Scope Difference

| Area | Paperclip | CoProgrammer Manager Plane |
| --- | --- | --- |
| Primary domain | AI-run companies and AI labor | Multi-agent software development and semantic integration |
| Main object | Company, goal, team, issue, budget | Repo, branch, contract, lease, digest, integration record |
| Human role | CEO/operator approving risky work | Maintainer/advisor approving architecture and integration decisions |
| Output | Business tasks performed by agents | Minimal safe patches and integration PRs |
| Governance | Budgets, org chart, approvals, accountability | Main constitution, protected paths, owner review, decision records |
| Agent runtime | Bring your own agent | Bring your own coding agent |

## Core Responsibilities

### 1. Shared State Store

The Manager Plane stores:

- repositories;
- projects;
- active branches;
- agent sessions;
- task briefs;
- heartbeats;
- workspace leases;
- contract board entries;
- branch digests;
- integration plans;
- decision records;
- integration records.

### 2. Lease Board

Agents should not freely edit every file. They request or receive leases:

- path lease;
- contract lease;
- test surface lease;
- integration branch lease.

A lease does not replace Git. It creates an early coordination signal before
conflicts become expensive.

### 3. Contract Board

Shared contracts should be first-class:

- API;
- schema;
- database migration;
- shared type;
- auth/payment behavior;
- deployment behavior;
- global configuration.

Agents publish intended contract changes before they land.

### 4. Decision Queue

The Manager Plane should route decisions to humans when:

- protected paths are touched;
- contract compatibility is uncertain;
- a branch has high risk;
- two agents propose conflicting architecture;
- a patch rewrites shared invariants;
- tests pass but product intent is unclear.

### 5. Branch Intelligence

The Manager Plane coordinates:

- branch digest generation;
- manifest collection;
- risk scoring;
- contract impact analysis;
- integration plan drafting.

### 6. Semantic Integration

The Manager Plane should prefer:

1. digest source branch;
2. ask for human decision on risky items;
3. create integration branch from latest main;
4. rebuild minimal safe patch;
5. validate;
6. write integration record;
7. hand off to merge queue.

## Event Model

The Manager Plane should be event-driven.

Candidate events:

- `agent.heartbeat`
- `agent.blocked`
- `lease.requested`
- `lease.granted`
- `lease.released`
- `contract.change.proposed`
- `branch.digest.created`
- `decision.requested`
- `decision.recorded`
- `integration.plan.created`
- `integration.recorded`

These events can later back a dashboard, audit log, or replayable project
timeline.

## Minimal MVP

The smallest Manager Plane MVP is not a full SaaS product.

It can start as:

- a JSON event log;
- a SQLite/Postgres state store;
- a small API;
- a dashboard showing active agents, leases, decisions, and digests;
- GitHub Action integration for PR digest artifacts.

The first feature should be a **decision queue** for risky branch digest
findings, because this directly addresses the "too fast and too slow" failure
mode.

The first local CLI prototype now focuses on the smaller slice before that:
workspace leases, decision requests for overlapping work, recorded decision
outcomes, and a reconstructed status snapshot.

## Initial Schemas

The first state objects are intentionally small:

- `schemas/manager-event.schema.json`
- `schemas/workspace-lease.schema.json`
- `schemas/decision-record.schema.json`

These can back a local JSON event log first, then later move into SQLite,
Postgres, or a hosted service.

## Implementation Sketches

- `docs/MANAGER_API_SKETCH.md`
- `docs/EVENT_LOG_PROTOTYPE.md`

## Non-Goals

- Do not become a generic chat room for agents.
- Do not auto-approve architecture decisions.
- Do not replace GitHub, GitLab, CI, or merge queues.
- Do not require every team to adopt one agent runtime.
- Do not copy Paperclip's company metaphor wholesale; keep the software
  integration domain clear.

## Product Hypothesis

CoProgrammer is an OpenClaw-like control plane for coding agents, but narrower:

> Paperclip manages AI labor as a company. CoProgrammer Manager manages AI
> coding work as an integration system.

This framing should guide the next roadmap: build the durable Manager Plane
around software state, not an agent chat surface.
