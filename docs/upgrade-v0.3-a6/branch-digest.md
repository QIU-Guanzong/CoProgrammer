# Branch digest

Preserve: opt-in generated-file updates guarded by matching hashes; read-only
preview; instruction preservation; customization conflicts; shared Manager
locking with worktree-local receipts; selective/cross-client record retention;
staged replacements and conditional rollback; real worktree/concurrency tests;
installation guidance and primary-source research.

Defer: automatic package/client updates, global settings, new inbox/database,
cross-machine live state, hooks, background scheduling, automatic ACKs or lease
takeover, WorkBuddy UI, account/model testing and outreach. No source integration
patch is applied by the feature and no event/schema/workflow change is included.

Validate both source and independently installed package; inspect the complete
PR after digest/CI, verify merged tree against the tested tree, then use the
existing preview-release workflow and verify a fresh published installation.
