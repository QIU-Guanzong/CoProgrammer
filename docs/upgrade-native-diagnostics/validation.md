# Local diagnostic validation

Validation on cloud Linux, 2026-10-23, based on
`9ee26c90a31afaa55b7ef39b603fbb47052f519a`:

- Reproduced the baseline stdin OSError defect with a fully mocked native call,
  both with and without execution diagnostics. These are expected baseline
  failures, not failures of the candidate.
- Seven new synthetic regression tests cover invalid JSON/UTF-8/duplicate fields,
  oversized input, stdin I/O, packet/sandbox rejection, allowlisted process I/O
  codes, temporary storage failure and result-read failure.
- Codex focused suite: 28 passed in 5.252 seconds.
- Serial full unittest: 510 passed in 50.805 seconds, zero failures/skips,
  with ResourceWarning promoted to an error. These are this candidate's results;
  the previous 503 tests and two private follow-up checks are historical evidence.
- Config and new manifest validation passed. All 58 tracked/candidate JSON and
  10 YAML files parsed. Canonical and bundled Codex guides match byte for byte.
- Original private failure evidence and fixture event-log hashes remain intact.
  Existing synthetic native process tests exercised the runner; this round made
  no real model request and did not replay any failed claim.

The additional `os_error` field is a local operator diagnostic, not an account,
quota, network or model-error classifier. Unrecognized codes remain `unknown`;
an OSError around subprocess I/O still leaves native startup unknown. Native
stdout/stderr remain discarded. Earlier unclassified native exit evidence
cannot be retroactively explained by these changes.

Recovery instructions require manual inspection of the original worker report,
task board and edits. No new retry, ACK, lease takeover or completion behavior is
introduced. No schema/protocol/workflow, native argv, provider/account settings,
package version or Skill is changed. At this validation checkpoint the candidate
was local only; no remote branch/PR/CI run, package build/release or real-client
acceptance was claimed. Later publication requires a separate remote receipt.
