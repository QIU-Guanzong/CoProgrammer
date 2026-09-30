# Multi-window collaboration: evidence and product choices

Reviewed 2026-09-27. This is a comparison of first-party project documentation
and our implementation gaps, not a user survey or a measured market-size claim.

| Observed developer problem | Reference and observed approach | CoProgrammer choice |
| --- | --- | --- |
| Many terminals obscure which session owns which work | [agent-deck](https://github.com/asheshgoplani/agent-deck) manages agent sessions, worktrees and terminal navigation | Persist a window directory with client, task, worktree and explicit pulse age; leave terminal lifecycle to the client |
| Humans repeatedly relay context between independent agents | [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail) exposes identities, durable inboxes, threaded messages and advisory reservations | Add task-scoped messages, explicit receipt and retry keys to the existing Manager log; keep its lease system |
| Team workflows need explicit messages and recoverable handoffs | [Overstory](https://github.com/jayminwest/overstory) combines isolated worktrees, typed mail and runtime orchestration | Keep update/question/handoff types and reply linkage; make the same operations available to independent CLI/MCP clients |
| Session recovery and stale task state can mislead the coordinator | [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams) documents shared tasks/messaging and session-resumption/status limitations | Preserve inboxes across process restart; distinguish declared status from pulse freshness and do not equate either with verified process liveness |
| Review stage completion and evidence can drift from the code | [gstack design sources already reviewed here](../github-intro/collaboration-notes.md) separate handoffs and verification | Handoff messages carry context; review-summary and commit-bound evidence remain the place to inspect verification |

These projects target overlapping but different surfaces. A terminal manager is
useful when the main problem is navigating and controlling processes. A mail
service emphasizes durable asynchronous communication. An orchestrator controls
worker lifecycle. CoProgrammer's selected increment connects independent coding
windows to existing repository state and review artifacts without taking over
their runtimes. No referenced implementation is copied or bundled.

## Requirements translated into implementation

1. **One window, one session ID.** Multiple Codex or Claude windows must coexist.
   The runtime/client, optional provider/model, task and Git context are separate
   fields. Registration cannot overwrite an existing ID.
2. **Recoverable communication.** A task message is persisted before success is
   returned. Client retry keys deduplicate identical sends atomically. Receipt
   is explicit, repeatable and separate from task completion or review approval.
3. **Continuity across clients.** Every client reads the same worktree-aware
   Manager location. Opaque event-ID cursors resume ordered changes; pending
   inbox snapshots remain visible even after the cursor moves past a message.
4. **Visible uncertainty.** A stale pulse remains stale until an explicit update.
   No UI scrape, terminal injection, hidden process watcher or model API call is
   involved. Tests describe protocol clients as such, rather than claiming live
   vendor integration.
5. **Cooperative local trust.** Session names route messages, not permissions.
   All clients with file access can inspect or alter state. This is explicit in
   the CLI/MCP guide; multi-user hosted access requires a separate design.

## Evidence and remaining product boundaries

Behavioral tests cover registration, closure, stale/future pulses, duplicate and
conflicting retries, recipient-only acknowledgements, reply task/participant
consistency, pagination, invalid input/history, CLI/MCP parity and cross-worktree
binding. A real two-process test exchanges and acknowledges a handoff across
linked Git worktrees and restarts a receiver without losing its pending inbox.

This increment provides local, pull-based synchronization. It does not claim
automatic push into arbitrary GUI windows, authenticated cross-machine teams,
an autonomous work scheduler, verified reviewer identity or a released package.
Those are different capabilities requiring additional implementation and proof.
