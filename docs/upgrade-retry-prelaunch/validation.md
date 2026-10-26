# Protected retry prelaunch recheck

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Cloud Linux, 2026-10-24. Base:
`f33190e67196f8e2a511043ad769ac341bc4d3cc`.

Two deterministic regression tests failed on the original runtime (2 failures
in 0.825 seconds): edits injected after start-record persistence or during output
storage setup did not stop the child. The same tests pass with the new prelaunch
snapshot. They exercise real synthetic Python child commands, not model clients.

Four tests are added in this increment:

- During start-record persistence: stop with `retry_prelaunch_content_changed`,
  `launched=false`; keep the new file content, claim and prior records. A further
  explicit protected attempt stops on the incomplete marker rather than
  overwriting or adopting a new baseline.
- During output setup: stop before child startup, preserve new content and close
  the output temporary file; retain the durable incomplete record.
- Prelaunch observation error: no child starts; retain incomplete evidence and
  refuse an automatic recovery baseline.
- Legacy execution: complete without calling the opt-in prelaunch check.

The 26-test retry suite passed in 9.592 seconds. Existing tests still cover
unchanged retry completion, expiration, cancellation, record-write failure,
preview/apply separation and completion/notification deduplication. The prior
post-check external-write characterization still passes: writes after the final
check can still be overwritten. The ignored-file limitation is also retained.

Serial full regression with ResourceWarning treated as an error passed all
536 tests in 55.828 seconds. This is four newly added tests beyond the prior
532-test candidate, not a claim of 536 new tests. `git diff --check` passed.

## Cost, compatibility and recovery

Only `--protect-retry` adds the extra snapshot. It reuses existing size/file limits
and double observation, increasing normally returning protected invocations from
four to six content scans. This is 50% more content passes, not a measured 50%
runtime increase. No benchmark or global atomicity guarantee is claimed.

There are no new persisted event fields/kinds, schema changes, permissions,
filesystem sandbox, editor lock or automatic retries. The new fixed stop reason
describes an invocation that did not launch. Retained start records remain
incomplete deliberately: preserving an uncertain attempt is preferable to
silently accepting newer content. Inspect the claim/files before an explicit
recovery decision. Reverting this increment restores prior execution behavior
without migrating records; it does not clear existing incomplete attempts.

Configuration and the new manifest validate. 61 JSON and 10 YAML files parse;
canonical/bundled foreground guides match. Six original private evidence files
retain their recorded hashes. Protected schemas/protocols/workflows are unchanged.
No real model call, account change, PR mutation, push, merge or CI trigger was
performed. All process tests are offline; Windows execution was not run here.
