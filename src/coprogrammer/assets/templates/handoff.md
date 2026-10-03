# Development handoff

Copy this template into a task artifact or an authorized task message. Replace
the guidance with evidence another worker can use.

## Result

Describe the completed behavior and the task ID, branch, worktree and exact
commit when available. Distinguish committed work from local changes.

## Validation

Record checks run, their results and relevant evidence. State checks that were
not run or failed; do not describe task completion as review approval.

## Remaining work

List unresolved questions, dependencies, known limitations and the next concrete
action. Include any files that need reconciliation before another worker edits.

## Coordination state

State whether the task was finished, released or still claimed, and whether
message receipt is pending. A handoff does not transfer a lease; the recipient
must sync and acquire their own task claim before editing.

## Portable context (CoProgrammer 0.3+)

Record `coprogrammer --version`, source HEAD/base, dirty state and content-bound
check statuses. Export `manager handoff` as JSON to an ignored/external path;
inspect it with `workspace compare` on the receiving machine. Confirm the source
worker stopped, run receiving-machine checks and acquire a local claim.
Context alignment does not transfer ownership between independent Managers.
