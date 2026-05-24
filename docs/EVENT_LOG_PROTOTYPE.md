# Event Log Prototype

Last updated: 2026-05-24

The first Manager Plane prototype can be local and append-only. It does not
need a hosted service.

## Goal

Demonstrate that a persistent state layer can prevent stale shared-state
failures between two coding agents.

## Prototype Hypothesis

If agents write heartbeats, lease requests, and decisions into a shared event
log, then the Manager can detect overlapping work earlier than Git merge
conflicts.

## Storage

Use a local JSONL file first:

```text
.coprogrammer/events.jsonl
```

Each line is a `manager-event`:

```json
{"id":"evt_1","type":"lease.requested","timestamp":"2026-01-01T00:00:00Z","actor":"agent-a","subject":"repo:owner/name","payload":{"patterns":["src/api/**"]}}
```

Do not commit `.coprogrammer/events.jsonl` by default. It is workspace state,
not source code.

## Derived State

The prototype can rebuild state by replaying events:

- active agent sessions;
- active leases;
- open decisions;
- proposed contracts;
- branch digests.

This keeps the first implementation simple and auditable.

## CLI Sketch

```bash
coprogrammer manager init
coprogrammer manager event append --type lease.requested --actor agent-a --payload payload.json
coprogrammer manager lease request --holder agent-a --pattern "src/api/**"
coprogrammer manager lease request --holder agent-b --pattern "src/api/auth.py"
coprogrammer manager leases
coprogrammer manager decisions
coprogrammer manager decision record --id decision_123 --decision "serialize work" --decider maintainer
coprogrammer manager status
coprogrammer manager heartbeat --agent agent-a --task "Implement login"
```

Current prototype status:

- `manager init` creates `.coprogrammer/events.jsonl`;
- `manager heartbeat` appends `agent.heartbeat`;
- `manager event append` appends raw events;
- `manager lease request` grants non-overlapping leases;
- `manager lease request` creates `decision.requested` for overlapping leases;
- `manager lease release` appends `lease.released`;
- `manager leases` reconstructs active leases by replaying events;
- `manager decisions` reconstructs open decisions by replaying events;
- `manager decision record` appends `decision.recorded`;
- `manager status` prints reconstructed event count, active leases, open
  decisions, and latest heartbeats.

## Simulation

Scenario:

1. Agent A requests lease for `src/api/**`.
2. Agent B requests lease for `src/api/auth.py`.
3. Manager detects overlap.
4. Manager emits `decision.requested`.
5. Human decides whether to split scope, serialize work, or allow overlap.
6. Manager records the decision and removes it from the open queue.

Expected output:

```text
conflict: agent-b overlaps active lease lease_agent_a
decision requested: should agent-b proceed on src/api/auth.py?
decision recorded: decision_123 [decided]
```

## Acceptance Criteria

- Event append is deterministic.
- JSON lines validate against `schemas/manager-event.schema.json` shape.
- Active leases can be reconstructed from events.
- Overlapping path leases produce a decision request.
- Recorded decisions close the open decision item.
- No Git branch mutation is required.

Implemented first:

- active lease reconstruction;
- overlap detection for path globs;
- decision request creation on lease conflict;
- decision recording;
- status snapshot reconstruction;
- local JSONL persistence.

## Later Storage Options

After the JSONL prototype:

- SQLite for local desktop/workspace state;
- Postgres for team/shared service;
- GitHub Issue/Discussion fallback for teams that do not want a service;
- hosted Manager Plane for cross-repo usage.

## Risk

An event log can become noise if agents emit too much. The prototype should
start with only high-signal events:

- heartbeat;
- lease request/grant/release;
- contract change proposed;
- decision requested/recorded;
- branch digest created;
- integration recorded.
