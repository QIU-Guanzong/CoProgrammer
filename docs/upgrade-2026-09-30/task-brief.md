# Research-led onboarding and coordination upgrade

Date: 2026-09-30

## Problem

The source preview has useful coordination primitives but requires many commands
to understand current work. New users cannot exercise the complete workflow
without preparing worktrees and sessions. Status reads replay collaboration
history more than once. The GitHub default branch also predates the upgrade.

## Expected outcome

- Source-backed comparison of adjacent projects, including their current status.
- A real, isolated, offline two-worktree demo, callable from one CLI command.
- A bounded CLI/MCP briefing of readiness, blockers and recommended next steps.
- Less repeated event replay, preserving validation and atomic transactions.
- English and Chinese entrypoints and accurate GitHub About/topics/homepage.

## Allowed paths

Assigned leases cover new demo and briefing modules/tests; collaboration and
scheduler internals; CLI/MCP command registration; README files; research and
upgrade documentation. Each worker records its own heartbeat and lease.

## Forbidden paths

Do not change existing event schemas, protocols, credentials, global client
configuration, dependency versions or production systems. Do not auto-approve
protected contracts or merge the existing draft PR.

## Shared contracts

Additive `demo`, `manager briefing` and `manager_briefing` entrypoints. Existing
commands, events and MCP outputs remain compatible. Briefing is advisory and
does not approve work, claim tasks, acknowledge messages or reclaim leases.
Demo session labels do not mean live Codex/Claude client connections.

## Validation

Run focused regressions and the full unittest suite, config/manifest validation,
JSON/YAML and documentation-link checks, a fresh wheel installation and real
demo/stdio MCP smoke checks. Measure replay optimization on a reproducible
synthetic history; timing is evidence about that workload only. Push the
reviewable branch and read back its exact-head CI and GitHub metadata.

## Handoff

Keep the existing PR #1 review boundary. Link the source-preview branch from
the repository About homepage so visitors can find the current implementation.
Metadata changes improve discoverability; they are not evidence of more views.
