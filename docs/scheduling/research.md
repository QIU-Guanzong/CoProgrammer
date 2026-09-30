# Scheduling research and implementation choices

Reviewed 2026-09-27. Source capabilities can change; local implementation and
verification are described separately in the [workflow](README.md).

| Primary source | Relevant observation | CoProgrammer choice |
| --- | --- | --- |
| [Codex MCP documentation](https://developers.openai.com/codex/mcp/) | Clients discover and invoke server tools; tool calls have configured timeouts. | One CLI/MCP core, discoverable task tools and a wait capped at 25 seconds. Tool availability does not establish native wakeup. |
| [Claude cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) | Claude has native session discovery and delivery between tool calls, with idle-session wakeup and session permissions. | Keep a portable durable task channel; do not read private sockets or present local polling as a native Claude bridge. |
| [Claude agent teams](https://code.claude.com/docs/en/agent-teams) | Shared task lists support dependency tracking and claims. | Add dependency-aware atomic claims coupled to path leases, with an explicit recovery path. |
| [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail) | Task discussions, mailboxes and acknowledgements support asynchronous cooperation. | Preserve sender/recipient conversation history separately from receipt and task completion. |
| [Overstory](https://github.com/jayminwest/overstory) | Its orchestration combines workspaces, task execution and mail coordination. | Put sync, pulse, guard and communication at explicit work boundaries; process orchestration remains outside this preview. |
| [gstack](https://github.com/garrytan/gstack) | Its workflow separates planning, implementation, review and verification. | Keep author-reported task completion distinct from tests, reviewer decisions and integration. |

The main implementation decision is to treat ownership as one transaction:
claim a task and its file scope together. A unique token identifies the claim,
while the original window, worktree and branch constrain later operations.
Freshness and expiry are explicit, and an expired claim never authorizes a
second worker to take over silently. Same-worktree exclusion addresses the
shared Git index as well as file-level overlap.

Client labels route work without assuming that one model brand is always best
at a role. GLM and DeepSeek remain provider choices behind a compatible client
or the existing explicit review adapter. No credentials or model calls are
needed for coordination.

Next research questions: supported native delivery adapters with explicit user
authorization; process lifecycle and cancellation; creator-unavailable recovery;
cross-machine authenticated transport; log compaction; and real-client latency
and missed-message measurements. None is described as shipped functionality.
