# Recheck protected content immediately before launch

Base: `f33190e67196f8e2a511043ad769ac341bc4d3cc`.

Reduce the known observation-to-execution window for opt-in protected retries.
The first snapshot precedes durable start-record persistence and output-file
setup. An external edit during those controlled operations currently reaches
the child unchanged by any further guard. Add one existing bounded snapshot
after setup and before Popen, comparing it with the recorded start digest.

On mismatch, report no child launched, retain the original claim/edits and the
durable incomplete start record, and never accept changed content as a new end
baseline. A snapshot error likewise stops before launch. Do not automatically
recover, replay or release that claim. Preserve legacy behavior without the flag.

First demonstrate failures using deterministic injected writes during record
persistence and output-file setup, then prove the local fix with actual synthetic
Python children. Test snapshot errors and unchanged legacy behavior. Re-run
focused/full offline checks serially, configuration, manifest and JSON/YAML.

This adds one double-pass snapshot (two content scans) only in protected mode.
It narrows a window; it does not lock arbitrary editors, guard ignored inputs,
or eliminate edits after the final observation. No new protocol, event kind,
sandbox, model/account action or atomic filesystem scheme is introduced. Retain
the previous audit's explicit limitation test. No remote writes, PR edits or CI.

Rollback: revert this local increment. Persisted record format is unchanged;
incomplete runs still require manual inspection and are not automatically cleared.
