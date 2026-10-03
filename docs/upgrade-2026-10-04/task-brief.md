# v0.3: workspace-aware coordination

Baseline: `ef81bcbe1072444f9bbc94822251614621471f4c` (`origin/main`).

The old upgrade branch's ten commits were squash-merged in PR #1. They are
already present in main; do not reapply the branch or downgrade its newer code.

## Outcome

- Preview dispatch for the actual session, client, branch and worktree.
- Record explicit local checks against the complete supported working content;
  detect stale results after edits, failed commands and changes during a check.
- Export a bounded task handoff and compare it in another clone, including
  package version, repository identity, HEAD, base and working content.
- Provide the same read operations over CLI and MCP, and update packaged Skills
  and Markdown guidance. No Manager event/schema changes.

## Scope and validation

Allowed: new workspace/evidence/workflow modules and tests; CLI/MCP adapters;
release metadata; plugin Skills and matching wheel assets; English/Chinese
entrypoints; these release artifacts. Existing provider transports, global
client configuration, schemas, protocols and release workflows stay outside
this increment.

Run focused tests, full source and independent-wheel tests, config/manifest/plan
validation, JSON/YAML parsing, a two-clone handoff and a real stdio MCP journey.
Use existing PR CI and tag publication after verification.

## Limits

Dispatch is a preview; atomic claim remains authoritative. Local check records
are not authenticated reviews. Content fingerprints exclude ignored files and
external dependencies. Handoffs compare context; independent computers still
have independent Managers and must reconcile ownership before taking over.
Do not copy Manager logs, claim tokens, credentials or absolute machine paths.
