# gstack and open-source collaboration

Reviewed on 2026-09-26. gstack references below are pinned to commit
`2a113ae7e623f590095bcaaa0cc581c9a10a6632`. These are design influences;
CoProgrammer does not bundle or execute gstack code.

## What we adapt

1. **Explicit handoffs.** gstack separates planning, engineering review, QA and
   shipping, with artifacts passed between stages. CoProgrammer uses a common
   handoff format across clients: intent, scope, commits, checks, decisions and
   next owner. See [gstack's workflow](https://github.com/garrytan/gstack/blob/2a113ae7e623f590095bcaaa0cc581c9a10a6632/README.md)
   and [engineering-review artifacts](https://github.com/garrytan/gstack/blob/2a113ae7e623f590095bcaaa0cc581c9a10a6632/plan-eng-review/sections/review-sections.md).
2. **Evidence freshness.** gstack compares review-start and review-end content
   fingerprints. CoProgrammer already binds review evidence to base/head commits
   and a diff hash, then checks it again before creating a draft integration
   plan. This follow-up also rejects named refs that move before or during a
   model request. An immutable SHA review remains a review of those specified
   commits; it does not assert that a remote PR is still current. See
   [gstack's evidence checks](https://github.com/garrytan/gstack/blob/2a113ae7e623f590095bcaaa0cc581c9a10a6632/lib/review-evidence.ts).
3. **Visible review coverage.** gstack treats a timed-out independent review as
   missing coverage. CoProgrammer's contributor guidance separates completed
   checks, mocks, failures and skipped work; model agreement never grants merge
   authority. See [gstack's review error handling](https://github.com/garrytan/gstack/blob/2a113ae7e623f590095bcaaa0cc581c9a10a6632/ship/sections/adversarial.md).

GitHub provides repository-level review controls, including required reviewers,
code-owner review and dismissal of stale approvals. CoProgrammer produces
evidence for that process; maintainers configure and enforce those controls in
GitHub. See [GitHub's protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-pull-request-reviews-before-merging).

## Deliberate scope

Codex, Claude Code and Copilot are client integration surfaces. Claude API,
GLM and DeepSeek are optional advisory providers. Roles are assigned per task;
no provider is designated the permanent architect, implementer or judge.

The current implementation has local coordination, branch digests and draft
plans. An independent-review completion ledger, hosted collaboration service
and automatic patch reconstruction remain future work. This update makes no
claim that those features exist or that model-provider authentication has been
tested live.
