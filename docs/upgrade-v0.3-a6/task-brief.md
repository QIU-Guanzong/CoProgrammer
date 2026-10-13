# Task brief

Improve the installed-client update experience after comparing gstack, Beads
and MCP Agent Mail. Existing setup cannot distinguish its own old generated
files from user changes, so a package upgrade or Python relocation can leave
Skills and MCP configuration permanently conflicting.

Add an explicit, preview-first `setup --upgrade` that updates only unchanged
files recorded by a previous successful setup. Keep project instructions and
customized/unrecorded files intact. Store hashes, not file contents, in a
worktree-local receipt. Serialize cooperating installers with the existing
Manager lock; recheck before writes, roll back unchanged completed writes on
failure, and report interruption/recovery limits accurately.

Allowed: setup implementation, CLI, focused tests, installation docs, bilingual
README, branch artifacts and release version metadata. Excluded: schemas,
protocols, workflows, authentication, global client configuration, automatic
model calls, automatic package downloads, hooks/daemons, WorkBuddy GUI testing,
automatic ACKs, lease takeover, and unrelated refactoring.

Validate customized files, missing/corrupt receipts, read-only preview, subset
and cross-client upgrades, links/reparse points, failures and cooperating
concurrent installers. Run full source and installed-wheel checks, Linux and
Windows CI, then verify the published package through the existing release flow.
