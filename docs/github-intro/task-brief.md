# GitHub introduction and collaboration follow-up

## Problem

The GitHub About field is empty. The README foregrounds research links and
unpublished installation channels before explaining the usable workflow.
The user requested clearer GitHub positioning and continued improvements
informed by gstack and open-source collaboration.

## Expected outcome

- A concise, factual public description and an actionable README.
- Clear distinctions between coding clients, GitHub workflows and optional
  model providers; preview status stays visible.
- Contributor handoffs identify intent, exact commits, validation and unresolved
  work. A model response is not a maintainer approval.
- Reviews reject branch changes occurring during a model request, using the
  existing stale-evidence boundary and without paid retries.

## Allowed paths

`README.md`, `CONTRIBUTING.md`, `ACKNOWLEDGMENTS.md`, `docs/github-intro/**`,
`src/coprogrammer/review.py`, `tests/test_review.py`.
GitHub repository description and relevant repository topics.

## Boundaries

No schema, protocol, dependency, account configuration or merge-policy changes.
No automatic PR merge, package publication, external model call or claim of a
live provider connection. Keep documentation and the review fix in separate
commits on the existing upgrade branch.

## Validation

Check README paths, current CLI examples, source installation and remote About
readback. Run focused review tests plus the existing full suite/config check
for the review fix. Validate the change manifest and inspect the updated PR.
