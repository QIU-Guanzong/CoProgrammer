# Comprehensive Research Plan

Last updated: 2026-05-25

This document turns CoProgrammer research into an executable program. The goal
is to decide whether CoProgrammer should become a software-specific Manager
Plane for coding agents, and which minimum product surface should be built
first.

## Core Thesis

The main problem is not that agents cannot talk to each other. The problem is
that agents lack a durable coordination layer.

CoProgrammer's thesis:

> Multi-agent coding needs a persistent Manager Plane that stores shared
> software state, manages leases and decisions, digests branches, and produces
> safe integration artifacts.

The 2026-05-25 research update strengthens this thesis. Current coding-agent
runtimes are moving toward background parallel work in isolated environments,
while recent empirical PR studies show that merge outcome alone hides reviewer
interventions, workflow constraints, duplicate work, and missing decision
rationale. See `docs/RESEARCH_UPDATE_2026-05-25.md`.

This places CoProgrammer between:

- general AI-labor control planes such as Paperclip;
- code review tools such as CodeRabbit, Copilot Code Review, OpenReview;
- merge and CI orchestration such as GitHub Merge Queue, Prow Tide, bors-ng;
- deterministic transformation tools such as OpenRewrite, Comby, and Grit.

## Research Questions

### RQ1: Is Manager Plane the right abstraction?

Questions:

- Do coding agents fail mainly because of stale shared state?
- Which state must be persistent: leases, contracts, decisions, digests, or all
  of them?
- Is the manager an advisor, a scheduler, a gatekeeper, or all three?
- How does the Manager Plane differ from generic AI-labor tools such as
  Paperclip?

Evidence to collect:

- failures from real multi-agent coding sessions;
- examples where agents worked on stale assumptions;
- examples where a central decision queue would have prevented rework.

### RQ2: What is the minimum useful product?

Candidate MVPs:

1. Branch Digest Bot.
2. Decision Queue for risky changes.
3. Lease Board for files/contracts.
4. Contract Board for API/schema/migration changes.
5. Integration Patch Bot.

Evaluation:

- time saved during review;
- number of conflicts avoided;
- number of noisy changes dropped;
- reviewer confidence;
- agent idle/wait time;
- integration failure rate.

### RQ3: What existing tools should be integrated instead of rebuilt?

Categories:

- merge queue;
- code review;
- deterministic codemod;
- GitHub App framework;
- PR reporting;
- agent runtime.

Decision rule:

CoProgrammer should build only what is specific to semantic integration and
agent coordination state. Everything else should be integrated.

### RQ4: What data model is stable enough?

Current candidate objects:

- manager event;
- workspace lease;
- decision record;
- agent heartbeat;
- change manifest;
- branch digest;
- integration plan;
- integration record;
- research lead.

Research should test which objects are essential and which are premature.

### RQ5: How should humans stay in control?

Questions:

- Which decisions must be human-approved?
- Which decisions can be advisory-only?
- How should the manager expose uncertainty?
- How should it avoid becoming an opaque auto-merge system?

Principle:

The Manager Plane should recommend, route, and record decisions. It should not
silently approve architecture, security, auth, payment, migration, or contract
changes.

### RQ6: How much instruction belongs in context files?

Questions:

- Which guidance belongs in `AGENTS.md`, `CLAUDE.md`, or repository
  instructions?
- Which guidance belongs in `.coprogrammer.json` or structured Manager state?
- Can minimal instructions plus structured policy outperform long natural
  language instruction files?

Principle:

Context files should describe stable working norms. Live coordination state
should live in Manager events, leases, decisions, contracts, and integration
records.

## Research Tracks

### Track A: Market and Prior Art

Goal: map direct competitors, adjacent tools, and reusable small features.

Inputs:

- `docs/OPEN_SOURCE_SCAN.md`
- `docs/FEATURE_GAP_MATRIX.md`
- `research/open-source-leads.json`
- new Research Leads discussions.

Questions:

- Does any tool already provide branch-intent digestion?
- Does any tool reconstruct minimal integration patches from latest main?
- Does any tool maintain durable software-state leases for coding agents?
- What should CoProgrammer borrow from Paperclip, Sourcegraph Batch Changes,
  OpenRewrite, Comby, Grit, reviewdog, Danger JS, Renovate, and Prow Tide?

