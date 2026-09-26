# Cross-window collaboration upgrade

## Problem and outcome

Independent coding windows already share leases and review artifacts, but cannot
discover sessions, exchange task-scoped messages, acknowledge handoffs or resume
an incremental sync after restarting a client. Add these operations to the shared
local Manager store and expose identical behavior through CLI and MCP.

## Scope

Allowed: a focused coordination module, CLI/MCP adapters, Manager event
validation, additive event schema entries, behavioral tests, README,
`docs/collaboration/**` and the packaged Active Sync skill. Existing Manager logs
remain readable.

Excluded: launching or controlling terminals, model requests, network messaging,
hosted authentication, dependency upgrades, automatic integration/merges and
global client configuration. The previous packaging task is complete; this is a
new runtime feature increment under the user's broader upgrade request.

## Contracts and review

Sessions identify windows independently of client/provider/model. Messages are
untrusted local coordination data, with recipient acknowledgements distinct from
approval. Session freshness reports age of explicit pulses, not process liveness.
Additive event types and MCP tools require maintainer contract review before
merge; this implementation does not record or imply that approval.

## Acceptance evidence

- Two sessions in linked Git worktrees share state through separate MCP processes.
- Registration cannot silently replace another window; closed sessions stay closed.
- Messages survive restart; duplicate request keys do not duplicate messages;
  mismatched retries and incorrect recipients fail without writes.
- Sync cursors paginate without dropping events; unread messages remain until
  explicitly acknowledged; stale sessions remain visibly stale.
- CLI and MCP reject malformed requests and preserve existing logs.
- Full tests, config/manifest/schema validation, installed-wheel smoke test and
  GitHub CI pass. README provides executable English/Chinese examples and
  states the local, cooperative, polling-based boundary.

## Handoff

Update the existing draft PR with code, research sources, validation and limits.
No release or merge is included in this increment.
