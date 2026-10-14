# Target cloud validation — 2026-10-13

Workspace: `e28bc78d56d3:/workspace/CoProgrammer`, branch
`codex/import-ae4a916-harness-check`. No other project or local host was used.

Private handoff acceptance:

- All 10 packets and 26 Git objects passed strict header/fragment/base64/SHA
  checks before import. The complete unique parent chain is
  `ae4a9164967c3c91a7c3983c8b680f5658e03c34` →
  `e963b72438a2e9f9fe859eb4e14b61f01460383e` →
  `d9e55083b506013f2c38380cb0d3f35a61e92a37`.
- `git fsck --full --strict` returned 0; baseline is an ancestor. Source changes
  cover eight allowed code/test/doc paths, with no protected contract/workflow
  changes. Seven original local scope/evidence files retain their SHA-256 hashes.
- Target's original adapter suite: 14 tests, OK, 7.041 seconds; config and source
  manifest validation passed.
- Supplementary gzip data: 25,819 bytes, SHA-256
  `9367cb42e7e4cbd5b106ea3b45b8054510e92c251dfc236e00e1325ed846391b`;
  packet 5/8/9 contents match existing caches, with no overwrite.

First-use diagnostic validation:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p
  'test_codex_harness*.py'`: 18 tests, OK, 6.982 seconds (14 retained + 4 new).
- Serial `PYTHONPATH=src python3 -m unittest discover -s tests`: 438 tests, OK,
  55.610 seconds. Config and new manifest validation passed; diff check passed.
- JSON/YAML syntax validation passed for 50 JSON and 10 YAML files.
- Offline wheel build used `--no-index --no-deps --no-build-isolation`; an
  independent local venv installed that wheel. Its isolated interpreter imported
  the installed module, whose bytes match the reviewed source. Check-mode smoke
  returned available/0 for a synthetic executable and unavailable/1 for a missing
  path without reading the supplied non-packet stdin or launching the fixture.
- Independent review found no implementation blocker. Documentation now carries
  the same explicit executable selection into worker examples and identifies
  `--handle-inbox` as a worker option.

Raw receipts/logs remain in local `work/transfer/` and `.coprogrammer/evidence/`.
They are not package contents or public uploads. No development service/watcher
was started; test children completed or were cleaned by the retained runner.
No native model, account or Windows CI acceptance is claimed. No paid model calls,
global changes, push, PR, merge, release or public write occurred.
