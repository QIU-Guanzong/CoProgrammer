# When multi-agent coding coordination is useful

CoProgrammer is useful when several coding windows share a repository and need
more than separate Git branches. It records ownership, dependencies, file scope
and handoffs. It has not yet established measured productivity gains or broad
adoption through an independent user study.

| Your problem / 你遇到的问题 | What to try | Actual boundary |
| --- | --- | --- |
| Codex and Claude edit overlapping files / 多个 AI 窗口改到同一文件 | Separate Git worktrees, scoped tasks and `worker step` guards | Cooperative checks; no interception of arbitrary writes |
| An agent starts before the API task finishes / 上下游任务顺序混乱 | Task dependencies and client/provider filters | Completion is reported by the worker, not automatically code-reviewed |
| A window restart loses the handoff / 窗口重启后丢失上下文 | Durable local messages, explicit receipt and `status` | No platform chat injection or automatic window wakeup |
| A custom agent harness repeats coordination commands / 每次手动同步分工 | Explicit `worker run` command and optional inbox receipts | A trusted command still needs its own execution tools and model account |
| OpenClaw MCP setup is hard to verify / 不知道 MCP 是否真正接上 | `integrations verify --client openclaw` | Native discovery is separate from live model execution |

Start with [the two-window walkthrough](GETTING_STARTED.md) or
[the harness workflow](NATIVE_RUNTIME_WORKFLOW.md). Search terms describing this
scope include **multi-agent coding**, **Codex Claude collaboration**, **Git
worktree task scheduling**, **AI coding conflict checks**, and **MCP agent
coordination**. 中文对应：多智能体编程协作、Codex/Claude 协作、多窗口任务调度、
Git 工作树冲突检查、AI 助手交接。

## When the extra layer is unnecessary

A single assistant working on a small task usually needs no shared queue. Git
worktrees may be enough when work is independent and your team already has a
reliable handoff process. CoProgrammer is not a replacement for Git merges, CI,
human review, a model subscription or a full coding-agent runtime. It does not
automatically discover semantic bugs caused by changes to different files.

## How to judge whether it helps

Try one real two-window feature with explicit file scopes and an upstream
dependency. Record coordination commands, overlapping-edit incidents, lost
handoffs, setup failures and the time spent maintaining the extra state. Keep it
only if those costs improve your own workflow. A passing protocol fixture proves
mechanism behavior; stars, a generated config and test counts do not establish
user value.

GitHub [topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)
help people find projects by subject. This repository uses matching topics,
bilingual problem statements and PyPI keywords. Search indexing, ranking, stars
and discovery by a particular query are not guaranteed. No community outreach or
marketplace listing should be described as complete unless actually submitted
and publicly verified.
