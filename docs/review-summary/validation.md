# Validation record

Date: 2026-09-26. Code and documentation implementation: `85a97392a0a18a106bef7e346edefe0b3681a1d4`.

## Results

- Source suite: 162 tests passed (`PYTHONPATH=src python3 -m unittest discover -s tests`).
- Core summary coverage: 23 tests, including old immutable commits, partial evidence,
  sensitive exclusions, duplicates, altered JSON, same-read input hashes, moved refs,
  preserved risk notes and literal Markdown rendering.
- CLI/MCP coverage: 8 tests, including missing-review reporting, attention exit status,
  existing output preservation, relative paths, nested input validation and stdio replies.
- Integration-plan coverage: 20 tests, including altered diff text, inconsistent completion
  fields, coverage metadata, and valid complete/partial review imports.
- Built a wheel in an isolated build environment, installed it into a fresh virtual
  environment, then ran the same 162 tests successfully without `PYTHONPATH`.
- Invoked the installed wheel as a real MCP subprocess: discovered the read-only
  `review_summary` tool, reported three missing reviews, returned a subsequent ping,
  and left the Manager event log byte-for-byte unchanged.
- Invoked the installed CLI against saved request previews: wrote a report and returned
  attention exit code 1; request previews were not promoted to completed reviews.
- Project config, change manifest and whitespace checks passed.
- Parsed 29 JSON and 10 YAML source files; checked 21 relative documentation links.
- Independently reviewed the new summary, command/tool boundaries and guide; no
  must-fix findings remained.

## Evidence and boundaries

The published example uses synthetic review artifacts and a temporary Git repository.
It demonstrates two current input artifacts, one missing reviewer, one file-level
conflict and one risk. These are fixture outcomes, not provider execution evidence.

No live provider call, API-key verification, client authorization, hosted service,
identity certification, remote PR freshness check, merge or package publication was
performed. The build emits the existing packaging-license deprecation warning but
completes successfully; packaging metadata cleanup is outside this feature.

The new additive interface and the broader upgrade remain subject to maintainer review
in PR #1. Read current-head CI results on the PR for Ubuntu/Windows Python 3.10/3.13.