Deliverables:

- updated feature gap matrix;
- top 10 reusable mechanisms;
- competitor positioning note;
- build-vs-integrate decision log.

### Track B: Empirical AI Coding Evidence

Goal: understand how agent-authored PRs behave in the wild.

Sources:

- empirical studies of agentic coding PRs;
- failed AI-agent PR studies;
- studies of PR descriptions and human review response;
- internal team examples.

Questions:

- Which PRs get accepted without modification?
- Which PRs fail and why?
- Are failures semantic, architectural, testing, or communication issues?
- Do reviewers need better summaries, better risk signals, or better patch
  reconstruction?

Deliverables:

- failure taxonomy;
- branch digest field validation;
- recommended reviewer workflow.

### Track C: Manager Plane Architecture

Goal: validate the persistent control-plane model.

Sources:

- Paperclip control-plane model;
- DevNous and centralized/hierarchical multi-agent project-management research;
- CAID-style centralized delegation and isolated workspaces;
- Codex, GitHub Copilot Cloud Agent, OpenHands, and SWE-agent as upstream
  coding-agent runtimes;
- older multi-agent coordination literature.

Questions:

- Should the Manager Plane be centralized, federated, or repo-local?
- How should agents check in?
- How should lease conflicts be handled?
- What state must be real-time and what can be eventually consistent?

Deliverables:

- Manager Plane object model;
- event model;
- API sketch;
- MVP dashboard wireframe;
- deployment options: local, self-hosted, cloud.

### Track D: Semantic Integration and Patch Reconstruction

Goal: decide how to rebuild useful branch ideas safely.

Sources:

- Sourcegraph Batch Changes;
- OpenRewrite;
- Comby;
- Grit;
- SemanticMerge;
- GitWand.

Questions:

- When should deterministic codemods be used before LLM patch generation?
- Can integration plans be represented as a desired-state spec?
- How should failed patch attempts be recorded?
- How should validation feedback loop back into the integration plan?

Deliverables:

- integration patch architecture;
- deterministic patch primitive shortlist;
- integration record workflow;
- rollback and validation requirements.

### Track E: Product and Workflow UX

Goal: design a workflow that real teams can use.

User roles:

- maintainer/advisor;
- coding agent;
- reviewer;
- integration agent;
- team lead/engineering manager.

Questions:

- Should users interact through GitHub comments, dashboard, CLI, or all three?
- What is the first "daily habit" surface?
- How should Chinese/English teams use the same workflow?
- Which moments need interruptive approval and which only need passive signal?

Deliverables:

- workflow storyboard;
- reviewer screen spec;
- decision queue spec;
- GitHub command set;
- bilingual terminology glossary.

### Track F: Safety, Governance, and Trust

Goal: keep the system conservative.

Questions:

- How can the Manager Plane avoid becoming an unsafe auto-merge agent?
- How should provenance be preserved?
- Which actions require explicit human identity?
- How should budget, rate, and permission limits apply to agents?
- How should secrets and private code be handled?

Deliverables:

- trust model;
- permission matrix;
- audit log requirements;
- high-risk action policy;
- human override procedure.

## Six-Week Research Sprint

### Week 1: Prior Art Baseline

Tasks:

- verify top 20 open-source and commercial adjacent tools;
- update `research/open-source-leads.json`;
- classify each project by direct competitor, adjacent capability, reusable
  component, or research reference;
- open Research Leads discussions for uncertain items.

Exit criteria:

- feature gap matrix covers at least 20 references;
- each high-signal reference has a clear "borrow/integrate/avoid/watch"
  decision.

### Week 2: Empirical Failure Taxonomy

Tasks:

- collect examples of failed or noisy AI-agent PRs;
- classify failures by stale state, contract drift, architecture drift, noisy
  refactor, bad test signal, or unclear intent;
- compare taxonomy against current branch digest fields.

Exit criteria:

- branch digest template updated with missing fields;
- failure taxonomy added to docs.

### Week 3: Manager Plane Object Model

Tasks:

- review `manager-event`, `workspace-lease`, and `decision-record` schemas;
- draft API endpoints;
- define state transitions for lease and decision records;
- sketch event log persistence.

Exit criteria:

- object model approved for MVP spike;
- at least one example event log exists.

### Week 4: Prototype Experiment

Tasks:

