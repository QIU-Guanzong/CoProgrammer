# Stage new installer files before exclusive publication

Base: `9bc02a17458f70f7da456ec0589e3c1b9e60735c`.

The installer owns creation of generated project files and its setup receipt.
Direct `xb` writes prevent initial name collisions but can leave a partial final
file on write failure. Rollback currently compares bytes alone and can remove a
different file that another writer replaced with identical content.

First reproduce those two cases. Stage complete new-file bytes beside the target,
flush/fsync, then publish with an atomic no-replace hard link. Record the created
file identity only after confirmed publication. Rollback deletion must observe
both that identity and unchanged bytes, preserving independently replaced files.
Unsupported publication fails without an overwriting fallback. Keep existing
content, receipt format, CLI/defaults and permission/umask behavior unchanged.

Scope is installer-owned new files only, including a newly created receipt.
Existing-file upgrades remain on their current compare-and-replace path. This
does not constrain arbitrary native model writes or external editors; identity
checks are observations, not an atomic conditional unlink or OS sandbox. Retain
recoverable files on uncertain ownership and do not automatically retry failures.

Acceptance: partial-write/fsync failure, destination creation during staging,
identical-content replacement before rollback, ordinary rollback of owned files,
successful full publication, unchanged permissions and unsupported hard links.
Run focused and serial full regression, configuration, manifest and syntax checks.
Deliver one local commit/patch, then request independent technical review against
the immutable commit. No public write, merge, CI, account or permission change.
