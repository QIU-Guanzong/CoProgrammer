# Research Landscape

Last updated: 2026-05-21

CoProgrammer sits between existing code review tools and merge automation. The
current ecosystem can review, queue, test, and structurally merge code, but it
does not yet provide a complete branch-intent digestion and semantic
reintegration layer.

For a living list of open-source adjacent projects and reusable small features,
see `docs/OPEN_SOURCE_SCAN.md`.

## Key Finding

The market already has strong tools for:

- path ownership and protected review;
- AI-assisted pull request review;
- merge queues and merge trains;
- structural or syntax-aware merge help.

The gap is the layer that asks:

> What did this branch learn, which parts are worth preserving, and how should
> those ideas be rebuilt as the smallest safe patch on top of current main?

That is CoProgrammer's target layer.

## Capability Map

| Area | Existing Capability | Remaining Gap for CoProgrammer |
| --- | --- | --- |
| Path ownership | GitHub CODEOWNERS maps files to owners and can require owner approval. GitHub also recommends protecting the CODEOWNERS file or `.github/` itself. | Convert ownership into machine-readable policy, digest risk, and integration rules instead of only review assignment. |
| Merge ordering | GitHub Merge Queue validates queued PRs against the latest target branch and earlier queued PRs before merging. | Queue systems validate the final commit state, but they do not decide which insights from noisy AI branches should survive. |
| Merge trains | GitLab Merge Trains provide queue order, pipeline status, and merge request train visibility. | They coordinate merge order and pipelines, not branch-intent extraction or semantic patch rebuilding. |
| Third-party queues | Mergify and Graphite provide queue setup, batching, parallel CI, and merge optimization. | These are useful downstream gates; CoProgrammer should feed them smaller, safer integration PRs. |
| AI PR review | GitHub Copilot Code Review and CodeRabbit can review PRs and produce comments or summaries. | Review tools inspect the PR as submitted. They generally do not discard noisy edits and regenerate a minimal patch from main constraints. |
| Structural merge | SemanticMerge uses language-dependent parsing to handle some refactors, imports, moved methods, and changed/deleted cases. | Structural merge is still code-shape oriented. CoProgrammer focuses on feature intent, experiments, and integration decisions. |
| AI-agent empirical studies | Recent studies analyze how AI coding agents create PRs and how their PR descriptions affect human review. | These findings support making branch intent, manifests, and reviewer-facing summaries first-class artifacts. |

## Architecture Implications

1. CoProgrammer should integrate with CODEOWNERS, branch protection, and merge
   queues instead of replacing them.
2. The first durable product surface is a Branch Digest Bot, because it turns
   large AI PRs into reviewable decision artifacts.
3. The second surface is an Integration Patch Bot, but it must remain
   human-approved and validation-gated.
4. Collaboration telemetry should be captured during development, not invented
   after the PR is already large.
5. Project policy must be machine-readable, versioned, and reviewed like code.

## Build vs. Integrate

Build inside CoProgrammer:

- branch digest format;
- project policy config;
- protected-path risk scoring;
- change manifest validation;
- agent heartbeat ingestion;
- integration plan generation;
- integration record history;
- future minimal-patch regeneration.

Integrate with existing tools:

- GitHub/GitLab PRs and merge requests;
- CODEOWNERS;
- branch protection;
- GitHub Merge Queue or GitLab Merge Trains;
- Mergify or Graphite where teams already use them;
- AI code reviewers such as GitHub Copilot Code Review or CodeRabbit;
- existing CI, contract tests, security scanners, and linters.

## Sources

- [GitHub Docs: Merge Queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [GitHub Docs: CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Docs: Copilot Code Review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [GitLab Docs: Merge Trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [Mergify Docs: Merge Queue Setup](https://docs.mergify.com/merge-queue/setup/)
- [Graphite Docs: Merge Queue Optimizations](https://graphite.com/docs/merge-queue-optimizations)
- [CodeRabbit Docs: Code Review Overview](https://docs.coderabbit.ai/guides/code-review-overview)
- [SemanticMerge Intro Guide](https://www.semanticmerge.com/documentation/intro-guide/semanticmerge-intro-guide)
- [arXiv: How AI Coding Agents Modify Code](https://arxiv.org/abs/2601.17581)
- [arXiv: How AI Coding Agents Communicate](https://arxiv.org/abs/2602.17084)
