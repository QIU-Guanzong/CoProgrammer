# MVP Design

## Current product requirements and CLI design

This section records the implemented a8 baseline and the local onboarding-guidance
candidate. The original Branch Digest Bot proposal remains below as historical
scope, not a list of unimplemented current features.

Sources: the 2026-10-27 maintenance request to make CLI results and installation
instructions clearer; [two-window workflow](GETTING_STARTED.md),
[installation maintenance](INSTALLATION_MAINTENANCE.md), and the source paths below.
The broader [architecture](ARCHITECTURE.md) and [localization rules](LOCALIZATION.md)
remain the design references. The applicable public references and their limited
use in this CLI are recorded in [wording sources](LOCALIZATION.md#public-references-and-review).

### Product surfaces and ownership

| Surface | Current implementation | Contract / acceptance boundary |
| --- | --- | --- |
| User-facing interface | Terminal `start`, `status`, `setup`, `worker`; `src/coprogrammer/onboarding.py`, `setup.py`, `worker_cli.py` | Human text explains the operation result, actual blockers and a valid next step. This is a CLI, not a browser frontend. |
| Background coordination | `manager_store.py`, `collaboration.py`, `scheduler.py`, `worker.py` | Local events and transactions coordinate tasks, leases, sessions and explicit message receipts. A foreground watcher is bounded; there is no new hosted admin console or daemon in this scope. |
| Client API | `mcp_server.py`, `workflow_mcp.py`, `collaboration_mcp.py`, `worker_cli.py` declarations | MCP stdio tools reuse local operations. Tool discovery and generated configuration do not prove a client connection. |
| Data returned to scripts | `coprogrammer.start.v1`, `coprogrammer.status.v1`, `coprogrammer.setup.v1` reports | Human wording can change without changing JSON keys, reason codes, mutation rules or exit codes. Scripts should consume `--json`, not screen text. |
| Installed guidance | `knowledge.py`, `src/coprogrammer/assets/skills/`, `assets/templates/` | Resources must remain readable after package installation without a source checkout. Source/plugin copies must be synchronized when those resources change. |
| Native coding clients | `codex_harness.py`, `claude_harness.py`, parent `runner.py` | Execution is explicit; task-only adapters do not ACK inboxes. Client/provider labels are not model connectivity evidence. |

### Audited user flow: preview → install/register → inspect

1. In a committed Git checkout on a named branch, preview
   `start --client claude --session docs-window --apply-setup --dry-run`.
   Result: a plan, no new registration or installed files. The next step is to
   review the plan and rerun that same command without `--dry-run`.
2. Run the reviewed command. If project setup conflicts, registration/resume is
   blocked; report the conflicting paths without exposing their contents.
   Recommend `setup --client claude --upgrade --include-content` for inspection,
   not a status lookup for a window that may not exist.
3. On success, distinguish installed files from the pre-application plan. Report
   registration/resume and setup as separate outcomes, then recommend
   `status --session docs-window`. Reload/trust the native client through its own
   normal workflow. CoProgrammer has not launched or connected a model.
4. Use status to inspect work and messages. A status read does not refresh a
   window, claim work or acknowledge a message. Task creation/claim, completion
   and recipient acknowledgement remain separate explicit actions.

`start` without `--apply-setup` registers/previews only. Existing sessions require
`--resume`; setup and registration are separate operations, so a registration
failure after installation can leave files requiring inspection. The renderer
must not invent an atomic whole-operation guarantee.

### Requirements, status and acceptance

| ID | Confirmed requirement | Status and evidence | Acceptance |
| --- | --- | --- | --- |
| UX-1 | Successful setup must not be described as still missing | Local candidate: `onboarding.render_start` distinguishes applied setup from its plan | Real-checkout CLI test applies setup, verifies files exist, and follows the recommended status command successfully. |
| UX-2 | Preview and blocked operations need an actionable next step | Local candidate: conflict paths, plan inspection and explicit rerun guidance | Dry-run leaves files/state unchanged; blocked registration and resume preserve events and private contents; no status command for an unregistered window. |
| UX-3 | Installation documentation must match optional start behavior | Local candidate: `GETTING_STARTED.md` describes `--apply-setup` | Examples retain preview first; default registration-only behavior remains documented. |
| DATA-1 | Human wording changes must not alter automation contracts | Existing report construction, CLI exit handling and MCP operations retained | `tests/test_onboarding.py` and `tests/test_foreground_automation.py` exercise JSON/state and human CLI paths. |
| MSG-1 | Reading or displaying a message is not receipt or approval | Implemented explicit receipts; `collaboration.py`, `worker.py`; existing two-window onboarding regression | Pending message count remains until explicit ACK; status does not expose message bodies/claim tokens. No new auto-ACK behavior. |
| PKG-1 | Published wheel and sdist must install with complete resources | a8 official distributions independently verified in cloud Linux on 2026-10-27 | Public wheel installed; official sdist built with isolated backend and installed in a separate fresh environment. Package resources matched source. These checks are historical evidence, not new tests for this text change. |
| NATIVE-1 | Describe only connectivity actually verified | Native/model acceptance remains incomplete | Keep discovery, authorized account configuration and successful model task/receipt evidence separate. Mac native installation, real provider collaboration and WorkBuddy GUI are not claimed here. |

Tests for this local candidate live in `tests/test_onboarding.py` (three
`test_start_guidance_*` regressions). The task manifest and validation record are
in [upgrade-onboarding-guidance](upgrade-onboarding-guidance/task.md). Release
and merge state must be reported separately from local test success.

### Scope kept outside this patch

No web UI/admin backend, new HTTP API, hosted account management, automatic model
routing, protocol/schema changes, default retry changes or message rewriting.
The current `status` renderer still has its legacy product heading; this candidate
changes only the `start` renderer, not every output surface. Full multilingual CLI
output is not implemented: digest localization supports
English/Simplified Chinese; current start/status text remains English. Preserve
actual Unicode names rather than assuming a language from a client/provider.

## Original Branch Digest Bot proposal

## MVP Name

Branch Digest Bot

## Primary User

A reviewer who receives a large AI-generated feature branch and needs to decide
what is worth integrating into main.

## User Story

As a reviewer, I want an AI-assisted branch digest so that I can evaluate
intent, risk, and integration strategy without reading every noisy generated
change first.

## Scope

This MVP is the first PR-facing slice of the broader lifecycle described in
`docs/COORDINATION_LIFECYCLE.md`. It should connect backward to project
covenants and Manager Plane telemetry, and forward to integration plans and
integration records.

The MVP should:

- read changed files and commits;
- detect contract-sensitive paths;
- load project policy from `.coprogrammer.json`;
- score branch risk;
- generate a digest draft;
- publish the digest as a PR artifact and stable PR comment;
- require humans to fill in branch intent and integration decisions;
- run as a local CLI and later as GitHub Actions.

The MVP should not:

- auto-merge;
- rewrite code autonomously;
- replace CI;
- approve protected file changes without owners.

## CLI Commands

```bash
coprogrammer digest --base origin/main --head HEAD
coprogrammer digest --base origin/main --head HEAD --language zh-CN
coprogrammer digest --base origin/main --working-tree
coprogrammer config validate
coprogrammer manifest validate path/to/change-manifest.json
coprogrammer heartbeat new --agent agent-a --task "Implement backend API"
```

## Future Bot Flow

1. On PR open, run digest.
2. Comment digest on PR.
3. Fail soft if protected paths are touched without manifest.
4. Fail hard when schema or migration changes lack owner review.
5. After approval, optionally create an integration branch.
