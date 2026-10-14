# Native readiness and review validation

The optional Claude probe runs version/help/auth status only, never a task.
Plain check still launches nothing. Version and account text are reduced to
fixed status fields. Missing declarations, logged-out state, invalid replies,
failed commands and interruption remain distinct from model connectivity.

- Claude focused: 22 tests passed, including nine new readiness cases.
- Codex focused: 14 tests passed; the shared probe's default exit-code behavior
  is unchanged. Accepting exit 1 stdout is explicit for Claude auth status only.
- Serial full regression: 496 passed, zero failures/skips, 80.740s, with
  ResourceWarning promoted to error.
- Config and 19 upgrade manifests passed; 56 JSON and 10 YAML documents parsed.
- Installed wheel/sdist match 51 source package payloads. All 16 installed
  resources are readable and the Claude guide matches its canonical source.
- Actual installed Claude 2.1.299 diagnostic recognized the native version and
  a logged-out auth status. Help omitted `--max-turns`, which remains unverified
  rather than classified unsupported. No model request or login was submitted.
- Earlier original claim, immutable receipt and all 22 recorded deliverable
  hashes remain unchanged. The unknown Codex model-start attempt was not replayed.

All new test runs are offline fixtures. Successful multi-provider model
collaboration remains unverified pending usable authorized configuration; no
fixture or local readiness label is treated as real model acceptance.

Public review content removes internal coordination identifiers and personal
environment/authorization narratives. Original cloud history and detailed
receipts remain private. The review commit uses the tested final file tree
with public main as its parent; its SHA differs from the private source chain.
The remote tree is checked against the local tree before the draft PR is opened.
No merge, release, schema/protocol/workflow or account/provider change is included.
