# CoProgrammer coordination

Follow the repository's `AGENTS.md` and
`docs/coprogrammer/COORDINATION.md` for parallel coding. Use one session per
window and a separate Git worktree for each concurrent task.

Before editing, sync shared state, claim an eligible task and guard its concrete
paths through CoProgrammer MCP or the matching CLI. Keep the claim token and
renew it explicitly; guard the working tree before committing. Respect failures
and preserve unrelated changes.

Exchange task messages only within the user's authorized scope. Reading is
not acknowledgement, and completion is not review approval. Report actual
validation and remaining work. Configuration alone does not prove that MCP
connected; do not silently continue coordinated edits when ownership is unknown.
