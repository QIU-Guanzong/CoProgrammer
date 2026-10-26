# Interrupted setup recovery validation

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Cloud Linux, 2026-10-25. Base: `b80b52efb4056e69939937dce4414c5d08e133b8`.

Two new regressions failed against the unchanged baseline setup implementation
(0.019s): interrupted first installation retained its completed MCP file, and an
interrupted upgrade retained new config bytes with the old receipt. The latter
could prevent a subsequent differing upgrade from matching its recorded hash.

After the change, eight new tests passed (0.186s). They cover clean recovery for
new installation and upgrade, explicit later retry, independent replacement and
user edits, interruption after receipt publication, unreadable receipt state,
a second interrupt during rollback, and a real POSIX SIGINT delivered to an
offline Python CLI subprocess. The subprocess emits no success report, preserves
KeyboardInterrupt termination, restores the config/receipt pair, and permits a
subsequent explicit setup (including reacquiring the Manager lock).

`PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests
-p 'test_setup*.py' -v`: 46 passed in 0.673s.

Serial full discovery with ResourceWarning treated as an error: 552 passed in
60.059s, eight added beyond the preceding 544-test candidate. Configuration and
this manifest validate; 63 JSON and 10 YAML files parse. All 21 recorded evidence
hashes from the preceding setup-create candidate remain intact.

An offline wheel was built with no dependencies, index or build isolation and
installed into this task's local work directory. Running outside the source
checkout verified the imported setup module matches the source bytes; the same
eight new tests passed against that installed candidate in 0.200s. No public
package was released. Package version remains the unreleased candidate's
existing 0.3.0a7; the immutable source commit and wheel hash identify this build.

The patch adds KeyboardInterrupt to the existing application recovery path and
re-raises it afterward. Recovery is attempted only while the observed receipt
equals its pre-run bytes; changed or unreadable receipt state retains completed
writes for inspection. No new signal handler, receipt schema, automatic retry,
forced overwrite, client call or account change was added. Existing rollback
content/identity checks and their external-race limitations still apply.

SIGKILL, process crash, interrupted publication with unknown outcome, subsequent
external changes after observation, and a second interrupt are not guaranteed
to recover. Windows native signal behavior was not executed. This is best-effort
recovery for catchable cancellation, not a filesystem transaction or sandbox.

Remote read-only checks found main at d9e55083b506013f2c38380cb0d3f35a61e92a37,
PR11 open at 26d64273fcdac83441026ba1f06f66772d7a24ec and PR12 open/draft at
4cd839c31ab5b627c02fc254f3573698a18d14a7, still stacked on PR11. These refs were
not changed. No GitHub write, CI, merge or model call was attempted. This new
increment has local implementation/testing evidence; the previous candidate's
independent review is not claimed as review of this increment.
