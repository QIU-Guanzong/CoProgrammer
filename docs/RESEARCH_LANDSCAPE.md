# Research Landscape

Last updated: 2026-06-10

CoProgrammer sits between existing code review tools and merge automation. The
current ecosystem can review, queue, test, and structurally merge code, but it
does not yet provide a complete branch-intent digestion and semantic
reintegration layer.

For a living list of open-source adjacent projects and reusable small features,
see `docs/OPEN_SOURCE_SCAN.md`. For a product-level comparison, see
`docs/FEATURE_GAP_MATRIX.md`.

## Key Finding

The market already has strong tools for:

- autonomous coding agents and cloud task execution;
- path ownership and protected review;
- AI-assisted pull request review;
- merge queues and merge trains;
- structural or syntax-aware merge help.

The gap is the layer that asks:

> What did this branch learn, which parts are worth preserving, and how should
> those ideas be rebuilt as the smallest safe patch on top of current main?

That is CoProgrammer's target layer.

The 2026-05-25 update adds a stronger runtime/coordination distinction:
Codex, GitHub Copilot Cloud Agent, OpenHands, and SWE-agent are upstream agent
runtimes. MCP and A2A are interoperability layers. CoProgrammer's distinct
scope is the software integration state that lives between those runtimes and
the merge queue.

### 2026-06-10 Update

Four developments since the last scan:

1. **Orchestration is commoditizing and consolidating.** Conductor (Microsoft,
   MIT), Sculptor (Imbue, container isolation), Composio agent-orchestrator,
   Claude Squad, Emdash, and Baton all ship worktree/container-isolated
   parallel agents. Vibe Kanban is sunsetting to community maintenance;
   Terragon shut down 2026-01. Conclusion: do **not** build orchestration;
   integrate with it (`docs/ORCHESTRATOR_INTEGRATION.md`).
2. **The semantic-integration layer got empirical validation.** AgentSpawn's
   Coherence Manager reports a triage distribution of auto-merge 15%, semantic
   merge 73%, escalation 12% — the 73% band is exactly CoProgrammer's target
   layer. AgenticFlict (arXiv:2604.03551) publishes a large-scale dataset of
   merge conflicts in AI-agent PRs, which becomes our primary evaluation set
   (`docs/EVAL_PLAN.md`).
3. **Direct competitors emerged.** Intent (shared-spec single source of truth
   for multi-agent workspaces) overlaps our Protocol Plane and contract board;
   MergeLoom markets "governed AI coding." Track both closely.
4. **The gap statement is now industry consensus.** 2026 reviews repeatedly
   note that orchestrators "leave task alignment, conflict resolution, and
   merge decisions on the developer's plate," and that nothing coordinates
   agents "against a shared evolving plan." That remains CoProgrammer's moat:
   Branch Intelligence + Semantic Integration planes, plus pre-PR conflict
   forecasting (`coprogrammer manager forecast`).

## Capability Map

| Area | Existing Capability | Remaining Gap for CoProgrammer |
| --- | --- | --- |
| Coding-agent runtime | Codex, GitHub Copilot Cloud Agent, OpenHands, and SWE-agent can run coding tasks, create branches, execute tests, and provide session artifacts. | Coordinate multiple agent-produced branches, forecast collisions, digest intent, and record integration decisions. |
| Agent instructions | AGENTS.md and tool-specific context files provide stable repository guidance. | Keep instructions minimal and move live coordination state into structured Manager objects. |
| Agent protocols | MCP exposes tools/resources/context; A2A targets agent interoperability. | Define repository-native objects and semantics: lease, contract board, branch digest, decision record, integration record. |
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
6. Agent instructions should be deliberately small. The Manager event log and
   `.coprogrammer.json` should carry structured state and policy.
7. CoProgrammer should expose protocol surfaces later, but should first prove
   its domain model through local CLI and GitHub-native workflows.

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
- future MCP/A2A access layer for Manager Plane state.

Integrate with existing tools:

- GitHub/GitLab PRs and merge requests;
- CODEOWNERS;
- branch protection;
- GitHub Merge Queue or GitLab Merge Trains;
- Mergify or Graphite where teams already use them;
- AI code reviewers such as GitHub Copilot Code Review or CodeRabbit;
- existing CI, contract tests, security scanners, and linters.
- upstream coding agents such as Codex, Copilot Cloud Agent, OpenHands, and
  SWE-agent.

## Sources

- [GitHub Docs: Merge Queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [GitHub Docs: CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Docs: Copilot Code Review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [OpenAI: Introducing Codex](https://openai.com/index/introducing-codex/)
- [GitHub Docs: Copilot Cloud Agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
- [OpenHands](https://github.com/OpenHands/OpenHands)
- [SWE-agent](https://arxiv.org/abs/2405.15793)
- [AGENTS.md](https://github.com/agentsmd/agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)
- [Linux Foundation: Agent2Agent Protocol](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [GitLab Docs: Merge Trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [Mergify Docs: Merge Queue Setup](https://docs.mergify.com/merge-queue/setup/)
- [Graphite Docs: Merge Queue Optimizations](https://graphite.com/docs/merge-queue-optimizations)
- [CodeRabbit Docs: Code Review Overview](https://docs.coderabbit.ai/guides/code-review-overview)
- [SemanticMerge Intro Guide](https://www.semanticmerge.com/documentation/intro-guide/semanticmerge-intro-guide)
- [arXiv: How AI Coding Agents Modify Code](https://arxiv.org/abs/2601.17581)
- [arXiv: How AI Coding Agents Communicate](https://arxiv.org/abs/2602.17084)
- [arXiv: Failed Agentic Pull Requests](https://arxiv.org/abs/2601.15195)
- [arXiv: Agentic PR Merge/Rejection Study](https://arxiv.org/abs/2605.22534)
- [arXiv: Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)
- [arXiv: AgenticFlict — Merge Conflicts in AI Coding Agent PRs](https://arxiv.org/abs/2604.03551)
- [arXiv: CodeCRDT — Observation-Driven Multi-Agent Coordination](https://arxiv.org/abs/2510.18893)
- [arXiv: Multi-agent Collaboration with State Management](https://arxiv.org/abs/2605.20563)
- [Microsoft Conductor](https://opensource.microsoft.com/blog/2026/05/14/conductor-deterministic-orchestration-for-multi-agent-ai-workflows/)
- [Imbue Sculptor](https://imbue.com/blog/sculptor-announce)
- [Vibe Kanban](https://github.com/BloopAI/vibe-kanban)
- [Composio agent-orchestrator](https://github.com/ComposioHQ/agent-orchestrator)
- [Open-Source Agent Orchestrators review (Augment Code, 2026)](https://www.augmentcode.com/tools/open-source-agent-orchestrators)
- [The Code Agent Orchestra (Addy Osmani)](https://addyosmani.com/blog/code-agent-orchestra/)
- [MergeLoom](https://mergeloom.ai/)
