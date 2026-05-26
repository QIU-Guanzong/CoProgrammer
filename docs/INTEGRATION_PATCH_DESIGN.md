# Integration Patch Design

Last updated: 2026-05-26

## Goal

Integration Patch Bot should not directly merge an agent branch. It should
rebuild the smallest safe patch from latest `main`, using the branch digest,
contract board, decision records, and validation results as inputs.

## Research Synthesis

Sourcegraph Batch Changes is the strongest reference for desired-state
reconciliation: a batch spec can be previewed, applied, and later updated so
changesets match the new desired state.

OpenRewrite shows the value of deterministic recipes and semantic trees for
large-scale automated refactoring.

Comby and Grit show that structural search/replace and declarative
transformations can cover many patch cases without asking an LLM to improvise
over raw text.

SemanticMerge shows that language-aware merge still matters, but CoProgrammer
should not stop at structural merge. It should decide which branch insight is
worth rebuilding under current main constraints.

Reviewdog and SARIF show that findings should have a machine-readable format
that can be reported locally, in PR comments, in checks, or later through code
scanning integrations.

## Integration Flow

1. Read branch digest.
2. Read open contract changes and required decisions.
3. Create an integration plan JSON artifact.
4. Human approves or edits the integration plan.
5. Create integration branch from latest `main`.
6. Apply patch primitives in the safest order.
7. Run validation.
8. Write an integration record.
9. Open integration PR.
10. Existing merge queue validates final landing state.

## Patch Primitive Order

Prefer deterministic transformations before LLM patch generation:

| Priority | Primitive | Use When |
| --- | --- | --- |
| 1 | manual | Small, sensitive, or architecture-heavy changes |
| 2 | recipe | OpenRewrite/Grit-style codemod already exists |
| 3 | structural_search_replace | Pattern is local and syntax-aware |
| 4 | cherry_pick | Source commit is clean and already minimal |
| 5 | git_apply | Patch is narrow and applies cleanly |
| 6 | llm_patch | Intent is clear but implementation must be reconstructed |

The bot should stop and request a human decision when a primitive touches
protected paths, changes contracts, or fails validation in a surprising way.

## Required Artifact

The integration plan should be machine-readable:

- `schemas/integration-plan.schema.json`
- `templates/integration-plan.json`
- `coprogrammer integration-plan validate`

The Markdown `templates/integration-plan.md` can remain reviewer-friendly, but
the JSON artifact should be the source of truth for automation.

## Safety Rules

- Never rewrite `main`.
- Never approve its own architecture, auth, payment, migration, or contract
  decisions.
- Never hide dropped changes; every dropped idea must appear in the integration
  plan or integration record.
- Never treat test pass as product approval.
- Always preserve source branch, source head, main baseline, and validation
  commands.

## MVP Slice

The first implementation does not need full automatic patching.

Build this order:

1. validate integration plan JSON;
2. generate integration plan from branch digest;
3. create integration branch from latest main;
4. apply only `git_apply` and `manual` placeholders;
5. write integration record;
6. leave `recipe`, `structural_search_replace`, and `llm_patch` as explicit
   future primitives.

## Sources

- [Sourcegraph Batch Changes](https://sourcegraph.com/docs/batch_changes)
- [Sourcegraph: Updating a batch change](https://sourcegraph.com/docs/batch_changes/how-tos/updating_a_batch_change)
- [OpenRewrite Docs](https://docs.openrewrite.org/)
- [OpenRewrite Recipes](https://docs.openrewrite.org/concepts-and-explanations/recipes)
- [Comby](https://comby.dev/)
- [Grit Docs](https://docs.grit.io/)
- [GritQL](https://docs.grit.io/language/overview)
- [SemanticMerge](https://www.semanticmerge.com/documentation/intro-guide/semanticmerge-intro-guide)
- [reviewdog](https://github.com/reviewdog/reviewdog)
- [GitHub SARIF support](https://docs.github.com/en/code-security/reference/code-scanning/sarif-support-for-code-scanning)