- implement a local event-log prototype or CLI subcommands;
- simulate two agents editing overlapping paths;
- produce lease conflict and decision queue output;
- connect digest findings to decision records.

Exit criteria:

- prototype demonstrates one stale-state prevention scenario;
- evidence recorded in an integration-style report.

### Week 5: Integration Patch Design

Tasks:

- evaluate deterministic patch primitives;
- draft integration plan to patch workflow;
- decide whether to use branch artifacts, local worktrees, or GitHub branches
  for first implementation.

Exit criteria:

- Integration Patch Bot design has a clear first slice;
- non-goals and safety constraints are explicit.

### Week 6: Product Positioning and MVP Cut

Tasks:

- decide MVP scope;
- produce product narrative;
- write technical RFC;
- convert research findings into issues.

Exit criteria:

- one-page product thesis;
- MVP implementation roadmap;
- prioritized issue backlog.

## Current Roadmap Adjustment

After the 2026-05-25 research update, the next MVP should be framed as two
connected surfaces:

1. Branch Digest Bot: PR diff ingestion, branch intent, risk extraction,
   protected-path signals, and reviewer-facing integration plans.
2. Manager Event Log: heartbeats, workspace leases, decision queue, status
   reconstruction, then contract board and integration records.

Integration Patch Bot remains the desired differentiator, but it should come
after Manager Plane state is reliable enough to explain why a patch is being
rebuilt.

## Evaluation Rubric

Each candidate feature should be scored 1-5:

| Criterion | Meaning |
| --- | --- |
| User pain | How painful is the current failure mode? |
| Frequency | How often does the failure occur in multi-agent coding? |
| Differentiation | Is this specific to CoProgrammer's semantic integration thesis? |
| Feasibility | Can we build a useful version in 1-2 weeks? |
| Integrability | Can it work with GitHub/CI/existing agents without replacing them? |
| Trust | Does it keep humans in control? |

Prioritize features with high pain, high differentiation, medium/high
feasibility, and strong trust properties.

## Evidence Standards

A research note is strong only if it includes:

- source links;
- observed capability;
- what to borrow;
- what gap remains;
- whether it changes architecture;
- whether it changes roadmap priority.

Avoid adding tool names without a concrete implication.

## Sources to Maintain

Core sources:

- [Paperclip](https://paperclip.ing/)
- [Paperclip Docs](https://docs.paperclip.ing/)
- [paperclipai/paperclip](https://github.com/paperclipai/paperclip)
- [OpenAI Codex](https://openai.com/index/introducing-codex/)
- [GitHub Copilot Cloud Agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
- [OpenHands](https://github.com/OpenHands/OpenHands)
- [SWE-agent](https://arxiv.org/abs/2405.15793)
- [AGENTS.md](https://github.com/agentsmd/agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)
- [Agent2Agent Protocol](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [GitHub Merge Queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Copilot Code Review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [GitLab Merge Trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [Prow Tide](https://docs.prow.k8s.io/docs/components/core/tide/)
- [reviewdog](https://github.com/reviewdog/reviewdog)
- [Danger JS](https://github.com/danger/danger-js)
- [Renovate](https://github.com/renovatebot/renovate)
- [Sourcegraph Batch Changes](https://sourcegraph.com/docs/batch_changes)
- [OpenRewrite](https://docs.openrewrite.org/)
- [Comby](https://comby.dev/)
- [Grit](https://docs.grit.io/)
- [arXiv: On the Use of Agentic Coding](https://arxiv.org/abs/2509.14745)
- [arXiv: Failed Agentic Pull Requests](https://arxiv.org/abs/2601.15195)
- [arXiv: Agentic PR Merge/Rejection Study](https://arxiv.org/abs/2605.22534)
- [arXiv: Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)
- [arXiv: AI Coding Agents Communicate](https://arxiv.org/abs/2602.17084)
- [Effective Strategies for Asynchronous Software Engineering Agents](https://huggingface.co/papers/2603.21489)

## Immediate Next Steps

1. Review the expanded structured leads and keep the list above 20 entries.
2. Review `docs/MANAGER_API_SKETCH.md`.
3. Review `docs/EVENT_LOG_PROTOTYPE.md`.
4. Convert the event-log prototype into an implementation issue.
5. Open Research Leads discussions after GitHub Discussions are enabled.
