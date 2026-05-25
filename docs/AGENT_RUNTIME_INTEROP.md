# Agent Runtime Interop

Last updated: 2026-05-25

## Positioning

CoProgrammer should not become a coding-agent runtime.

Codex, GitHub Copilot Cloud Agent, OpenHands, SWE-agent, Claude Code, Cursor,
and local CLI agents can all produce code. CoProgrammer should coordinate their
outputs and preserve integration decisions.

The boundary:

| Layer | Owns |
| --- | --- |
| Coding agent runtime | planning, editing, commands, tests, task logs, branch or patch output |
| CoProgrammer Manager Plane | leases, heartbeats, contract board, decision queue, branch digests, integration records |
| Git provider / CI | pull requests, checks, branch protection, merge queue |

## Runtime Artifact Mapping

| Runtime Artifact | CoProgrammer Object |
| --- | --- |
| Agent task/session | agent heartbeat or manager event |
| Claimed file or module scope | workspace lease |
| Proposed contract change | contract board entry |
| Branch or PR | branch digest |
| Test log or terminal evidence | validation evidence in digest or integration record |
| Reviewer approval/rejection | decision record |
| Final integration PR | integration record |

## First Integration Surface

The first stable surface should be Git-based:

1. Agent runtime creates a branch or PR.
2. CoProgrammer runs branch digest against that branch.
3. CoProgrammer checks protected paths and contract signals.
4. Risky findings create Manager decisions.
5. Maintainer records decisions.
6. Later, Integration Patch Bot rebuilds the smallest patch from latest `main`.
7. Existing merge queue validates and lands the integration PR.

This works across Codex, Copilot, OpenHands, SWE-agent, and local agents because
they all can produce branches, diffs, logs, or PRs.

## Local Adapter

The current local prototype already supports:

```bash
coprogrammer manager heartbeat --agent agent-a --task "Implement login"
coprogrammer manager lease request --holder agent-a --pattern "src/api/**"
coprogrammer manager contract propose --proposer agent-a --kind api --name "POST /login" --summary "Change login response"
coprogrammer manager decisions
coprogrammer manager decision record --id decision_123 --decision "serialize work" --decider maintainer
coprogrammer manager status
```

This is enough to test Manager Plane state without depending on any single
agent runtime.

## Future Protocol Surfaces

### MCP

Expose Manager state as:

- tools: request lease, release lease, record decision, create digest;
- resources: active leases, open decisions, latest heartbeats, contract board;
- prompts: branch digest review, integration plan review.

### A2A

Use A2A only as an interoperability bridge when external agents need to
communicate with the Manager Plane or each other. CoProgrammer should not make
agent-to-agent chat its core product.

## Adapter Priority

1. Git/PR adapter: universal and already useful.
2. Local CLI adapter: fastest for experiments and offline use.
3. GitHub App adapter: better webhooks, comments, and checks.
4. MCP server: best agent-facing protocol surface.
5. Runtime-specific adapters: only when a runtime exposes high-value session
   logs or task metadata.

## Non-Goals

- Do not replace coding-agent runtimes.
- Do not build a merge queue.
- Do not require one vendor's agent.
- Do not rely on agent chat as the source of truth.
- Do not let runtime logs replace decision records.

## Open Questions

- Which runtime exposes the most useful task/session metadata today?
- Should CoProgrammer store runtime evidence as files, PR comments, or Manager
  events?
- How much of a branch digest can be generated from PR data alone?
- Which Manager objects should be exposed through MCP first?
