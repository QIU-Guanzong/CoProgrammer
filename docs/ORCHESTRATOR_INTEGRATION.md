# Orchestrator Integration

Last updated: 2026-06-10

CoProgrammer does not run agents. It sits **after** any agent orchestrator and
**before** the merge queue:

```text
┌─────────────────────────────────────────────────────────────────┐
│ UPSTREAM: agent runtimes & orchestrators (not built here)       │
│ Conductor · Sculptor · Vibe Kanban · Claude Squad · Codex ·     │
│ Copilot Cloud Agent · OpenHands · local CLI agents              │
│         → produce parallel branches / worktrees                 │
├─────────────────────────────────────────────────────────────────┤
│ COPROGRAMMER: integration & governance layer (built here)       │
│ covenant & policy → leases/heartbeats/contract board →          │
│ conflict forecast → branch digest → integration plan →          │
│ minimal integration patch → integration record → policy update  │
├─────────────────────────────────────────────────────────────────┤
│ DOWNSTREAM: landing infrastructure (not built here)             │
│ GitHub Merge Queue · GitLab Merge Trains · Mergify · Graphite   │
│ · CI · CODEOWNERS · branch protection                           │
└─────────────────────────────────────────────────────────────────┘
```

The orchestration layer is well served and rapidly commoditizing. The unsolved
layer — repeatedly called out in 2026 ecosystem reviews — is that existing
orchestrators "leave task alignment, conflict resolution, and merge decisions
on the developer's plate." That layer is CoProgrammer's scope.

## General Recipe

Any orchestrator that produces one branch (or worktree) per agent can feed
CoProgrammer with three touchpoints:

1. **Task start → lease + heartbeat.** When the orchestrator assigns a task,
   register the agent's edit scope:

   ```bash
   python -m coprogrammer manager lease request \
     --holder agent-a --pattern "src/api/**" --task "Implement login API"
   python -m coprogrammer manager heartbeat --agent agent-a --task "Implement login API"
   ```

2. **During work → forecast.** Periodically (or in a pre-PR hook), forecast
   conflicts before they become merge-time explosions:

   ```bash
   python -m coprogrammer manager forecast --base origin/main --fail-on-conflict
   ```

   This flags (a) overlapping agent leases, (b) breaking/unknown contract
   proposals, (c) leases or changed files that touch protected paths.

3. **Task end → digest.** Before the branch becomes a PR, digest it:

   ```bash
   python -m coprogrammer digest --base origin/main --head HEAD
   ```

   The digest (plus a `change-manifest.json` written by the agent itself) is
   what reviewers and the future Integration Patch Bot consume.

## Per-Orchestrator Notes

### Conductor (conductor.build / Microsoft Conductor)

Conductor runs each agent in its own git worktree. Hook CoProgrammer into the
workspace setup and archive scripts: request a lease when a workspace is
created, run `manager forecast` + `digest` before archiving. The Manager event
log (`.coprogrammer/events.jsonl`) should live in the shared main checkout, not
in per-agent worktrees, so all agents see the same state.

### Sculptor (Imbue)

Sculptor runs agents in containers. Mount the repository's `.coprogrammer/`
state directory into each container, or point `--state-dir` at a shared
volume. Container startup runs `lease request`; the pre-PR check runs
`forecast --fail-on-conflict`.

### Vibe Kanban / Claude Squad / Emdash (worktree-based boards)

Map each Kanban card to a task brief; when a card moves to "in progress",
request a lease for the card's declared paths. When it moves to "review",
attach the digest output to the PR. Vibe Kanban is community-maintained now,
so prefer integration via plain git hooks rather than its internal APIs.

### Cloud agents (Codex, Copilot Cloud Agent, OpenHands)

These create branches directly on the remote. Use the GitHub Actions digest
workflow (`.github/workflows/pr-digest.yml`) as the integration point: the
digest runs on PR open, and `manager forecast` can run on a schedule against
all open agent branches. See `docs/AGENT_RUNTIME_INTEROP.md`.

### Git hooks (orchestrator-agnostic fallback)

```bash
# .git/hooks/pre-push (per agent worktree)
python -m coprogrammer manager forecast --base origin/main --fail-on-conflict || {
  echo "CoProgrammer forecast found high-risk conflicts; see manager status."
  exit 1
}
```

## What CoProgrammer Will Not Do

- It will not schedule, spawn, or sandbox agents (upstream's job).
- It will not order or batch final merges (downstream's job).
- It will not silently resolve conflicts: high-risk findings become
  `decision.requested` events for humans.
