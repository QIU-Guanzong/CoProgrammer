# v0.3 validation and release readback

Local baseline: Python 3.13.5 on macOS; 282 existing tests passed before edits.
The 24 focused new regressions passed after the implementation review.

New acceptance coverage uses real Git repositories, independent clones,
registered windows and stdio MCP processes. It exercises eligible/excluded
dispatch, stale sessions, occupied worktrees, client/dependency constraints,
content changes at one HEAD, content-preserving commits, failed/missing/timed-out
commands, command hashes, record tampering/expiry, owner-checkout mismatch and
cross-clone version/base/content drift. No models or native client GUIs are used.

Final source receipt is generated after all authored files are finalized:

```sh
PYTHONPATH=src python -m coprogrammer check run --label v03-source \
  --output .coprogrammer/checks/v03-source.json \
  -- python -m unittest discover -s tests
PYTHONPATH=src python -m coprogrammer check verify \
  --artifact .coprogrammer/checks/v03-source.json \
  -- python -m unittest discover -s tests
```

Build a wheel outside the repository, install into a fresh virtual environment,
unset `PYTHONPATH`, verify the import location and run the same full suite.
Installed-package client configuration pins those stdio subprocesses to that
environment. Also validate config, manifest, integration plan, JSON/YAML, local
Markdown links and whitespace. Existing PR CI covers Ubuntu/Windows with Python
3.10/3.13. Final PR/check/tag/PyPI results are read back after publication and
recorded in release notes; this document alone does not establish a release.

The source/wheel checks do not establish native Codex/Claude/Copilot trust or
connection, a live GLM/DeepSeek request, a hosted Manager, or a distributed lock.
No credentials or global client configuration are changed.
