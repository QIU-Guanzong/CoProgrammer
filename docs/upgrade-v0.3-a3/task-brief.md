# Local worker cycle and installation editions

Request: after publishing a2, connect Codex/Claude and GLM/DeepSeek-backed windows,
reduce manual scheduling/conflict/inbox work, and provide Skill/MCP variants.
Baseline: published a2 main 6e596c6ad9b12da037c94029be5666015744f7b4.

Implement additive worker step/finish CLI and MCP wrappers over the existing
transaction, session, claim, guard, renewal and message APIs. Preserve event
formats. Preview is read-only; applying a step records activity, handles owned
work or claims eligible work atomically. Pending inbox and open decisions stop
new claims. Completion can notify explicitly selected local recipients and be
retried without duplicate records. No automatic ACK, model process, provider
request, unguarded takeover or cross-clone ownership.

Client identifies the coding host; provider/model are declared routing labels.
Use existing client filters for client or provider labels consistently in dispatch
and claims. Add full, Skill and MCP setup editions, retaining missing-file-only
writes, conflict checks, existing instructions and native trust flows.

Validate real worktrees, concurrent step races, transactional rollback, stale/
expired/moved ownership, provider routing, inbox privacy, notification retries,
all setup editions, installed-wheel behavior and real stdio MCP calls. Complete
source/wheel and Ubuntu/Windows CI before merge and publication.
