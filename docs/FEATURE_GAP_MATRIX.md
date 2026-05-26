# Feature Gap Matrix

Last updated: 2026-05-25

This matrix turns open-source research into product decisions. A project can be
valuable even when it is not a direct competitor.

Legend:

- `native`: the project directly owns this capability;
- `partial`: the project has a related mechanism;
- `none`: not a meaningful part of the project;
- `candidate`: promising but needs more verification.

## Capability Comparison

| Capability | CoProgrammer Target | Existing References | Status |
| --- | --- | --- | --- |
| Machine-readable team policy | `.coprogrammer.json` controls language, risk, protected paths, and future gates. | Danger JS policy scripts, Renovate config, Prow/Tide config. | Implemented foundation |
| PR diagnostic reporting | Branch digest findings should later emit comments, checks, and artifacts. | reviewdog reporters, GitHub Checks, Danger comments. | Partial |
| AI PR review | CoProgrammer should consume review signals but not become a generic reviewer first. | OpenReview, CodeRabbit, GitHub Copilot Code Review. | Integrate, not replace |
| Merge queue | CoProgrammer should feed smaller integration PRs into existing queues. | GitHub Merge Queue, GitLab Merge Trains, Prow Tide, bors-ng. | Delegate |
| Integration branch | Rebuild minimal patch from latest main after digest approval. | bors staging branches, MergePilot integration branches, Sourcegraph Batch Changes changesets. | Planned |
| Branch-intent digest | Extract intent, core contribution, noise, risk, and human decisions. | PR summaries are partial references. | Core differentiator |
| Semantic patch reconstruction | Regenerate useful branch ideas under main constraints. | OpenRewrite, Comby, Grit, Sourcegraph Batch Changes. | Planned |
| Development telemetry | Heartbeats, contract board, conflict forecast. | Agent status logs, issue dashboards, CI dashboards. | Planned |
| Integration record | Preserve why insights were kept or dropped. | Sourcegraph batch specs and changeset tracking, Renovate dashboard issues. | Schema/template |
| Discussion-backed research loop | Keep exploratory leads out of implementation PRs. | GitHub Discussions, issue forms. | Implemented foundation |
| Persistent manager plane | Store shared state for agents, leases, decisions, branch digests, and integration records. | Paperclip control plane, Prow status, Renovate dashboard. | Architecture hypothesis |
| Agent runtime | CoProgrammer should consume outputs from coding agents rather than become the runtime. | Codex, GitHub Copilot Cloud Agent, OpenHands, SWE-agent. | Integrate, not replace |
| Repository agent instructions | Keep stable agent guidance minimal and portable. | AGENTS.md, Codex AGENTS.md support, tool-specific context files. | Borrow, but keep live state structured |
| Agent interoperability | Manager Plane may expose state through standard protocols. | MCP, Agent2Agent. | Future access layer |
| Manager event log | Reconstruct leases, decisions, heartbeats, and status from append-only events. | Paperclip heartbeats, CAID structured integration, event sourcing patterns. | Local CLI prototype |
| Model routing | Route simple work to cheaper models and high-risk work to stronger review. | LiteLLM, Continue checks, repository policy configs. | Config foundation |
| Deterministic patch primitives | Prefer structured transforms before LLM patch generation. | ast-grep, tree-sitter, Semgrep, jscodeshift, ts-morph. | Planned |

## Project-by-Project Fit

