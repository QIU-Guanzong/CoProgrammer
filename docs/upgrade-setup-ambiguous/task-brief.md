# Preserve ambiguous setup recovery states

Base: d97d06bbf8fee5e029950426a215b38bc67221fb.

Reproduce two concrete remaining boundaries before modifying runtime code:
receipt publication that succeeds but raises OSError/RuntimeError before returning,
and a confirmed output subsequently relinked through a surviving hard-link alias.
Recovery must not roll files back under a newly published or unreadable receipt,
nor unlink/replace a recovery target with observed multiple links. Retain original
failure evidence, avoid retry, and keep ordinary single-link rollback behavior.

Extend existing checks locally; do not invent ownership for an unconfirmed syscall,
add persistent journals, mask signals, change permissions, or change public schemas.
Check link count again after rollback staging. A link added after the final check
or created then removed before observation cannot be distinguished and remains
outside the guarantee. Preserve files for inspection in ambiguous cases.

Acceptance: synthetic create/update failures, ordinary unchanged-receipt rollback,
late hard links, unknown receipt, and actual CLI SIGINT on a relinked target.
Run focused tests, setup tests, serial full regression and offline installed CLI;
independently review the frozen candidate. Retain old candidates and Library files.
Integrate only atop the existing PR11 -> PR12 tree sequence; no remote merge retry
or identity/permission changes in this work. Windows native signals remain unverified.
