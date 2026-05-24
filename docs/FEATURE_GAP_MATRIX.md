# Feature Gap Matrix

Last updated: 2026-05-21

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