| Project | Policy | PR Reporting | Queue | Code Transform | Intent Digest | Integration Record | CoProgrammer Takeaway |
| --- | --- | --- | --- | --- | --- | --- | --- |
| reviewdog | none | native | none | none | none | none | Borrow diagnostic/reporting shape. |
| Danger JS | native | native | none | none | partial | none | Borrow policy-as-code and PR messaging. |
| Renovate | native | native | partial | partial | partial | partial | Borrow dashboard and confidence metadata ideas. |
| Prow/Tide | native | partial | native | none | none | partial | Borrow merge pool and status visibility ideas. |
| bors-ng | partial | partial | native | none | none | partial | Borrow staging branch principle. |
| Sourcegraph Batch Changes | native | partial | none | native | partial | native | Borrow spec/reconciliation and changeset tracking. |
| OpenRewrite | native | none | none | native | none | none | Borrow recipe-based semantic transformation model. |
| Comby | partial | none | none | native | none | none | Borrow structural search/replace as deterministic patch primitive. |
| Grit | native | partial | none | native | partial | partial | Borrow declarative transformation language and PR generation flow. |
| OpenReview | partial | native | none | none | partial | none | Borrow self-hosted GitHub App deployment pattern. |
| GitWand | none | none | none | partial | none | partial | Borrow conflict confidence taxonomy. |
| MergePilot | partial | partial | partial | partial | partial | partial | Track closely as direct competitor candidate. |
| Pullfrog | partial | partial | none | partial | partial | none | Borrow mention-triggered agent task UX. |
| Paperclip | native | partial | none | none | partial | partial | Borrow persistent manager/control-plane model, but specialize it for software integration. |
| OpenAI Codex | partial | partial | none | partial | partial | partial | Treat as upstream branch/task producer. |
| GitHub Copilot Cloud Agent | partial | partial | none | partial | partial | partial | Consume GitHub-native agent branches and session logs. |
| OpenHands | partial | partial | none | partial | partial | partial | Consider runtime interoperability, especially for self-hosted teams. |
| SWE-agent | none | none | none | partial | none | none | Borrow agent-computer-interface thinking. |
| AGENTS.md | native | none | none | none | partial | none | Use minimal stable instructions; do not store live coordination state here. |
| MCP | none | none | none | none | none | none | Future protocol surface for Manager tools/resources. |
| Agent2Agent | none | none | none | none | none | none | Future interop bridge, not a semantic integration model. |

## Research Decisions

1. CoProgrammer should not build its own merge queue.
2. CoProgrammer should not start as a generic AI code reviewer.
3. CoProgrammer should define a digest finding format before adding more PR
   comment features.
4. CoProgrammer should treat OpenRewrite/Comby/Grit as future patch primitives,
   not as competitors.
5. CoProgrammer should borrow Sourcegraph Batch Changes' "spec and
   reconciliation" idea for Integration Patch Bot design.
6. CoProgrammer should use Discussions to keep research leads alive until they
   become executable tasks.
7. Paperclip validates the Manager Plane direction, but CoProgrammer should
   narrow the domain to repository state and semantic integration rather than
   broad AI-company operations.
8. Research should be evaluated against `docs/FAILURE_TAXONOMY.md`; if a tool
   does not address a target failure mode, it should not drive roadmap priority.
9. Codex, Copilot Cloud Agent, OpenHands, and SWE-agent should be treated as
   upstream runtimes. CoProgrammer should coordinate their outputs rather than
   duplicate them.
10. `AGENTS.md` should remain minimal. Structured policy and live coordination
    state belong in `.coprogrammer.json` and the Manager event log.
11. MCP and Agent2Agent are future access/interoperability layers, not the core
    semantic integration object model.
12. High-star coding agents are upstream runtimes. CoProgrammer should consume
    their outputs, not duplicate their coding-agent UX.
13. Simple work may route to `codex-5.3`, but protected paths, contracts, and
    integration patch application require stronger review.

## Next Research Questions

- Can branch digest findings be represented as SARIF or should CoProgrammer
  define its own format first?
- Which deterministic patch engines should be supported before LLM-generated
  patch reconstruction?
- Should integration records be stored as repository files, PR comments, or
  release-like artifacts?
- What minimal GitHub App is needed beyond GitHub Actions?
- How should agent heartbeats be stored without creating noisy repository churn?
- Which Manager Plane objects are essential for an MVP: leases, decisions,
  contract board, digest queue, or all four?
- Which failure modes are most frequent in real team usage?
- Can a minimal `AGENTS.md` plus `.coprogrammer.json` outperform a long
  instruction-heavy context file?
- Which coding-agent runtime should be the first Manager Plane integration:
  Codex, Copilot Cloud Agent, OpenHands, or local CLI agents?
