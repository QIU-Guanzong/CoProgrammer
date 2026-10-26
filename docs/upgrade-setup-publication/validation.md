# Publication recording validation — 2026-10-26

> Historical implementation checkpoint. Test counts and remote/action status below
> describe that batch, not current integration status. See
> [the cumulative integration record](../upgrade-reliability-integration/validation.md)
> for the reviewed publication baseline and remaining limits.

Base: `c887fdf6f67fab5f046f2d004fb262fccfd89e18`. Existing cloud Linux
checkout reused; tracked source was clean and Manager had no active leases,
open decisions or contract changes. Earlier untracked materials were retained.

Fresh baseline checks on c887: eight setup interruption and seven cleanup
interruption tests passed (0.244s and 0.213s). These are this round's reruns,
not a restatement of the earlier 559-test acceptance.

Seven new synthetic publication tests were written before runtime changes.
An initial fixture incorrectly used its patched Python path to start a child;
that fixture error was corrected before the accepted baseline run. The corrected
baseline had five failures and zero errors in 0.209s: helper-return interruption
and I/O failure left an inconsistent old receipt/new file pair, same-content
foreign replacements were rolled back, and the actual CLI boundary did not
restore the old pair. The two cases refusing unconfirmed ownership already
passed and remain deliberate limits.

The helper now records successful update publication before returning and saves
the staged inode identity. Conditional recovery checks identity plus content,
then checks identity again after staging rollback. No write is registered before
the publishing primitive returns successfully. Receipt publication still uses
the existing changed/unreadable receipt guard. Creation behavior is unchanged.

Final checks with ResourceWarning treated as an error:

- Seven focused tests passed in 0.188s.
- All 60 setup tests passed in 1.073s.
- Serial full unittest: 566 tests passed in 60.986s.
- An offline wheel was built and installed into a separate task directory;
  from outside the checkout its setup bytes matched source and the same seven
  tests passed, including actual CLI SIGINT and subsequent explicit retry.
- Config, this change manifest and diff whitespace checks passed.

Independent review and exact final commit/tree/patch/wheel hashes belong to the
private handoff receipt produced after this commit. No published-package or
maintainer-approval claim is made.

## Integration and remaining limits

Read-only GitHub checks found main unchanged at
`d9e55083b506013f2c38380cb0d3f35a61e92a37`; PR11 remains open at
`26d64273fcdac83441026ba1f06f66772d7a24ec`. PR12 remains a stacked draft at
`4cd839c31ab5b627c02fc254f3573698a18d14a7`, parent PR11, tree
`02855b6a1e03562585d6a992aaab751f0c754960`. That tree exactly matches local
`edb13745db5496df7402bb94d7408489312c9567`, the cumulative handoff patch base.
Both PRs report mergeable, but combined status is pending with no status entries
and the submitted-review lists are empty. Neither field establishes approval.
The prior platform merge rejection remains; no new merge/write attempt was made.
Integrate PR11 then PR12 under normal approval rules before this cumulative
increment; preserve the original branches and evidence. Refresh this assessment
if remote heads change. Do not apply the increment directly to old main.

The syscall-to-record interruption gap remains: the publication primitive may
have written but not returned confirmation. Such output is retained for manual
inspection. Identity/content checks are not filesystem compare-and-swap or a
lock on editors; same-inode hard links and writes after the final check remain
outside coverage. No extra hashing or full-tree scan was added; only per-file
fstat/lstat bookkeeping. Unsupported hard-link filesystems and Windows native
signals retain prior limits. No accounts/models, global signal handling,
GitHub writes, CI or package publication occurred. Roll back this local change
by reverting its single commit; existing setup receipt format is unchanged.
