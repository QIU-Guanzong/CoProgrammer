# Scheduling and development-time communication

## Requested outcome

Improve cross-client agent scheduling, prevent cooperating coding windows from
claiming conflicting work, and connect task execution to internal communication.

## Implementation scope

- Durable dependency-aware tasks, client eligibility, atomic claims and path leases.
- Claim tokens bound to a window, worktree and branch; explicit renew, edit guard,
  completion, release and expired-claim recovery. No automatic takeover.
- Shared task board, bounded MCP/CLI wait and participant-scoped task discussions.
- Fix pending-event visibility for nested collaboration transactions and report
  same-label lease overlap instead of hiding it.
- CLI/MCP adapters, behavioral and process tests, README and Active Sync guidance.

Allowed files: scheduler/channels modules and their adapters/tests, existing
collaboration and Manager integration points, Manager event enum, README,
`docs/scheduling/**` and the packaged Active Sync skill. Work is split with exact
path leases; no unrelated refactoring or dependency update.

## Boundaries and shared contracts

The scheduler coordinates cooperating CLI/MCP clients on the local Manager.
It does not launch model processes, inject terminal input, access native private
mailboxes, expose a network service or grant merge authority. Guard checks do
not intercept arbitrary filesystem writes. Shared contract additions remain
draft until maintainer review. No merge, release or live model request here.

## Acceptance

1. Competing claims grant one owner and acquire its edit lease atomically.
2. Dependencies/client eligibility, stale sessions, overlapping paths and shared
   worktrees block inappropriate claims without leaving partial state.
3. Expired/replaced tokens, branch switches and out-of-scope paths fail guard,
   renewal/completion; released/finished claims release only their own lease.
4. Waiting releases locks, times out clearly and responds to relevant updates;
   task discussions retain sent/received/acknowledged history across clients.
5. Real independent MCP processes in linked worktrees exercise the workflow.
6. Full source and installed-wheel tests, config/manifest/schema/skill validation
   and GitHub CI pass; README states verified support and practical limitations.

## Handoff

Update existing draft PR #1 with reviewable code, test evidence and GitHub docs.
