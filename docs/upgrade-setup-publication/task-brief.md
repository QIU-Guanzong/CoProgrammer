# Record confirmed setup replacements before helper return

Base: `c887fdf6f67fab5f046f2d004fb262fccfd89e18`.

An interrupted upgrade can return from its write helper before the caller records
the completed replacement. Narrow that window by recording confirmed publication
inside the helper. Do not register writes before publication or infer ownership
from matching content after a failed publication. Retain staging-file identity
for updates so recovery can preserve same-content foreign replacements, including
replacement while a rollback file is being staged.

Acceptance: synthetic failures immediately after helper return restore the old
file/receipt pair; competitor changes before publication and after publication
survive; actual CLI SIGINT keeps interruption exit semantics and releases its
Manager lock. Keep receipt changed/unreadable behavior, no automatic retry, and
the existing creation path. The syscall-to-Python-record gap remains: failure
inside the publishing primitive has no confirmed ownership and must retain the
files for inspection. No global signal masks, durable journal, schema changes,
account/model calls or GitHub writes.

Integration: preserve the existing PR11 -> PR12 dependency. Current remote main
and PR heads must be rechecked; package the cumulative local increment relative
to the exact PR12 tree plus a separate c887 delta. Existing merge auto-review
rejection is not bypassed; mergeable metadata is not approval. Run focused,
setup, installed CLI and serial full validation, then independent technical
review of the immutable candidate. Previous results remain historical.
