# Contributing to CoProgrammer

CoProgrammer is itself developed with the collaboration style it proposes.

## Your first contribution

Start with `coprogrammer demo` and the [two-window walkthrough](docs/GETTING_STARTED.md).
Reproduce one problem before changing code. A focused improvement to a client
example, error message, worktree conflict check or handoff guide is a useful
first PR. Describe what users did, what went wrong and how they can verify the fix.

For a documentation change, run the example you changed. For CLI or MCP behavior,
add a regression that exercises the failure through a real checkout or server.
Open a [GitHub issue](https://github.com/QIU-Guanzong/CoProgrammer/issues) for
questions with a minimal reproduction; remove credentials and private source.

See [current product requirements and CLI flow](docs/MVP_DESIGN.md#current-product-requirements-and-cli-design)
and [product wording rules](docs/LOCALIZATION.md#product-wording-and-model-generated-text)
when changing user-facing output or installation guidance.

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

## Handoff and Review

Keep the same handoff format whether the contributor uses Codex, Claude Code,
Copilot or another tool. A role such as implementer or reviewer belongs to the
task, not to a particular model.

| Include | Make it concrete |
| --- | --- |
| Goal and scope | The behavior changed, allowed paths and explicit exclusions |
| Evidence | Base/head commit IDs and the branch digest or review artifact |
| Validation | Exact commands, results and the commit tested; identify mocks and skipped checks |
| Decisions | What to preserve, drop, rebuild or defer, with reasons |
| Open work | Unresolved questions, conflicting reviews and the next owner or role |

Reviewers should inspect the diff and validation evidence independently. A
second model's agreement does not count as maintainer approval; a missing,
failed or timed-out review remains missing coverage. When the code changes,
refresh the affected checks and review against the new commits.

CoProgrammer's local checks complement the repository's review rules. Maintainers
configure required reviews, CODEOWNERS and status checks in GitHub; generating
a digest or draft integration plan does not enable or satisfy those rules.

## Where to Start

- **Report a failure:** include the smallest reproducible branch/worktree setup,
  expected behavior, actual result and relevant versions. Remove private code
  and credentials from attached reports.
- **Improve an integration:** name the client or provider, record the setup
  tested, and distinguish generated configuration from a live connection.
- **Propose a shared contract:** explain compatibility and migration before
  implementing a schema, protocol or cross-module behavior change.

The [collaboration design notes](docs/github-intro/collaboration-notes.md)
explain the patterns we adapt from gstack and open-source review workflows.

## Local Checks

```bash
python -m pip install -e .
python -m unittest discover -s tests
python -m coprogrammer config validate
python -m coprogrammer manifest validate templates/change-manifest.json
```
