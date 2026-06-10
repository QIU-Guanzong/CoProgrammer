# Acknowledgments

CoProgrammer learns from, integrates with, and in some cases borrows design
ideas or code from the open-source ecosystem. We believe attribution is part of
the protocol: every borrowed idea is credited, every borrowed line of code
keeps its license.

## Borrowing Policy

1. **Ideas and patterns**: when a design pattern is adapted (not copied), we
   credit the source project in the relevant design doc under a `Sources`
   section, and list it here.
2. **Code**: if code is vendored or adapted, the original license header is
   preserved, the source repository and commit are recorded in the file, and
   the project is listed below with its license. We only adapt code under
   licenses compatible with this repository's MIT license.
3. **Data**: research datasets (e.g. AgenticFlict) are used under their
   published terms and cited in evaluation reports.
4. **Competitors are also teachers**: projects solving adjacent problems are
   credited for what we learned, even where we deliberately diverge.

## Projects and Research We Learn From

### Design patterns adapted

| Source | License | What we adapted |
| --- | --- | --- |
| Sourcegraph Batch Changes | Apache-2.0 (docs/concepts) | Spec-and-reconciliation model for integration plans. |
| bors-ng | Apache-2.0 | Staging-branch principle: validate on a rebuilt branch, not the source branch. |
| Danger JS | MIT | Policy-as-code and PR messaging shape. |
| reviewdog | MIT | Machine-readable finding/reporting format. |
| Renovate | AGPL-3.0 (ideas only, no code) | Dashboard issue and confidence metadata ideas. |
| OpenRewrite | Apache-2.0 / MSAL | Recipe-based deterministic transformation model. |
| Comby | Apache-2.0 | Structural search/replace as a deterministic patch primitive. |
| AGENTS.md | CC / community spec | Minimal stable agent instruction convention. |
| Paperclip | (see upstream) | Persistent manager/control-plane event model. |

### Upstream runtimes and orchestrators we integrate with (not fork)

Conductor (Microsoft, MIT), Sculptor (Imbue), Vibe Kanban (BloopAI,
community-maintained), Claude Squad, Composio agent-orchestrator, OpenHands
(MIT), SWE-agent (MIT), OpenAI Codex, GitHub Copilot Cloud Agent.

### Research that shaped the design

- *AgenticFlict: A Large-Scale Dataset of Merge Conflicts in AI Coding Agent
  Pull Requests on GitHub* (arXiv:2604.03551) — empirical grounding and our
  primary evaluation dataset.
- *AgentSpawn / Coherence Manager* — the auto-merge / semantic-merge /
  escalation triage model and its observed 15% / 73% / 12% distribution.
- *CodeCRDT: Observation-Driven Coordination for Multi-Agent LLM Code
  Generation* (arXiv:2510.18893) — observation-driven (not chat-driven)
  coordination, reflected in our Manager event log and forecast design.
- *SWE-agent* (arXiv:2405.15793) — agent-computer-interface thinking.
- Studies of agentic PRs (arXiv:2601.17581, 2602.17084, 2601.15195,
  2605.22534) — evidence for making branch intent and manifests first-class.

If you believe your project should be listed here or is credited incorrectly,
please open an issue — we will fix it promptly.
