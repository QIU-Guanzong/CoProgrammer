# Start result guidance

Baseline local commit: `c9962237f414960777e1cc9ab23074220cfcb0ef`; tree matches
released a8/main `97d72efa925975bc231ea65ba0e4f2d566cac0ef`.

Scope: correct human `start` output after preview, setup conflict and successful
setup; align the existing design/localization/first-use documents. Keep JSON,
exit codes, session registration, setup application and message receipts intact.

Evidence: the renderer always used pre-application missing counts and always
suggested `status --session`, including preview/new blocked windows. The first-use
guide said start never installed Skills/MCP despite `--apply-setup` support.
Three real-checkout regression tests fail on the baseline output.

Acceptance: success describes applied setup and a working status command; preview
is read-only; conflicts name paths but reveal no contents, preserve registration
state and suggest inspection before an explicit rerun. Existing onboarding and
foreground regressions must pass. Applicable Fluent 2, Ant Design and GOV.UK wording guidance is linked and
scoped in LOCALIZATION.md; it does not establish model-quality acceptance.

No package version, release, workflow, schema, account or provider changes.
