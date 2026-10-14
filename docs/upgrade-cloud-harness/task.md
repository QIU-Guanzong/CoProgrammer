# Codex CLI task adapter

Baseline: d9e55083b506013f2c38380cb0d3f35a61e92a37.

Problem: worker run/watch accept a JSON harness but the installed package only
contains a deterministic fixture. Add one opt-in Codex CLI task adapter, using
the existing harness result contract. Do not change Manager ownership, message
receipts, provider configuration, schemas, approval policies or publishing.

Scope: one packaged Python module, focused process tests and usage documentation.
The adapter must require explicit execution, retain read-only as the default,
use trusted argv without a shell, discard native diagnostics, bound final output,
and never retry. Inbox handling remains in the existing client/MCP workflow.

Acceptance: a fake native CLI executes through the actual worker runner, edits
only the claimed scope and returns structured completion; preview never launches;
unavailable/failed/invalid clients retain claims; no raw native output escapes.
Run focused adapter/runner tests, all unittest tests and config/manifest validation.
Fake clients establish transport behavior only, never autonomous model quality.

Cloud constraint: Codex, Claude and OpenClaw executables were absent from PATH.
No accounts, credentials, global profiles or paid model calls are created.
