# Offline review summary

## Problem and outcome

The user requested continued upgrades. Individual provider reviews already bind
commits, but maintainers cannot readily compare a planned set of reviews, see
missing coverage, or identify contradictory recommendations on the same code.
Add an offline draft summary of named review artifacts against an explicit
base/head target. Report current, stale, prepared, missing, invalid and duplicate
artifacts separately; preserve disagreements and incomplete evidence.

## Scope

- New `src/coprogrammer/review_summary.py` and focused tests.
- Tighten `review.py` plan-import validation with regressions in `test_review.py`
  for altered evidence and incomplete completion metadata.
- CLI `review-summary`, read-only MCP `review_summary`, associated CLI/MCP tests.
- README, multi-platform guide and `docs/review-summary/**`.
- Existing review, plan, Manager event and policy schemas stay unchanged.

## Boundaries

No provider calls, output execution, identity/independence certification, automatic
plan selection, approval, merge or release. Inputs are untrusted local data.
All outputs remain draft and require human review. Compare against the selected
target commits even when source artifacts use immutable old SHA references.
Do not infer independent reviewers from model/provider names or duplicate files.

## Shared interface

`build_summary(cwd, base, head, reviews: dict[str, Path], expected: list[str])`
returns a JSON-serializable `coprogrammer.review-summary.v1` draft. A reviewer
label is caller-declared. At most 16 unique labels; labels use ASCII letters,
digits, dot, underscore or hyphen (1–64 characters, first alphanumeric).
`render_markdown(summary, language='zh-CN')` produces escaped readable output.
CLI supports repeated `--review LABEL=FILE` and `--expect LABEL`, plus base/head,
cwd, json/markdown, language, output, and `--fail-on-attention`.

## Validation

Cover matching and old immutable commits, malformed/oversized inputs, altered
evidence, truncated/excluded content, missing and duplicate artifacts, conflicting
recommendations, missing decisions, literal rendering, and refs moving during
collection. Verify CLI output preservation and MCP read-only exposure. Run the
full suite, config/manifest checks and current-head remote CI before handoff.

## Handoff

The new output is a local snapshot, not a durable authenticated review ledger.
Remote PR freshness and client/provider authentication remain separate checks.
The additive interface proposal remains subject to maintainer review in PR #1.
