# Collaboration upgrade verification

Verified locally on 2026-09-27. This report concerns the source-preview increment,
not a released package or live third-party model connection.

| Requirement | Evidence inspected | Result |
| --- | --- | --- |
| Research current collaboration approaches | [Primary-source comparison](research.md) of Agent Mail, agent-deck, Overstory, Claude Teams and existing gstack notes | Implemented choices and limits are documented; no market-size or productivity claims |
| Multiple windows, including the same brand | Session registration/duplicate/closure tests in `tests/test_collaboration.py` | Unique window IDs preserve separate client/provider/model/worktree/task fields |
| Cross-worktree, cross-client state | `tests/test_collaboration_processes.py` starts two independent stdio servers from generated Codex/Claude configurations | Shared Manager location; both branch names visible; no secondary worktree log |
| Durable task communication | Actual process handoff, receiver restart, pending inbox recovery, ACK and reply | Messages and receipt state survive restart; tools still answer ping afterward |
| Concurrent retries | Threaded and separate-process sends with the same request key | One stored message; conflicting content is rejected |
| Resumable synchronization | Event and inbox pagination tests; read-only repeated snapshots | No dropped events; pending messages remain after cursor advancement; unknown cursor fails |
| Truthful state and trust | Fresh/stale/future/closed pulse tests; recipient, task, worktree and malformed-history checks | No implicit ACK/pulse, process-liveness claim, identity certification or approval |
| CLI/MCP consistency | CLI sends read by MCP; both status interfaces expose the same directory | Passed, including Chinese message bodies |
| Existing behavior | Full source suite | **185 tests passed** |
| Installability | Built `coprogrammer-0.2.0a1-py3-none-any.whl`, installed into a temporary virtual environment, ran all tests from outside the source checkout | **185 tests passed**, including actual stdio processes using the installed package |
| Artifact correctness | Configuration/manifest validation, repository JSON parsing, Draft 2020-12 schema check against emitted lifecycle events, Active Sync skill validator, local documentation links and diff whitespace | Passed |

The temporary validation environment installed JSON Schema/YAML validation tools;
they are not new CoProgrammer runtime dependencies. No persistent client settings,
provider credentials, model requests, package release or merge were involved.

GitHub CI on the draft PR is the authoritative remote-platform result. Its
existing matrix tests Ubuntu and Windows with Python 3.10 and 3.13 and builds
the wheel. Client GUI installation and live provider authentication remain
outside this validation; the two-client test uses protocol clients.

The additive Manager event enum requires maintainer contract review before
merge. Older strict enum validators must be updated before consuming the new
event types. See [task brief](task-brief.md) and [change manifest](change-manifest.json).
