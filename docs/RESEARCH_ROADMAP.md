# Research Roadmap

## Research Question

How can a team coordinate many humans and AI agents so that parallel branches
preserve useful insight, reduce merge risk, and keep main branch architecture
stable?

## Phase 0: Protocol First

Goal: change team behavior before building a complex platform.

Deliverables:

- `protocols/main-branch-constitution.md`
- `protocols/agent-workspace-contract.md`
- task brief template
- change manifest template
- branch digest template
- PR checklist
- CODEOWNERS

Validation:

- one real PR includes a branch digest;
- reviewers can identify core contribution without reading the entire diff.
- protected-path risk is visible in the digest;
- project policy can be validated locally and in CI.

## Phase 1: Branch Digest Bot

Goal: convert large AI branches into reviewable integration plans.

Inputs:

- PR diff;
- commit history;
- main branch constitution;
- protected file list;
- CI result;
- optional agent heartbeats.

Outputs:

- branch intent;
- core contribution;
- noise and unrelated changes;
- contract impact;
- architecture risk;
- protected path matches;
- integration plan;
- human decision list.

Current implemented foundation:

- local `coprogrammer digest`;
- PR digest GitHub Action;
- bilingual digest output;
- `.coprogrammer.json` policy config;
- protected-path risk scoring.

## Phase 2: Integration Patch Bot

Goal: rebuild useful changes from latest `main` instead of directly merging
noisy branches.

Workflow:

1. read branch digest;
2. checkout latest main;
3. create integration branch;
4. implement minimal patch;
5. run validation;
6. open integration PR with traceability to source branch.

Required before implementation:

- explicit human approval step;
- validation command registry;
- rollback plan format.

## Phase 3: Multi-Agent Orchestrator

Goal: prevent conflicts during development, not only at merge time.

Capabilities:

- task decomposition;
- path ownership assignment;
- heartbeat ingestion;
- shared contract board;
- conflict forecast;
- agent handoff records.

## Phase 4: Semantic Integration Platform

Goal: turn the protocol and tools into a product-quality collaboration system.

Capabilities:

- dashboard;
- branch graph;
- semantic diff;
- integration history;
- rollback suggestions;
- team policy learning.
