# New setup file publication validation

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base: `9bc02a17458f70f7da456ec0589e3c1b9e60735c`; cloud Linux, 2026-10-24.

The corrected baseline reproduction executes that commit's original setup
module against the same new regressions: two tests fail with three assertions
(partial MCP file, partial receipt, and identical-content replacement deleted
during rollback). An initial fixture used an instruction path excluded by the
MCP-only edition; its log is retained separately and is not product evidence.
The corrected baseline failures took 0.016 seconds; both tests pass after the fix.

Eight tests were added for partial writes, full-byte publication and original
creation mode, competing destination creation, fsync failure, unsupported links,
identical-content replacements, in-place user edits, and temporary-name collision.
The existing late-failure rollback test now injects failure at publication rather
than the former direct destination open. All 38 setup tests passed in 0.604 seconds.
Serial full unittest with ResourceWarning treated as an error passed all 544
tests in 57.889 seconds: eight new tests beyond the prior 536-test candidate.
`git diff --check` passed.

Configuration and the new manifest validate. 62 JSON and 10 YAML files parse.
Six original private failure-evidence hashes remain intact. No protected schema,
protocol, workflow, generated Skill content, account or global permission changed.

The new-file path stages complete bytes, flushes/fsyncs and publishes with a
same-directory no-replace hard link. Original exclusive-creation mode/umask is
retained. A confirmed publication records local file identity; rollback requires
matching identity and bytes. Unconfirmed creation cannot authorize deletion.
Existing-file updates retain their original behavior.

Limitations: hard-link support is required for new files, with no unsafe fallback.
Windows execution was not performed here. Temporary cleanup and rollback still
use observed path identity; arbitrary writes after observation are not excluded.
Multi-file application is not atomic, directory durability across power loss is
not guaranteed, and a crash/uncertain publication can leave files for inspection.
This does not mediate native coding-agent writes or establish a sandbox.

Rollback of the code is a revert of this local increment; receipt format and
persisted state have not changed. Do not automatically remove recovery artifacts
or replay failed setup operations. No push, merge, CI, real model call or package
release is part of this work. Independent technical review is tracked separately
against the resulting immutable local commit, not treated as maintainer approval.
