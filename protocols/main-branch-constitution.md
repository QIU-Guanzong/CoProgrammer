# Main Branch Constitution

The main branch is the source of architectural truth. AI agents may propose
changes, but they must not silently rewrite shared assumptions.

## Principles

1. Main must remain deployable and testable.
2. Public contracts must be changed explicitly and reviewed by owners.
3. Feature work, refactoring, formatting, and dependency changes should be
   separated.
4. Generated code must be reviewed as human-owned code before merging.
5. Large branches must be digested before integration.

## Protected Areas

Teams should customize this list:

- API schemas and OpenAPI specs;
- protobuf, GraphQL, shared type definitions;
- database migrations;
- authentication and authorization;
- payment and billing;
- global configuration;
- build and deployment workflows;
- package manager lockfiles;
- architecture documents.

## Required Review

Protected-area changes require:

- owner review;
- explicit compatibility note;
- migration or rollback plan when applicable;
- validation evidence.

## Forbidden Agent Behavior

Agents must not:

- rewrite broad architecture without an approved proposal;
- hide contract changes inside feature PRs;
- combine formatting churn with business logic;
- remove tests to make a branch pass;
- create mock success paths for security, payment, or data integrity flows.
