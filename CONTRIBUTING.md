# Contributing to CoProgrammer

CoProgrammer is itself developed with the collaboration style it proposes.

## Development Rules

1. Keep protocol changes, tool changes, dependency upgrades, and formatting-only
   changes in separate PRs.
2. Any change to `protocols/`, `schemas/`, or `.github/` must explain the
   compatibility impact.
3. Any CLI behavior change must include or update tests.
4. Large AI-generated branches should include a branch digest before review.
5. Avoid broad rewrites unless the PR is explicitly about architecture cleanup.

## Required PR Artifacts

Every non-trivial PR should include:

- task intent;
- files touched;
- shared contracts changed;
- validation run;
- known risks;
- integration notes.

Use `.github/PULL_REQUEST_TEMPLATE.md` and `templates/branch-digest.md`.

## Local Checks

```bash
python -m pip install -e .
python -m unittest discover -s tests
python -m coprogrammer config validate
python -m coprogrammer manifest validate templates/change-manifest.json
```
