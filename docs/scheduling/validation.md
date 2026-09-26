# Scheduling verification

Local verification date: 2026-09-27. This increment targets the existing
`0.2.0a1` source preview and draft PR #1.

| Area | Behavioral evidence |
| --- | --- |
| Atomic ownership | Concurrent independent MCP processes claim one task once; one corresponding path lease remains |
| Conflict prevention | Overlapping scopes, same worktree, wrong client, unfinished dependency and stale session are rejected |
| Claim validity | Wrong token/worktree/branch, detached HEAD and expired/missing lease fail; invalid operations preserve event bytes |
| Recovery | Explicit creator reclaim after lease loss; old tokens cannot resume; completion/release relinquishes the task lease |
| Concrete paths | Planned-path scope, symlink escape, actual Git rename source/destination, Unicode filenames and literal-backslash ambiguity checks |
| Communication | Task/message changes wake a bounded wait without blocking another process; pending messages and sent/received/ACK history remain available |
| Nested mutations | Pending registrations, pulses, keyed sends and duplicate ACKs are visible inside one transaction; failed duplicates roll back |
| Forecast | Existing overlapping leases with the same holder label remain visible |

Focused evidence lives in `tests/test_scheduler.py`, `tests/test_channels.py`,
`tests/test_scheduling_integration.py`, `tests/test_collaboration.py` and
`tests/test_cli.py`. The seven scheduling process tests use generated client
configurations and actual Git worktrees, not live model sessions.

The final source suite passed **228 tests**. A fresh wheel installed into an
isolated virtual environment outside the source checkout also passed **228
tests**, including the independent MCP processes and literal-path regression.
Configuration and change manifests, repository JSON/YAML, Draft 2020-12 schemas
against emitted task/session/message events, Active Sync skill metadata,
documentation links and diff whitespace checks passed. JSON Schema/YAML tools
were installed only into a temporary validation environment.

Remote Ubuntu/Windows Python 3.10/3.13 results are shown in the draft PR's Checks
on its current head. Windows skips the POSIX-only literal-backslash filename
case because that filename is not permitted there; canonical slash handling
and rejection of backslash guard input are tested on all platforms.

No GUI client installation, model authentication, native idle-session wakeup,
cross-machine delivery, package release or merge is established by these tests.
Guard checks remain cooperative, not filesystem enforcement. Shared event
contract additions require maintainer review; old strict enum consumers must
update before reading task lifecycle events. No runtime dependency was added.
