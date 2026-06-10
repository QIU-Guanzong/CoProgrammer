# Coordination Lifecycle

CoProgrammer should help teams before, during, and after AI-assisted coding.
The product is strongest when these stages are treated as one continuous
governance loop instead of separate templates or one-off PR comments.

## Core Claim

AI coding agents create value faster than humans can continuously inspect raw
diffs. The solution is not to slow every agent down. The solution is to make
direction, shared state, and integration decisions explicit at the right time.

CoProgrammer's lifecycle is:

1. **Before coding**: define the project covenant and task boundary.
2. **During coding**: synchronize agents through a durable Manager Plane.
3. **After coding**: negotiate what to preserve, drop, rebuild, or defer before
   anything reaches `main`.

## Stage 1: Before Coding

Goal: prevent direction loss before agents start producing code.

Primary question:

> What is this project allowed to become, and what is this task allowed to
> touch?

Required artifacts:

| Artifact | Purpose |
| --- | --- |
| `protocols/main-branch-constitution.md` | Human-readable principles for `main`. |
| `.coprogrammer.json` | Machine-readable protected paths, risk levels, and routing policy. |
| `CODEOWNERS` | Ownership for review and protected areas. |
| `AGENTS.md` | Stable repository instructions for coding agents. |
| `templates/task-brief.md` | Task intent, allowed paths, forbidden paths, contracts, and validation. |

Useful rules:

- Every non-trivial task starts with a task brief.
- Every task declares allowed paths and forbidden paths before implementation.
- Contract changes must be named before code edits, not discovered at PR time.
- Long-lived architecture debates go through a decision record or discussion
  before agent work begins.
- Simple work may use cheaper/faster models, but protected areas require human
  review according to `.coprogrammer.json`.

Minimum workflow:

```bash
python -m coprogrammer config validate
python -m coprogrammer agents check
```

Future product surface:

- `coprogrammer project init` to generate the covenant pack.
- `coprogrammer task brief new` to create a machine-readable task brief.
- A policy checker that refuses high-risk agent work without an explicit scope.

## Stage 2: During Coding

Goal: prevent stale state, duplicate work, and hidden contract drift while
agents are still working.

Primary question:

> What is each agent doing right now, and which shared assumptions are under
> pressure?

The Manager Plane is the coordination channel. Agents should not depend on
direct chat with each other as the source of truth. Direct conversation can
help, but durable coordination must be captured as events, leases, contract
proposals, and decisions.

Required artifacts and events:

| Signal | Purpose |
| --- | --- |
| `agent.heartbeat` | Current task, edit area, next step, blockers, and insights. |
| `lease.requested` / `lease.granted` | Advisory path, contract, test, or integration ownership. |
| `contract.change.proposed` | Early notice that a shared API/schema/type/behavior may change. |
| `decision.requested` | A human decision is needed before agents continue safely. |
| `decision.recorded` | Accepted direction that future agents can trust. |

Current local workflow:

```bash
python -m coprogrammer manager init
python -m coprogrammer manager heartbeat --agent agent-a --task "Implement API"
python -m coprogrammer manager lease request --holder agent-a --pattern "src/api/**"
python -m coprogrammer manager contract propose \
  --proposer agent-a \
  --kind api \
  --name "POST /login" \
  --summary "Add login response contract"
python -m coprogrammer manager status
```

Useful rules:

- If an agent needs to edit outside its task brief, it requests a new lease or
  decision first.
- Overlapping leases should create a decision item, not a silent race.
- Breaking or unknown contract compatibility should create a decision item.
- Heartbeats should be high-signal, not a full transcript.
- Decisions, not temporary agent opinions, become the reusable source of truth.

Future product surface:

- A dashboard showing active agents, leases, contract pressure, and open
  decisions.
- Stale-state warnings when an agent heartbeat references old `main` or an
  already superseded decision.
- GitHub/Slack/IDE adapters that write to the Manager Plane instead of becoming
  separate coordination silos.

## Stage 3: After Coding

Goal: keep useful branch insight while refusing noisy or unsafe merge units.

Primary question:

> Which parts of this branch should survive, and how should they be rebuilt on
> latest `main`?

Required artifacts:

| Artifact | Purpose |
| --- | --- |
| `templates/change-manifest.json` | Agent-authored summary of intent, contracts, tests, and risks. |
| Branch digest | Reviewer-facing summary of files, commits, risk, protected paths, and decisions. |
| `templates/integration-plan.json` | Machine-readable plan for what to rebuild, drop, validate, and roll back. |
| `templates/integration-record.json` | Historical record of what was preserved, dropped, decided, and validated. |

Compromise model:

| Decision | Meaning |
| --- | --- |
| Preserve | The branch contains an idea or implementation detail worth keeping. |
| Drop | The branch contains noise, churn, or an unsafe direction. |
| Rebuild | The idea is valid, but the patch must be reconstructed from latest `main`. |
| Defer | The idea is useful but belongs in a separate task or proposal. |
| Reject | The proposal violates the project covenant or accepted decisions. |

Current PR workflow:

```bash
python -m coprogrammer digest --base origin/main --head HEAD --language zh-CN
python -m coprogrammer manifest validate templates/change-manifest.json
python -m coprogrammer integration-plan validate templates/integration-plan.json
```

Useful rules:

- The source branch is evidence. The integration branch is the merge candidate.
- Reviewers approve an integration plan, not just a raw generated diff.
- Protected path changes require compatibility notes and owner review.
- Every dropped idea should be visible in the integration plan or integration
  record.
- Integration records should feed back into future policy, tests, and task
  briefs.

Future product surface:

- A PR bot that converts digest findings into explicit preserve/drop/rebuild
  decisions.
- A minimal-patch integration bot that starts from latest `main`.
- Automatic integration record creation after validation.
- Recurring protocol-update suggestions from repeated integration failures.

## End-to-End Loop

```text
Project covenant
  -> task brief
  -> lease and heartbeat
  -> contract proposal or decision request
  -> change manifest
  -> branch digest
  -> integration plan
  -> minimal integration patch
  -> validation
  -> integration record
  -> policy or protocol update
```

## MVP Implication

The current Branch Digest Bot is the right first PR-facing wedge, but the
larger product should be framed as a lifecycle guardrail:

1. **Covenant pack** for new projects.
2. **Manager Plane** for active multi-agent work.
3. **Branch digest and integration plan** for PR review.
4. **Integration record** for learning after merge or rejection.

This keeps CoProgrammer focused: it does not replace GitHub, CI, or coding
agents. It supplies the missing coordination and semantic integration layer
around them.
