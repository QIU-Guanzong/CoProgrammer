# Validation plan

Baseline: main 9ce280073ab01d9c5233f028364aa77faf9a8cdc, published 0.3.0a1.
The existing suite contains 310 tests. Fourteen new regressions exercise real Git
worktrees, configuration preservation, dry-run/register/resume, eligibility,
claim ownership boundaries, stale sessions, message/token privacy, UTF-8 output
and native stdio MCP schema/annotations. Four additional storage regressions
cover the Windows CI failure: retrying the same complete log under lock,
persistent failure preserving the old log, and immediate failure for unrelated
Windows errors or POSIX errors. The final suite contains 328 tests.

Final checks use source and an independently installed wheel with PYTHONPATH
removed; validate config/manifests, JSON/YAML, repository Markdown links and
packaged Skill mirroring. PR CI covers Ubuntu/Windows with Python 3.10/3.13.
Publication is verified separately from source commits through the existing
release workflow, version-specific PyPI metadata, downloaded wheel checksums,
matching package files and a fresh installation/demo/MCP run.

No native client GUI, live provider request, distributed lock or star-growth
outcome is established by these checks. Final results belong in release notes
and local release evidence, not in project agent instructions.
