# Validation record

Date: 2026-09-26.

- Code under test: `98d171de2371f27151856980d0c26a1ecbd66471`.
- `PYTHONPATH=src python3 -m unittest discover -s tests`: 126 tests passed.
- Focused `test_review.py` coverage: 15 tests passed. New regressions cover
  base/head moves before a request (no provider call), moves during a request
  (one call, rejected advice), and immutable SHA reviews while branches move.
- `PYTHONPATH=src python3 -m coprogrammer config validate`: passed.
- Documentation check: 19 relative links across README, contributing,
  acknowledgments and collaboration notes resolve to local files.
- `git diff --check`: passed.
- GitHub repository About readback matches the description below; 10 relevant
  topics were added. This is live repository metadata, independent of PR merge.

## Published About

Open-source coordination for coding agents: shared workspace state, branch digests, and reviewable integration plans for Codex, Claude Code, and GitHub.

## Boundaries

The provider tests use mocks. No paid provider calls, client authorization,
package publication, protected-branch setting changes or PR merge were made.
The updated README is part of the existing upgrade PR. Remote CI results must
be read from the checks on that PR's current head.
