# Preserve interruption through temporary cleanup failure

Frozen parent: `c67b580842a7d38d6538ee7fc6233f9b82316b1b`.

Reproduce actual CLI SIGINT followed by temporary cleanup OSError. Verify the
exit semantics, original exception and retained staging/recovery evidence. Fix
only the two staged setup write helpers if cleanup currently masks interruption.
The original KeyboardInterrupt must remain primary, cleanup error remain in its
chain, conditional application recovery stay active, and no operation retry or
forced removal be added. Preserve ordinary cleanup-failure behavior and second
interrupt behavior. Test creation, update and the actual offline CLI subprocess.

Separately assess the already observed publication-to-bookkeeping window. Do
not preclaim ownership of an unconfirmed publication or broaden deletion rules
merely to make that probe pass. Record what can and cannot be safely narrowed
within current semantics; no installer rewrite or persistent journal.

Allowed: setup.py, test_setup_cleanup_interruption.py, installation maintenance
guide and this upgrade directory. Preserve other commits, source artifacts and
Library packages. No schemas/protocols/workflows, global signal handling,
permissions, accounts, model execution, GitHub writes or process-management
changes. Focused failures must precede the fix; run appropriate serial regression
and config/manifest checks after a runtime change. Windows remains unverified.
