# Native probe cloud validation

Cloud: `e28bc78d56d3:/workspace/CoProgrammer`, Linux; branch
`codex/codex-native-probe`; base
`6f6d948dcb2e5f7707c5f4a3f4476eff6ed9dcb0`.

- Existing four discovery-only tests still pass with no process, stdin,
  temporary state, workspace or Manager access.
- New 12 offline tests pass. Portable cases cover exact argv, independent
  version/help evidence, required-value declaration shapes, footer/body false
  positives, invalid/oversized/empty text, nonzero exits, unavailable executable,
  successful sampling followed by failed cleanup, and private exception context
  on interruption. POSIX fixtures execute real synthetic programs; Linux timeout
  and SIGINT cases verify owned child/grandchild shutdown and no later help after
  interruption. These are not AI quality or Windows native acceptance tests.
- Final focused harness/check suite: 30 passed, 0 failed, 0 skipped, 7.814s,
  with ResourceWarning treated as errors.
- Serial full unittest: 473 passed, 0 failed, 0 skipped, 67.777s. No heavy checks
  overlapped. Existing runner/watch/Manager tests are included once in this run.
- Config and all six implemented upgrade manifests passed. `git diff --check`
  and `git fsck --full` passed. JSON/YAML and final chain/bundle receipts carry
  the remaining syntax, preservation and artifact hashes.
- AST comparisons of execute and _json_loads against the base passed exactly
  (attributes excluded). Task argv, packet/result validation and model/account
  execution protocol were not modified.

During this round, cloud PATH discovery found a preinstalled ELF executable at
`/opt/codex/bin/codex`. The explicitly authorized local version/help probe ran
after full regression, with no task stdin. It reported `0.159.0-alpha.3`, version
exit 0 and exec-help exit 0; all four required flags were advertised. Sanitized
CLI report and zero-byte stderr are saved in private evidence. No native task,
login/config command, installation, account creation or model request was made.
Configuration/model/argument execution remain not_checked; native network
internals remain not_checked. This local snapshot is not a version pin or a
compatibility inference based on that version number.

Two agents reviewed parsing and cleanup read-only. Findings fixed before final
regression: a heading-free indented footer must not advertise a valued option;
private cleanup exceptions must not leak through a KeyboardInterrupt chain;
sampling success must not bypass failed cleanup. A wrong exec-help usage prefix
is also rejected. No Manager/security/protocol/profile changes were introduced.

The parsed stdout sample is bounded at 128,000 bytes; each command has five
seconds before timeout, plus the existing bounded cleanup. Temporary output is
not a hard disk quota or security sandbox. No automatic repair or retry occurs.
Ordinary --check still has its earlier zero-launch behavior and exit semantics;
only --check --probe-native opts into subprocesses. CLI misuse returns 2,
incomplete/unavailable returns 1, and interruption returns fixed stderr/130.

Windows native CLI behavior, real model/task acceptance, account authorization
and WorkBuddy GUI remain not run. Public push/PR/merge/release/deployment,
GitHub403 or Library retries, Air and other project data access did not occur.
Previous private artifacts and untracked source-handoff materials remain intact.

Actual benefit: detect a missing advertised adapter flag, bad CLI startup,
unexpected version/help output or timeout before risking a claimed task. Next
gap: help cannot prove argument values or structured real-task semantics, and
native Windows process cleanup still needs a separately authorized cloud check.
