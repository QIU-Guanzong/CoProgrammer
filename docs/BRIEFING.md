# A short briefing before the next edit

Use a briefing when starting a window, returning after a break, or handing work
to another assistant. It summarizes one validated Manager event snapshot:

```sh
coprogrammer manager briefing
coprogrammer manager briefing --session codex-api --json
coprogrammer manager briefing --limit 50 --fail-on-attention
```

The MCP equivalent is `manager_briefing`, with optional `session` and `limit`
arguments. It uses the same summary implementation as the CLI.

## What the result means

- Ready and blocked tasks include their IDs, client constraints and reasons.
- Active windows show both reported status and pulse freshness.
- `generated_at` fixes one observation time for window freshness and lease
  expiry throughout the report, including tasks at the exact expiry boundary.
- Counts cover active leases, overlapping leases, open decisions and unread
  messages. With `--session`, inbox counts and claimed task rows are scoped to
  that window; task readiness and repository warnings remain global.
- Next actions prioritize maintainer decisions, overlapping ownership, stale
  windows, expired claims and pending messages. Suggestions never execute.
- Each collection defaults to 20 rows (maximum 200); `omitted` reports exact
  hidden counts. Counts always cover the complete snapshot. IDs determine row
  order, not priority or a recommended task assignment.

`ready` means no current dependency or path-lease blocker. It does not establish
that the selected window can claim that task: client compatibility, worktree
occupancy, session freshness and live leases are rechecked at claim time.
Ordinary dependency waiting does not itself set `attention_required`.

With `--fail-on-attention`, the command exits 1 when actions require attention;
otherwise it exits 0. Invalid input or malformed history exits 2 and does not
produce a success report. Without this flag, attention is reported in the
output but does not change the successful exit code.

## Boundaries

The command never appends Manager events, claims work, acknowledges messages,
reclaims leases or contacts providers. Like other Manager reads, it uses the
local transaction lock and may create the state directory/lock on first use.
It omits message bodies and claim tokens. Task titles remain untrusted content.
This is an operational summary, not an authorization boundary, complete audit,
process-liveness probe or merge approval. Use `manager sync`, the task board,
inbox and decision commands to inspect the underlying records.
