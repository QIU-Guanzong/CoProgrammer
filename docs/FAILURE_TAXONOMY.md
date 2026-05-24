# Failure Taxonomy

This taxonomy defines the failure modes CoProgrammer should detect, prevent, or
record.

## Primary Failure Modes

### 1. Stale Shared State

An agent acts on information that was true earlier but is no longer true.

Signals:

- another branch already changed the same contract;
- a decision was made but not propagated;
- tests pass locally against an old interface;
- duplicated work appears in parallel branches.

Manager Plane response:

- heartbeat;
- workspace lease;
- contract board update;
- decision record.

### 2. Contract Drift

An agent changes an API, schema, migration, shared type, auth behavior, or
deployment contract without explicit coordination.

Signals:

- protected path match;
- generated client/server mismatch;
- frontend/backend contract disagreement;
- undocumented migration.

Manager Plane response:

- protected-path risk scoring;
- decision queue;
- owner review;
- contract compatibility note.

### 3. Architecture Drift

An agent solves a local task by changing a shared architecture principle.

Signals:

- new global abstraction;
- bypassed auth/payment/data integrity path;
- duplicate service layer;
- new dependency that changes platform assumptions.

Manager Plane response:

- architecture decision request;
- main constitution reference;
- integration plan before merge.

### 4. Noise Amplification

The branch contains useful ideas mixed with broad generated churn.

Signals:

- formatting unrelated files;
- large refactor without task intent;
- dependency lockfile churn;
- generated artifacts mixed with source changes.

Manager Plane response:

- branch digest;
- noise section;
- minimal patch reconstruction.

### 5. Review Compression Failure

Reviewers cannot see the real decision because the diff is too large or poorly
explained.

Signals:

- vague PR description;
- missing manifest;
- many unrelated files;
- no integration plan.

Manager Plane response:

- change manifest;
- branch digest;
- human decision list.

### 6. Validation Mismatch

Tests pass but the branch still violates product or architecture intent.

Signals:

- mocks replace real paths;
- test coverage only proves the new path, not compatibility;
- security/payment/auth success is simulated;
- no migration dry run.

Manager Plane response:

- validation registry;
- risk-specific checks;
- human approval for high-risk behavior.

### 7. Agent Cross-Talk Contamination

Agents directly copy each other's temporary plans, partial assumptions, or
unfinished patches.

Signals:

- agent output references unaccepted ideas from another agent;
- branch repeats a discarded approach;
- multiple agents modify the same files without a lease.

Manager Plane response:

- shared state store;
- accepted decision records only;
- lease board;
- integration record.

## Research Use

Every research lead should map to one or more failure modes. If a project does
not help with any failure mode, it is probably not relevant to CoProgrammer.

## MVP Implication

The first Manager Plane slice should focus on:

1. stale shared state;
2. contract drift;
3. review compression failure.

These are frequent, painful, and can be improved without building a full
autonomous integration agent.
