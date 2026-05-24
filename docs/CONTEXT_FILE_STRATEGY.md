# Context File Strategy

Last updated: 2026-05-25

## Core Claim

Agent instruction files are useful, but they should stay small.

CoProgrammer should separate stable guidance from live coordination state:

| Layer | Purpose | Example |
| --- | --- | --- |
| `AGENTS.md` | Stable human-readable agent instructions | How to test, how to request leases, what not to do |
| `.coprogrammer.json` | Machine-readable policy | language, protected paths, risk levels |
| Manager event log | Live coordination state | heartbeats, leases, decisions, status |
| Branch digest | Review artifact for a branch | intent, contribution, noise, risk, integration plan |
| Integration record | Historical merge rationale | what was kept, dropped, validated, and decided |

The anti-pattern is one giant prompt file that tries to contain architecture,
policy, backlog, active status, decisions, and review history. That makes agents
slower and makes state stale.

## Minimal `AGENTS.md`

A good `AGENTS.md` should contain only:

- repository purpose;
- fastest reliable validation commands;
- protected workflow reminders;
- how to use CoProgrammer Manager commands;
- clear boundaries for dangerous work.

It should not contain:

- current task backlog;
- active leases;
- open decisions;
- complete architecture docs;
- long natural-language policy copies;
- secrets, tokens, or environment-specific private state.

## Policy Placement

| Policy Type | Best Location | Reason |
| --- | --- | --- |
| Default output language | `.coprogrammer.json` | Machine-readable and CI-friendly |
| Protected paths | `.coprogrammer.json` | Used by digest risk scoring |
| Team principles | `protocols/main-branch-constitution.md` | Stable, reviewable human protocol |
| Active ownership | Manager leases | Changes during development |
| Architecture decision | Manager decision record | Needs timestamp, decider, and audit trail |
| Branch intent | Branch digest | Specific to one PR or branch |
| Validation commands | `AGENTS.md` and CI docs | Stable enough for agent onboarding |

## Experiment

CoProgrammer should run a context-file minimality experiment:

1. no `AGENTS.md`;
2. minimal `AGENTS.md`;
3. long policy-heavy `AGENTS.md`;
4. minimal `AGENTS.md` plus `.coprogrammer.json` and Manager events.

Measure:

- task success;
- files touched;
- instruction violations;
- validation commands run;
- time and token cost;
- number of stale-state mistakes.

Expected result:

Minimal instructions plus structured policy should outperform long prompt-like
instruction files for multi-agent work.

## Product Implication

CoProgrammer should provide:

- `templates/AGENTS.md`;
- `coprogrammer agents check`;
- config validation for `.coprogrammer.json`;
- Manager event commands for live state;
- branch digest and decision record artifacts for review.

The product promise is not "write a better prompt." It is "move the right state
into the right layer."
