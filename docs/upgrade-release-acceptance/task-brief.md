# Whole-package release candidate acceptance

Candidate base: `5b3f7aa154745038da4cf15c5fd1dfac1a8042a5` in the existing
cloud workspace `/workspace/CoProgrammer`. Review the cumulative upgrade from
`d9e55083b506013f2c38380cb0d3f35a61e92a37`; preserve all prior commits/evidence.

Review CLI/help, canonical documentation, packaged resources, setup output and
old configuration together. Build from a clean export, install a wheel into a
new temporary virtual environment, unset source import paths and execute from
disposable Git projects with no remotes. Use synthetic native/client programs
only. Validate check/preview/success, one failed launch/result, and actual Linux
interruption followed by read-only task/lease/message/edit inspection. Separate
fixtures keep failed/interrupted claims from being replayed.

Observed defect before editing: the initial wheel contains the new Python
adapter but none of CODEX_TASK_HARNESS, FOREGROUND_WORKERS or
INTERRUPTED_RUN_INSPECTION. Installed users cannot read these through the existing
knowledge catalog. README/maintenance entry points omit the new diagnostic flow.
The Codex example also assumes an eligible queued task without saying so.

Minimal repair scope: bundle the three canonical guides using the existing
Markdown package-data path and explicit knowledge allowlist; make installed
read commands discoverable in README/maintenance; state the queued-task
prerequisite; extend resource completeness/canonical synchronization checks.
Do not change installer selections, task/probe execution, Manager mutations,
resource request shape or URI validation, config, pyproject/version, protocols,
schemas, workflows, accounts/profiles or cleanup policy.

Acceptance: wheel and sdist contain the three synchronized guides, all existing
templates/Skills and runtime modules; installed CLI/module imports and generated
launchers point to the virtual environment rather than the source checkout;
baseline config validates unchanged. The synthetic adapter runs once per
explicit case, retains failed/interrupted claims and partial edits, discards
private output, and inspection preserves Manager bytes. No paid model/network
acceptance is inferred. Focused checks precede one serial full unittest run,
config/manifests, JSON/YAML, Git and artifact integrity checks.

Finish with a local commit, patches/bundle, package hashes, candidate checklist,
actual limitations and a prioritized next user goal. Remove owned temporary
fixture environments/services after capturing evidence. Do not upload/push,
open PRs, release, retry GitHub403 or the failed Library route. The previously
reported403 is historical; neither the preceding round nor this round retries it.
