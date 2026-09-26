---
name: coprogrammer-active-sync
description: "Coordinate active multi-agent coding through CoProgrammer Manager state: status, heartbeats, leases, contract proposals, open decisions, and decision records."
---

# CoProgrammer Active Sync

Prerequisite: install the CoProgrammer CLI and make `coprogrammer` available on
`PATH`. This plugin can be used in another repository, so do not assume that
the current project contains CoProgrammer's Python source tree. If the CLI is
unavailable, report Manager state as unavailable and continue only with work
that does not require a live Manager read or write.

Use this workflow during coding when several agents, branches, or worktrees may
touch overlapping code or shared contracts.

## Workflow

1. Initialize Manager state if needed:

```bash
coprogrammer manager init
```

2. Read current shared state:

```bash
coprogrammer manager status
coprogrammer manager leases
coprogrammer manager decisions
coprogrammer manager contracts
```

3. For active work, record a heartbeat:

```bash
coprogrammer manager heartbeat \
  --agent <agent> \
  --task "<task>"
```

4. Before editing a shared area, request a lease:

```bash
coprogrammer manager lease request \
  --holder <agent> \
  --pattern "<path-or-glob>"
```

5. Before changing shared behavior, propose a contract change:

```bash
coprogrammer manager contract propose \
  --proposer <agent> \
  --kind api \
  --name "<contract-name>" \
  --summary "<summary>" \
  --compatibility unknown
```

6. If Manager creates an open decision, stop risky edits until a maintainer
   records the decision.

## Output

Summarize:

- active leases;
- open decisions;
- contract pressure;
- stale or conflicting work;
- recommended next action: proceed, serialize, split scope, or ask maintainer.

Live state belongs in Manager events, not in `AGENTS.md`.
