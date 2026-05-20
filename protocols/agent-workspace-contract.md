# Agent Workspace Contract

This protocol defines how multiple agents work in parallel without destroying
shared context.

## Before Work

Each agent receives:

- task brief;
- allowed paths;
- forbidden paths;
- expected output;
- contract dependencies;
- validation commands.

## During Work

Each agent should publish a heartbeat when one of these changes:

- current file ownership;
- contract touched;
- blocker discovered;
- plan changed;
- useful experiment found;
- handoff needed.

## After Work

Each agent must produce a change manifest:

- task intent;
- core changes;
- files touched;
- contract changes;
- tests run;
- known risks;
- follow-up work.

## Path Ownership

Path ownership is advisory, not a substitute for code review. If an agent needs
to edit outside its allowed path, it must request a contract update before
making the change.
