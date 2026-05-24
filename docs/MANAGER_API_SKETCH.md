# Manager Plane API Sketch

Last updated: 2026-05-24

This is a first API sketch for the CoProgrammer Manager Plane. It is not yet an
implementation contract. It defines the minimum surface needed to coordinate
coding agents without making them talk directly to each other.

## Design Goals

- Keep humans in control of high-risk decisions.
- Store durable shared state outside agent-local context windows.
- Support multiple coding agents and runtimes.
- Work locally first, then support self-hosted or cloud deployment.
- Integrate with GitHub, CI, and merge queues rather than replacing them.

## Core Resources

| Resource | Purpose |
| --- | --- |
| Repository | A source repository under Manager Plane supervision. |
| Agent Session | One active coding-agent run. |
| Workspace Lease | A claimed path, contract, test surface, or integration branch. |
| Contract Entry | A proposed or accepted shared contract change. |
| Branch Digest | A branch-intelligence artifact. |
| Decision Record | A human or advisor decision request and outcome. |
| Integration Record | A completed integration attempt and validation result. |
| Manager Event | Append-only audit event for all important state changes. |

## API Principles

1. Every state-changing call emits a Manager Event.
2. Leases and decisions are first-class; they are not hidden in comments.
3. Agents may request, propose, and report; maintainers decide high-risk items.
4. API responses should include current conflict or decision pressure.
5. The first implementation may be local-only, backed by JSONL or SQLite.

## Endpoints

### Health

```http
GET /v1/health
```

Returns service health and schema version.

### Repositories

```http
POST /v1/repositories
GET /v1/repositories
GET /v1/repositories/{repo_id}
```

Repository object:

```json
{
  "id": "repo_owner_name",
  "provider": "github",
  "full_name": "owner/name",
  "default_branch": "main",
  "policy_path": ".coprogrammer.json"
}
```

### Agent Sessions

```http
POST /v1/repos/{repo_id}/agent-sessions
GET /v1/repos/{repo_id}/agent-sessions
PATCH /v1/agent-sessions/{session_id}
```

Agent sessions connect heartbeats, leases, manifests, and branches.

### Heartbeats

```http
POST /v1/agent-sessions/{session_id}/heartbeats
```

Input should be compatible with `schemas/agent-heartbeat.schema.json`.

Manager response should include:

- accepted heartbeat id;
- active leases;
- relevant open decisions;
- detected conflicts or stale-state warnings.

### Workspace Leases

```http
POST /v1/repos/{repo_id}/leases
GET /v1/repos/{repo_id}/leases?status=active
PATCH /v1/leases/{lease_id}
POST /v1/leases/{lease_id}/release
```

Input should be compatible with `schemas/workspace-lease.schema.json`.

Lease conflict response:

```json
{
  "status": "conflict",
  "conflicts": [
    {
      "lease_id": "lease_backend_api",
      "holder": "agent-backend",
      "patterns": ["src/api/**"]
    }
  ],
  "suggested_action": "request_decision"
}
```

### Contract Board

```http
POST /v1/repos/{repo_id}/contracts
GET /v1/repos/{repo_id}/contracts?status=proposed
PATCH /v1/contracts/{contract_id}
```

Contract entries should capture:

- name;
- kind: API, schema, migration, shared type, auth, payment, deployment;
- proposed compatibility;
- producer branch;
- affected consumers;
- required owner review.

### Branch Digests

```http
POST /v1/repos/{repo_id}/branch-digests
GET /v1/repos/{repo_id}/branch-digests/{digest_id}
```

The POST can either upload a digest artifact or request Manager to create one
from Git metadata.

### Decision Records

```http
POST /v1/repos/{repo_id}/decisions
GET /v1/repos/{repo_id}/decisions?status=open
PATCH /v1/decisions/{decision_id}
POST /v1/decisions/{decision_id}/resolve
```

Input should be compatible with `schemas/decision-record.schema.json`.

Decision examples:

- "Should this schema change be accepted as breaking?"
- "Should agent-b rewrite the shared auth middleware?"
- "Should this branch be integrated or reimplemented as a minimal patch?"

### Integration Records

```http
POST /v1/repos/{repo_id}/integration-records
GET /v1/repos/{repo_id}/integration-records
GET /v1/integration-records/{record_id}
```

Input should be compatible with `schemas/integration-record.schema.json`.

### Event Log

```http
GET /v1/repos/{repo_id}/events
POST /v1/repos/{repo_id}/events
```

Input should be compatible with `schemas/manager-event.schema.json`.

The event log is append-only.

## First MVP Cut

Do not implement everything at once.

First useful API slice:

1. `POST /agent-sessions`
2. `POST /heartbeats`
3. `POST /leases`
4. `GET /leases`
5. `POST /decisions`
6. `GET /decisions`
7. `POST /events`

This supports a local simulation where two agents request overlapping path
leases and Manager creates a decision record instead of letting them proceed
blindly.

## Open Questions

- Should the first implementation expose HTTP or only CLI commands?
- Should repository state live inside `.coprogrammer/` or outside the repo?
- Should agents authenticate through local tokens, GitHub identity, or
  workspace-scoped secrets?
- How much real-time coordination is required before a dashboard exists?
