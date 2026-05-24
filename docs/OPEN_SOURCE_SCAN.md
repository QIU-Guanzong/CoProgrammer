# Open Source Scan

Last updated: 2026-05-25

This page tracks adjacent open-source projects and small reusable features that
may influence CoProgrammer.

The goal is not to prove that no similar tool exists. The goal is to keep a
living map of prior art, reusable pieces, and differentiation.

For a feature-by-feature product comparison, see
`docs/FEATURE_GAP_MATRIX.md`.

## Classification

| Category | Meaning |
| --- | --- |
| Direct competitor | Attempts to solve a similar end-to-end workflow. |
| Adjacent capability | Solves one important nearby problem. |
| Reusable component | Has a pattern, API, format, or implementation detail worth borrowing. |
| Research reference | Useful evidence, dataset, or concept, but not directly reusable. |

## High-Signal Projects

| Project | Category | What It Does | Useful Ideas | Gap vs. CoProgrammer |
| --- | --- | --- | --- | --- |
| [reviewdog](https://github.com/reviewdog/reviewdog) | Reusable component | Converts linter/static-analysis output into PR comments, checks, annotations, and suggestions. | Generic diagnostic format, diff-aware reporting, multiple reporters, local + CI modes. | Does not reason about branch intent, semantic integration, or AI-generated noise. |
| [Danger JS](https://github.com/danger/danger-js) | Reusable component | Runs project-specific PR rules and posts messages inside PRs. | Policy-as-code, PR hygiene automation, custom team rules. | Focuses on PR checks and reminders, not digesting branch contribution. |
| [bors-ng](https://github.com/bors-ng/bors-ng) | Adjacent capability | Historical merge bot that staged and tested approved PRs before landing. | Staging branch queue pattern, evergreen main principle. | Deprecated for new feature work; merge queue handles order, not semantic branch digestion. |
| [OpenReview](https://github.com/vercel-labs/openreview) | Adjacent capability | Open-source, self-hosted AI PR review bot powered by Claude and a GitHub App. | Self-hostable GitHub App model, mention-triggered review, Vercel deployment path. | Reviews submitted PRs; does not rebuild minimal integration patches. |
| [GitWand](https://gitwand.devlint.fr/) | Adjacent capability | Native Git client with deterministic conflict classification and confidence scoring. | Conflict pattern taxonomy, per-hunk confidence, local-first merge assistance, MCP surface for agents. | Resolves merge conflicts after they exist; does not capture branch intent or integration records. |
| [MergePilot](https://mergepilot-ai.com/) | Direct competitor candidate | GitHub App for merging multiple PRs, AI conflict resolution, validation, and integration branches. | Slash-command workflow, integration branch creation, multi-PR merge flow. | Appears conflict-resolution oriented; CoProgrammer should emphasize protocol, branch digestion, and preserving insights under main constraints. |
| [Pullfrog](https://pullfrog.com/) | Adjacent capability | GitHub bot that runs AI agents for PR review, issue triage, CI fixes, plans, and merge conflict fixes. | Mention-triggered agent tasks, GitHub Actions execution, configurable repo instructions. | General agent execution layer; CoProgrammer should provide specific semantic integration protocol and artifacts. |
| [CodeRabbit](https://docs.coderabbit.ai/guides/code-review-overview) | Adjacent capability | AI code review across PRs with summaries and comments. | Review summaries, continuous PR comments, reviewer UX. | Closed/commercial; reviews PRs as submitted rather than regenerating minimal patches. |
| [GitHub Copilot Code Review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review) | Adjacent capability | GitHub-native Copilot-assisted PR review. | Native review UX and GitHub integration model. | Not an open-source component; does not own protocol or integration records. |
| [Paperclip](https://paperclip.ing/) | Direct competitor candidate | Open-source control plane for AI labor and AI-run companies with org charts, goals, tasks, budgets, approvals, heartbeats, and bring-your-own agents. | Persistent manager/control-plane metaphor, BYO agent model, heartbeats, budgets, governance, dashboard. | Broad company operations layer; CoProgrammer should specialize in repo state, branch digestion, semantic integration, and integration records. |
| [Probot](https://github.com/probot/probot) | Reusable component | Framework for building GitHub Apps in Node.js/TypeScript. | Webhook app model, event routing, GitHub-native automation pattern. | App framework only; CoProgrammer still owns protocol and digest semantics. |
| [Renovate](https://github.com/renovatebot/renovate) | Adjacent capability | Open-source dependency update automation that opens and tracks update PRs. | Highly configurable policy, generated PR bodies, dependency dashboard, confidence metadata. | Domain-specific for dependencies; does not perform semantic branch integration. |
| [Prow Tide](https://docs.prow.k8s.io/docs/components/core/tide/) | Adjacent capability | Kubernetes Prow component that manages PR pools, retests PRs, and merges when criteria pass. | Merge pool status, retest-before-merge principle, dashboard-friendly state. | Merge automation only; no branch-intent digest. |
| [Sourcegraph Batch Changes](https://sourcegraph.com/docs/batch_changes) | Adjacent capability | Spec-driven large-scale code changes with changeset tracking across repositories. | Desired-state spec, changeset reconciliation, progress tracking. | Optimizes planned large-scale changes, not noisy multi-agent branch digestion. |
| [OpenRewrite](https://docs.openrewrite.org/) | Reusable component | Open-source automated refactoring ecosystem using recipes and semantic trees. | Recipe-based deterministic transformations, semantic patch primitives. | Transformation engine only; no collaboration protocol or branch review layer. |
| [Comby](https://comby.dev/) | Reusable component | Structural search and replace across many languages. | Syntax-aware transformation templates that avoid many regex pitfalls. | Patch primitive only. |
| [Grit](https://docs.grit.io/) | Reusable component | Declarative code search and transformation via GritQL and migration workflows. | Declarative transformations, AI-assisted migration surface, PR-generation flow. | Transformation layer; not an integration governance system. |

## 2026-05-25 Additions

| Project | Category | What It Does | Useful Ideas | Gap vs. CoProgrammer |
| --- | --- | --- | --- | --- |
| [OpenAI Codex](https://openai.com/index/introducing-codex/) | Adjacent capability | Cloud coding agent that can run many tasks in parallel in isolated repository sandboxes and propose changes for review. | Parallel task model, sandbox evidence, AGENTS.md-guided execution, terminal/test citations. | Agent runtime; does not provide cross-agent leases, contract board, or semantic integration records. |
| [GitHub Copilot Cloud Agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent) | Adjacent capability | GitHub-native cloud agent that researches, plans, creates branches, and can open PRs from GitHub workflows. | GitHub task assignment, session logs, branch automation, custom agents. | Produces branches/PRs; does not digest multiple branches into minimal patches under project policy. |
| [OpenHands](https://github.com/OpenHands/OpenHands) | Adjacent capability | Open-source AI-driven development platform and SDK for autonomous coding agents. | Sandboxed execution, model-agnostic runtime, SDK and evaluation infrastructure. | Runtime layer; CoProgrammer should coordinate outputs rather than replace the runtime. |
| [SWE-agent](https://arxiv.org/abs/2405.15793) | Research reference | Agent-computer interface for automated software engineering tasks. | Purpose-built ACI, repo navigation, edit/test affordances. | Single-agent interface; CoProgrammer needs team-level integration state. |
| [AGENTS.md](https://github.com/agentsmd/agents.md) | Reusable component | Open format for repository-level coding-agent instructions. | Stable build/test/PR guidance for agents. | Static instructions only; live state must remain in Manager events and structured policy. |
| [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture) | Reusable component | Protocol for exposing tools, resources, prompts, notifications, and context to AI applications. | Future Manager Plane MCP server, tool/resource model, elicitation for human decisions. | Transport/context layer; not a software integration model. |
| [Agent2Agent](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents) | Reusable component | Open protocol project for secure agent-to-agent interoperability. | Future bridge across heterogeneous agent runtimes. | Agent communication layer; not repository lease, digest, or integration semantics. |
| [CAID research](https://huggingface.co/papers/2603.21489) | Research reference | Centralized Asynchronous Isolated Delegation for multi-agent software engineering. | Central manager, async isolated workspaces, structured integration, test verification. | Research paradigm; CoProgrammer can productize it as event logs, leases, decisions, and integration records. |

## Small Features Worth Borrowing

### 1. Diagnostic Format for Digest Findings

Source inspiration: reviewdog.

CoProgrammer should define a machine-readable finding format for:

- protected path hit;
- contract change;
- architecture risk;
- missing manifest;
- large diff warning;
- integration decision needed.

This would allow multiple reporters later:

- PR comment;
- GitHub check;
- SARIF-like artifact;
- local terminal output;
- future dashboard.

### 2. Policy-as-Code Rules

Source inspiration: Danger JS.

CoProgrammer already has `.coprogrammer.json`. A later step could add a
scriptable policy hook, but the first version should stay JSON-only to avoid
turning policy into arbitrary CI code too early.

Candidate future rule examples:

- fail if high-risk protected paths lack a change manifest;
- warn if one branch modifies more than N modules;
- require integration plan for schema and migration changes;
- require human decision notes for auth, payment, or security behavior.

### 3. Conflict Confidence Taxonomy

Source inspiration: GitWand.

CoProgrammer should avoid treating every conflict equally. A future integration
agent can classify integration risk:

- text-only conflict;
- same symbol modified;
- public contract drift;
- shared invariant drift;
- test-only conflict;
- generated artifact conflict.

Only low-confidence or contract-level conflicts should block the integration
agent and force human decision.

### 4. Mention-Triggered Agent Runs

Source inspiration: OpenReview, Pullfrog, MergePilot.

Possible commands:

```text
@coprogrammer digest
@coprogrammer plan integration
@coprogrammer create integration-pr
@coprogrammer record decision
```

The bot should not merge or approve by default. It should produce artifacts and
wait for explicit maintainer approval.

### 5. Staging Branch / Integration Branch Pattern

Source inspiration: bors-ng and MergePilot.

CoProgrammer's integration branch should be created from latest main, not from
the source feature branch. The branch digest and integration plan become the
inputs to reconstruct the patch.

### 6. Spec and Reconciliation Loop

Source inspiration: Sourcegraph Batch Changes.

CoProgrammer's future Integration Patch Bot should separate:

- desired semantic outcome;
- generated patch attempt;
- validation result;
- review outcome;
- final integration record.

This is closer to a reconciliation loop than a one-shot merge.

### 7. Recipe-Based Patch Primitives

Source inspiration: OpenRewrite, Comby, and Grit.

LLMs should not be the only way to rebuild patches. A mature CoProgrammer
integration agent can mix:

- deterministic codemods;
- structural search/replace;
- language-aware transformations;
- LLM reasoning for intent and edge cases.

### 8. Dashboard Issue / Research Inbox

Source inspiration: Renovate dependency dashboard and GitHub Discussions.

CoProgrammer should maintain a visible queue of research leads, high-risk
integration decisions, and pending protocol updates. Discussions are the open
research surface; issues are the executable task surface.

### 9. Persistent Manager Plane

Source inspiration: Paperclip.

Paperclip's strongest idea is not "agents talk to agents." It is that agents
report into a persistent control plane with goals, tasks, approvals,
heartbeats, budgets, and governance. CoProgrammer should adopt this control
plane pattern but narrow it to software integration:

- repositories instead of companies;
- branch digests instead of business tasks;
- leases and contract boards instead of generic org-chart delegation;
- integration records instead of general accountability logs.

### 10. Minimal Agent Instructions

Source inspiration: AGENTS.md and 2026 context-file studies.

CoProgrammer should treat static instruction files as a stable onboarding layer,
not as a live coordination database. A good repository setup should separate:

- stable agent guidance in `AGENTS.md`;
- machine-readable policy in `.coprogrammer.json`;
- live work state in Manager events;
- reviewable integration rationale in branch digests and decision records.

This prevents the "one giant prompt file" failure mode while staying compatible
with existing agent runtimes.

## Projects to Verify Later

These appeared in current research but need deeper source/license verification
before they should influence architecture:

- GitSynth
- reconcile-ai
- Airlock
- Phantom
- ruah
- dmux
- Clash
- Converge AI
- CodeCanary
- CodeLux
- Gito
- ShipItAI
- Robin AI Reviewer

## Differentiation Checklist

CoProgrammer should remain distinct by requiring:

- branch intent before integration;
- explicit separation of insight vs. noise;
- main-branch constitution and project policy;
- protected-path risk scoring;
- integration record history;
- minimal patch reconstruction from latest main;
- human approval for architecture/security/contract decisions.

If another tool provides one of these directly, add it to this document and
open a Research Lead discussion.
