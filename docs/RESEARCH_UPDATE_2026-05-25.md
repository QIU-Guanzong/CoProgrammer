# Research Update: Manager Plane Evidence

Last updated: 2026-05-25

## Chinese Summary

这一轮调研的结论更明确了：CoProgrammer 不应该只做 PR review
机器人，也不应该变成另一个通用 coding agent。更好的位置是：

> 给并行 coding agents 提供一个软件集成专用的 Manager Plane。

也就是说，Codex、GitHub Copilot Cloud Agent、OpenHands、SWE-agent
这类工具负责执行任务；CoProgrammer 负责管理它们之间共享的软件状态：
leases、contracts、branch digests、decisions、integration records。

## What Changed

### 1. Agent runtimes are moving to background parallel work

OpenAI Codex describes a cloud software engineering agent that can work on many
tasks in parallel, each in an isolated sandbox preloaded with the repository.
GitHub Copilot Cloud Agent similarly works in GitHub Actions-powered
environments, can research, plan, create branches, and optionally open pull
requests. OpenHands provides an open-source platform and SDK for autonomous
coding agents, including sandboxed environments and multi-agent coordination
research.

Implication:

- CoProgrammer should not compete with these runtimes.
- CoProgrammer should sit above them as the durable repository-state and
  semantic integration layer.
- The Manager Plane should assume multiple agent-produced branches will exist
  at the same time.

### 2. Empirical PR studies validate decision records

Recent agentic PR studies show that merge/rejection status alone is a poor
measure of agent performance. Rejected agentic PRs can reflect agent failures,
workflow constraints, duplicate work, missing rationale, or lack of reviewer
engagement. Failed PR studies also report that not-merged agent PRs often touch
more files, fail CI, duplicate existing work, implement unwanted features, or
show agent misalignment.

Implication:

- CoProgrammer should record why a branch was accepted, rejected, deferred, or
  partially integrated.
- Branch digest must separate useful insight from noisy implementation.
- Decision records are not bureaucracy; they are needed evaluation data.

### 3. CAID is the closest research match

The Centralized Asynchronous Isolated Delegation pattern describes three
software-engineering primitives: centralized task delegation, asynchronous
execution, and isolated workspaces. It also treats structured integration and
test-based verification as core to consolidating agent work.

Implication:

- CoProgrammer's Manager Plane should be treated as a productized CAID-style
  layer for real repositories.
- The local event log prototype is on the right track: leases, decisions,
  heartbeats, and status reconstruction are minimum viable Manager objects.

### 4. AGENTS.md is useful but insufficient

AGENTS.md provides a simple open format for repository-level agent instructions.
However, a 2026 evaluation found that context files can reduce task success and
increase inference cost when they include unnecessary requirements, even though
agents tend to respect the instructions.

Implication:

- CoProgrammer should support a minimal `AGENTS.md` or `Main Branch
  Constitution`, but should not dump all policy into natural-language prompts.
- Live coordination state belongs in structured Manager objects, not in an
  ever-growing instruction file.
- Repository instructions should say how to work; the Manager Plane should say
  what is currently happening.

### 5. MCP and A2A are transport/interoperability layers

MCP standardizes how applications expose tools, resources, prompts, and
notifications to agents. A2A focuses on secure agent-to-agent communication and
interoperability. These are useful infrastructure layers, but they do not define
software integration semantics.

Implication:

- CoProgrammer can expose Manager Plane state through MCP tools/resources later.
- CoProgrammer can interoperate with A2A runtimes later.
- CoProgrammer's durable value remains the software-specific object model:
  branch digest, lease, contract board, decision record, integration record.

## Roadmap Adjustment

The MVP should now be framed as two connected surfaces, not one:

1. **Branch Digest Bot**
   - PR diff and commit ingestion;
   - branch intent and risk extraction;
   - protected-path and contract signals;
   - reviewer-facing integration plan.

2. **Manager Event Log**
   - agent heartbeats;
   - workspace leases;
   - decision queue;
   - status reconstruction;
   - later: contract board and integration records.

The Integration Patch Bot remains important, but it should come after the
Manager Plane can reliably record decisions and contract state.

## Next Experiments

### Experiment A: Three-Agent Lease Simulation

Run three agents against one small repo:

- backend agent touches `src/api/**`;
- frontend agent depends on an API shape;
- test agent modifies shared fixtures.

Measure:

- number of lease conflicts forecast before Git conflict;
- number of decision records created;
- whether integration diff is smaller than raw combined branch diff.

### Experiment B: Minimal Context File Test

Compare:

- no `AGENTS.md`;
- minimal `AGENTS.md`;
- long policy-heavy `AGENTS.md`;
- minimal `AGENTS.md` plus structured `.coprogrammer.json`.

Measure:

- task success;
- files touched;
- test runs;
- instruction violations;
- output size and time.

### Experiment C: Agentic PR Retrospective

Take real or internal agent-authored PRs and label:

- accepted as-is;
- accepted after human edits;
- rejected due agent error;
- rejected due duplicate work;
- rejected due workflow or product decision;
- partially integrated through a new patch.

Map each category to missing CoProgrammer artifacts.

## Build Decisions

| Decision | Status | Rationale |
| --- | --- | --- |
| Treat Codex, Copilot, OpenHands, SWE-agent as upstream runtimes | Adopt | They create branches and task artifacts; CoProgrammer should coordinate and integrate them. |
| Build Manager Event Log first | Adopt | CAID and Paperclip both validate persistent manager state. |
| Keep AGENTS.md minimal | Adopt | Context-file evidence warns against overloading instruction files. |
| Add MCP server later | Watch | MCP is a good access layer, but not the core product. |
| Add A2A bridge later | Watch | A2A helps interop, but CoProgrammer should first define repo-state semantics. |
| Build own merge queue | Avoid | Existing queues and trains should remain downstream gates. |

## Sources

- [OpenAI: Introducing Codex](https://openai.com/index/introducing-codex/)
- [OpenAI: Codex is now generally available](https://openai.com/index/codex-now-generally-available/)
- [GitHub Docs: About GitHub Copilot Cloud Agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
- [GitHub Docs: Copilot Cloud Agent usage](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent)
- [OpenHands GitHub repository](https://github.com/OpenHands/OpenHands)
- [arXiv: OpenHands](https://arxiv.org/abs/2407.16741)
- [arXiv: SWE-agent](https://arxiv.org/abs/2405.15793)
- [Hugging Face Papers: Effective Strategies for Asynchronous Software Engineering Agents](https://huggingface.co/papers/2603.21489)
- [arXiv: Where Do AI Coding Agents Fail?](https://arxiv.org/abs/2601.15195)
- [arXiv: Why Are Agentic Pull Requests Merged or Rejected?](https://arxiv.org/abs/2605.22534)
- [AGENTS.md repository](https://github.com/agentsmd/agents.md)
- [arXiv: Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)
- [arXiv: Configuring Agentic AI Coding Tools](https://arxiv.org/abs/2602.14690)
- [Model Context Protocol architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [Linux Foundation: Agent2Agent Protocol Project](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [Graphite Merge Queue](https://graphite.com/docs/graphite-merge-queue)
- [GitLab Merge Trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
