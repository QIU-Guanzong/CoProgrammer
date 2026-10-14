# Explicit native version and help diagnostics

Base: `6f6d948dcb2e5f7707c5f4a3f4476eff6ed9dcb0`. Use only cloud
`e28bc78d56d3:/workspace/CoProgrammer`, branch `codex/codex-native-probe`.
Preserve all private commits, receipts, bundles and original untracked materials.
No delivery retry, paid model call, account/config write, automatic install or
other project access.

Existing coverage: four tests prove discovery-only --check does not read task
stdin, launch a client, touch Manager/workspace or create temporary state. The
14 execution adapter tests cover the existing task/result transport and cleanup.
The adapter actually invokes exec with --ephemeral, --sandbox, --output-schema
and --output-last-message, plus a stdin prompt. Version is currently not checked.

Scope before implementation: retain ordinary --check exactly. Add the explicit
--probe-native option only alongside --check. Discover once, then run that trusted
resolved executable with --version and exec --help, serially, at most once each.
Use DEVNULL stdin/stderr, a bounded parsed output sample, five seconds per command,
and existing runner helpers to clean only each probe's new owned process group.
No task execution, login/config/provider/sandbox-policy command or repair.

Return a limited version token and optional native_probe observations in the
existing check report. Help options must be actual option rows rather than body
mentions. Advertised required flags are evidence only about help; argument values,
execution semantics, native configuration and model access remain unverified.
Never infer capability from a version threshold. Do not print native output,
exception details or credentials. After native launch, network activity is not
independently checked; no new network sandbox or profile change is introduced.

Acceptance:

- Existing --check fields, exit behavior and four zero-launch tests stay intact.
  --probe-native without --check or with --execute is a usage error before input
  or process launch. Explicit execution protocol/argv stays unchanged.
- Opt-in probes use exact resolved argv, no task stdin/Manager, and no retry.
  Help advertises all four required flags before reporting advertised status;
  missing/invalid/nonzero/oversized/timeout/unavailable probes exit 1 with fixed
  guidance and retain only observed original exit codes.
- Version and help evidence are independent: a high version never implies
  flags, an unrecognized version cannot be echoed, and body/footer mentions do
  not become advertised options. No ready/verified/model-acceptance claim.
- Offline synthetic executable tests exercise parsing, actual CLI argv, bounded
  timeout/descendant cleanup and interruption. Portable simulations supplement
  POSIX fixtures, without claiming Windows native acceptance.
- Focused checks precede one serial full unittest, config/manifests, JSON/YAML
  and Git integrity; local commit/bundle/patch and immutable prior-chain proof.

Allowed: codex_harness module, new probe tests, existing harness guide, this
artifact directory. No runner/worker/Manager, schema, protocol, workflow,
package/dependency, OpenClaw trusted-native/profile or account behavior changes.
Output sampling bounds parsing/memory; timeout bounds runtime. Temporary-file
output is not a hard disk quota or security isolation. Trusted executable startup
internals remain outside this diagnostic's proof.
