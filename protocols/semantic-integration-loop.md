# Semantic Integration Loop

Semantic integration means merging intent instead of blindly merging raw diffs.

## Source Branch Role

A source branch is evidence. It may contain:

- working implementation;
- failed experiments;
- useful tests;
- noisy rewrites;
- temporary debugging;
- accidental contract drift.

The branch digest decides which parts should survive.

## Integration Branch Role

An integration branch starts from latest `main` and rebuilds the smallest safe
patch using the digest as input.

## Integration Checklist

- [ ] Confirm branch intent.
- [ ] Preserve core insight.
- [ ] Drop unrelated refactors.
- [ ] Re-apply contract changes explicitly.
- [ ] Keep main branch architecture constraints.
- [ ] Run validation.
- [ ] Record human decisions.

## Merge Record

Every semantic integration should record:

- source branch;
- digest version;
- integration branch;
- decisions made;
- tests run;
- protocol updates needed.
