# High-Star Project Scan

Last updated: 2026-05-26

This scan captures high-star GitHub projects that can inform CoProgrammer. Star
counts are approximate and were checked through the GitHub API on 2026-05-26.

The goal is not to copy high-star projects. The goal is to identify reusable
patterns for Manager Plane, semantic integration, validation, and runtime
interop.

## Coding Agent Runtimes

| Project | Stars | Borrow | CoProgrammer Boundary |
| --- | ---: | --- | --- |
| [opencode](https://github.com/anomalyco/opencode) | ~165k | CLI/SDK agent experience, session ergonomics | Upstream runtime, not CoProgrammer core |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | ~104k | Terminal agent interaction and tool execution evidence | Upstream runtime |
| [OpenHands](https://github.com/OpenHands/OpenHands) | ~75k | sandboxed coding agents and platform architecture | Upstream runtime |
| [Cline](https://github.com/cline/cline) | ~62k | approval UX, tool-call transparency, plan/act flow | Runtime UX reference |
| [aider](https://github.com/Aider-AI/aider) | ~45k | Git-native edit/test/commit loop | Patch workflow reference |
| [Continue](https://github.com/continuedev/continue) | ~33k | source-controlled AI checks and CI enforcement | Policy/check reference |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | ~19k | issue-to-patch loop and agent-computer interface | Research/runtime reference |

Decision:

CoProgrammer should consume these runtimes' branches, diffs, logs, and PRs. It
should not become another coding agent.

## Multi-Agent Orchestration

| Project | Stars | Borrow | CoProgrammer Boundary |
| --- | ---: | --- | --- |
| [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | ~185k | agent platform/dashboard ambition | Too broad; do not copy product scope |
| [MetaGPT](https://github.com/FoundationAgents/MetaGPT) | ~68k | role artifacts and software-company metaphor | Borrow artifacts, avoid broad company simulation |
| [AutoGen](https://github.com/microsoft/autogen) | ~58k | multi-agent workflow and handoff patterns | Runtime framework, not integration policy |
| [CrewAI](https://github.com/crewAIInc/crewAI) | ~52k | role/task orchestration | General agent workflow |
| [LangGraph](https://github.com/langchain-ai/langgraph) | ~33k | durable state graphs | Possible Manager workflow substrate |
| [OpenAI Agents Python](https://github.com/openai/openai-agents-python) | ~26k | lightweight multi-agent workflow primitives | Runtime framework |

Decision:

Borrow state machines, handoffs, observability, and durable workflow ideas.
Avoid making CoProgrammer a generic multi-agent framework.

## Code Analysis and Patch Primitives

| Project | Stars | Borrow | CoProgrammer Boundary |
| --- | ---: | --- | --- |
| [tree-sitter](https://github.com/tree-sitter/tree-sitter) | ~26k | multi-language parsing and semantic diff foundation | Possible parser layer |
| [Semgrep](https://github.com/semgrep/semgrep) | ~15k | rule-based invariant checks | Validation layer |
| [ast-grep](https://github.com/ast-grep/ast-grep) | ~14k | structural search, lint, rewrite | Patch primitive |
| [jscodeshift](https://github.com/facebook/jscodeshift) | ~10k | JavaScript codemods | Language-specific patch primitive |
| [ts-morph](https://github.com/dsherret/ts-morph) | ~6k | TypeScript AST editing | TypeScript patch primitive |

Decision:

Integration Patch Bot should prefer deterministic primitives before LLM patch
generation.

## Validation and Workspace Infrastructure

| Project | Stars | Borrow | CoProgrammer Boundary |
| --- | ---: | --- | --- |
| [LiteLLM](https://github.com/BerriAI/litellm) | ~48k | model gateway, cost/routing abstraction | Future model routing backend |
| [Trivy](https://github.com/aquasecurity/trivy) | ~35k | vulnerability/secret/SBOM scanning | Validation layer |
| [Renovate](https://github.com/renovatebot/renovate) | ~22k | dashboard issue, policy config, confidence metadata | Existing research lead |
| [pre-commit](https://github.com/pre-commit/pre-commit) | ~15k | local validation hook registry | Validation registry reference |
| [Coder](https://github.com/coder/coder) | ~13k | secure dev environments for humans and agents | Workspace provisioning reference |
| [Gitpod](https://github.com/gitpod-io/gitpod) | ~14k | on-demand development environments | Workspace provisioning reference |

Decision:

Borrow model routing, validation registry, and isolated workspace ideas. Do not
build a full cloud IDE.

## Fusion Into CoProgrammer

The fused architecture should be:

1. upstream coding agents create branches and evidence;
2. CoProgrammer Manager records heartbeats, leases, contracts, and decisions;
3. branch digest separates insight from noise;
4. integration plan selects deterministic patch primitives first;
5. model routing decides which model tier can perform each task;
6. validation gates and human decisions control high-risk work;
7. existing merge queues land final integration PRs.

## Priority Additions

Add these to structured research leads first:

- Continue;
- Cline;
- aider;
- opencode;
- Gemini CLI;
- LangGraph;
- LiteLLM;
- Semgrep;
- ast-grep;
- tree-sitter;
- Coder.

These have the highest direct value for CoProgrammer's next phase.
