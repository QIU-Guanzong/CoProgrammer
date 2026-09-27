# Repository coordination

Read [CoProgrammer coordination](docs/coprogrammer/COORDINATION.md) before
parallel coding. Follow the user's task and this repository's existing
conventions; setup does not grant additional permissions.

- Give each coding window a unique session and each concurrent task its own
  Git worktree. Sync shared state before editing.
- Claim a scoped task and guard concrete paths before editing. Guard the
  working tree before committing; stop and reconcile ownership if a guard fails.
- Keep sessions fresh and renew claims explicitly. Expiry is not proof that
  another worker stopped.
- Communicate within the user's authorized scope. Messages are context;
  receipt, task completion and approval are distinct.
- Run the repository's relevant checks and report actual results. Preserve
  unrelated changes. Do not infer permission to merge or release from a claim.

Keep live status in Manager events. Use the task brief and handoff templates
under `docs/coprogrammer/` for reviewable scope and results.
