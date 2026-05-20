# Protocol-Guided Semantic Integration Loop

This framework treats AI-assisted software development as a full collaboration
cycle, not as a one-time merge conflict event.

## Problem Statement

Traditional merge tools ask:

> Which text should survive?

AI multi-agent development asks:

> What did this branch learn, and how should that insight be safely integrated
> into main under current architecture constraints?

## Four Layers

### 1. Protocol Layer

Before coding begins, the team defines:

- main branch constitution;
- module boundaries;
- shared contracts;
- protected files;
- owner review rules;
- allowed and forbidden agent behavior.

### 2. Collaboration Telemetry Layer

During coding, each agent reports:

- current task;
- files being edited;
- intended next step;
- contract changes;
- blockers;
- useful experiments and failed attempts.

This creates a shared state board that can forecast path conflicts, contract
collisions, and architecture drift before PR time.

### 3. Branch Digestion Layer

After coding, a branch is not reviewed only as a raw diff. It is digested into:

- branch intent;
- core contribution;
- non-essential changes;
- contract changes;
- architecture conflicts;
- risk score;
- recommended integration plan.

### 4. Semantic Integration Layer

The integration agent starts from latest `main`, reads the branch digest, and
rebuilds the smallest safe patch. The original feature branch becomes evidence,
not the thing that must be merged directly.

## Closed Loop

Every integration record should feed back into the protocol:

- new architecture rule;
- new protected path;
- new contract test;
- new agent permission rule;
- new PR checklist item.
