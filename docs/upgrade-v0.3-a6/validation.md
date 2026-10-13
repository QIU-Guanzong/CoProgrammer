# Validation scope

Focused setup regressions cover explicit preview/application, exact-hash
ownership, preserved instructions, customized/unrecorded conflicts, adoption of
identical legacy files, selective and shared-client updates, malformed/oversized
receipts, linked/reparse paths, conditional rollback, concurrent installers and
real Git worktree receipt isolation. Existing setup and expanded-client checks
remain required.

Release gates: full source and independently installed-wheel test suites;
configuration, changed JSON and Markdown link validation; PR and main Linux /
Windows CI; merged-tree equality; existing PyPI workflow; metadata/hash readback
and fresh published installation. A fresh second Python environment must refresh
the recorded MCP launcher and successfully rediscover tools/resources. A legacy
install must preserve customization rather than treating it as owned.

Local check artifacts are stored under `.coprogrammer/checks/` and are excluded
from source. Published-package receipts remain local. Connection verification
distinguishes transport/native discovery from model access. This release does
not re-run WorkBuddy GUI tests or claim autonomous model work, multi-file
filesystem transactions, cross-machine leases, adoption or productivity gains.
