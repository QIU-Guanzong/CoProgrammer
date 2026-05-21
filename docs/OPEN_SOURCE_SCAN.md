# Open Source Scan

Last updated: 2026-05-21

This page tracks adjacent open-source projects and small reusable features that
may influence CoProgrammer.

The goal is not to prove that no similar tool exists. The goal is to keep a
living map of prior art, reusable pieces, and differentiation.

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
