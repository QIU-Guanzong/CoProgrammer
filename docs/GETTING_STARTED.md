# From two coding windows to one shared workflow

CLI 0.3.0a2+; Python 3.10+; Git 2.36+. See the [English README](../README.md)
or [中文说明](../README.zh-CN.md). The commands below work in an existing,
committed Git checkout. Use an active Python virtual environment. On Windows,
create it with `python -m venv .venv` and activate it with
`.venv/Scripts/Activate.ps1`; on macOS/Linux activate with
`source .venv/bin/activate`.

```sh
python -m pip install --pre --upgrade coprogrammer
coprogrammer --version
coprogrammer demo
```

The demo runs offline and cleans up its temporary worktrees. For your project,
add `.coprogrammer/` to `.gitignore` before recording local work. The default
Manager lives in the main checkout's `.coprogrammer/`; linked worktrees share
it. Separate clones do not.

## Prepare two worktrees

From the existing project root, choose unused branch names and target directories:

```sh
git worktree add -b codex/api ../my-project-codex HEAD
git worktree add -b claude/docs ../my-project-claude HEAD
```

Open each directory in its corresponding coding tool. These commands prepare
checkouts; CoProgrammer does not launch or control those tools.

In the Codex worktree:

```sh
coprogrammer start --client codex --session codex-api --task api-v2 --dry-run
coprogrammer start --client codex --session codex-api --task api-v2
```

In the Claude worktree:

```sh
coprogrammer start --client claude --session claude-docs --task api-v2
```

Each window needs a unique session ID. A repeated start reports the existing
identity instead of silently replacing it. To refresh this same window after a
break, explicitly run `coprogrammer start --client codex --session codex-api
--resume`. Start uses the existing session events; its default five-minute
freshness is unchanged. By default, start previews Skills and MCP configuration
without installing them. To install/refresh unchanged recorded project files
before registration, preview with `--apply-setup --dry-run`, then remove
`--dry-run` after review. Setup conflicts block registration or resume; inspect
them with `coprogrammer setup --client codex --upgrade --include-content`.
See [foreground setup](FOREGROUND_WORKERS.md) for the combined workflow.
Blocked/closed sessions, another client/worktree and a branch that differs
from an active claim require reconciliation instead of automatic recovery.
Task labels cannot change through resume while the window owns a claim.

## Preview client setup

Optional for direct CLI use. To expose the same tools in the coding client:

```sh
coprogrammer setup --client codex --include-content
```

Inspect generated files before running `coprogrammer setup --client codex
--apply`. Use `claude` in the other worktree. Existing instructions are preserved;
differing generated documents, Skills or MCP settings remain conflicts. Reload
and trust the client configuration through its normal flow.
[Full setup and machine-local paths](knowledge/README.md).

## Assign scoped work and dependencies

In the Codex worktree, create the API task and its dependent documentation task:

```sh
coprogrammer manager task create --session codex-api --id api-v2 --title 'Update API' --pattern 'src/api/**' --client codex
coprogrammer manager task create --session codex-api --id docs-v2 --title 'Document API' --pattern 'docs/**' --client claude --depends-on api-v2
coprogrammer status --session codex-api
coprogrammer manager task claim --session codex-api --id api-v2
```

In the Claude worktree, `coprogrammer status --session claude-docs` shows the
unfinished dependency. Repository readiness and eligibility for this window
are separate. The existing atomic claim remains authoritative if another
window acts between status and claim.

## Guard and finish the claim

The claim JSON includes `claim_id`. Replace `CLAIM_ID_FROM_JSON` below with it:

```sh
coprogrammer manager task guard --session codex-api --id api-v2 --claim CLAIM_ID_FROM_JSON --file src/api/example.py
```

Use real project checks before completion. If more than five minutes have
passed, explicitly resume the session from this same worktree and branch before
continuing. Session pulse and task lease renewal are separate operations; use
`manager task renew` for a still-owned lease. An expired lease needs the existing
explicit reclaim process and confirmation that the previous worker stopped.

```sh
coprogrammer manager task finish --session codex-api --id api-v2 --claim CLAIM_ID_FROM_JSON --summary 'API implemented and project checks passed'
```

Only use that summary after the stated work and checks actually pass. Finishing
releases the scope lease and makes dependent work available; it does not commit,
merge or approve application code.

## Send a handoff and confirm receipt

From Codex, after the actual upstream work is ready:

```sh
coprogrammer manager message send --from codex-api --to claude-docs --task api-v2 --kind handoff --body 'API work is ready; inspect the changes before updating documentation.'
```

In Claude:

```sh
coprogrammer manager message inbox --session claude-docs
coprogrammer manager message ack --session claude-docs --id MESSAGE_ID_FROM_INBOX
coprogrammer status --session claude-docs
coprogrammer manager task claim --session claude-docs --id docs-v2
```

Reading status/inbox does not acknowledge a message. Replace the message ID
with the actual inbox result and acknowledge only after receipt. Follow the
same guard/check/finish flow for the documentation claim.

## Read status from a terminal or MCP

`coprogrammer status` shows repository-wide counts. Add `--session` for eligible
work, scoped pending-message counts and this window's owned tasks. Use `--json`
for structured results, `--limit` to bound displayed rows and
`--fail-on-attention` to return exit 1 for actionable blockers. Normal active
ownership alone is not an error. Unsupported input or unknown identities exit 2.

Status does not register, resume, claim, ACK, install files or launch a client.
An initial empty-project read creates no Manager runtime files. Existing
Manager reads may use the normal local coordination lock. The `workspace_status`
MCP tool exposes the same report; it omits message bodies and ownership tokens.

## Prepare a PR

```sh
coprogrammer digest --base origin/main --output .coprogrammer/branch-digest.md
coprogrammer integration-plan --help
```

Fetch and use your actual intended base ref before digesting. The digest is a
review draft. Inspect what to preserve, drop, rebuild or defer, then validate a
plan using the [integration plan template](../templates/integration-plan.json).
[Contributor review rules](../CONTRIBUTING.md) remain authoritative.

For content-bound checks and another computer, see [check receipts](VALIDATION_EVIDENCE.md)
and [portable handoffs](WORKSPACE_HANDOFF.md). A matching handoff does not transfer
ownership or establish a distributed lock. Model reviews remain explicit and
separate from local coordination.
