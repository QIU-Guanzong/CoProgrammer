# Eval Report — Harness Bring-Up (2026-06-10)

Status: harness validated on synthetic cases. AgenticFlict import pending
dataset download (Zenodo DOI 10.5281/zenodo.19396917).

## What Was Run

Condition `raw_merge` over 2 synthetic cases (`eval/make_synthetic_case.py`),
each with 2 agent branches merged sequentially into the base.

| Case | Design | Raw merge result | Semantic check |
| --- | --- | --- | --- |
| synthetic-001 | Textual conflict (both agents edit `fetch()`) + noise (whole-file reformat) | agent-a clean, agent-b **conflict** on `src/util.py` | n/a (blocked at conflict) |
| synthetic-002 | No textual overlap: agent-a renames `parse`→`parse_json`; agent-b adds new file importing old `parse` | both merges **clean** | **FAILED** — `ImportError: cannot import name 'parse'` |

Aggregate: auto-resolved by raw merge 0/2 (0%); textually clean but
semantically broken: 1.

## Why This Matters

synthetic-002 is the case class that motivates CoProgrammer: Git (and any
purely textual merge queue) reports success, yet the merged tree is broken.
Detection requires either (a) post-merge validation, or (b) contract-change
awareness *before* merge — agent-a's rename is exactly a
`contract.change.proposed (shared_type, breaking?)` event, which
`coprogrammer manager forecast` would have flagged while both agents were
still coding. This is also the band AgentSpawn attributes to "semantic merge"
(73% of their conflict triage).

## AgenticFlict Context (from the paper, arXiv:2604.03551)

- 107,026 PRs simulated; conflict rate **27.67%** (29,609 PRs);
- per conflicting PR: mean 4.36 files / 11.36 regions / 540 conflict lines
  (median 2 files — most conflicts are localized; a heavy tail is large);
- 5 agents, 59,412 repos; merge anchored at `baseRefOid`/`headRefOid`.

Implication for our subset selection: stratify by conflict-file count; the
median-2-files majority should be cheap for `digest_integration`, the heavy
tail is where insight-preserving rebuild matters most.

## Next Steps

1. Download the Zenodo artifact; run
   `python eval/import_agenticflict.py --input <pr_table> --out eval/cases --only-conflicting --limit 50 --max-conflict-files 10`.
2. Run `raw_merge` over the imported cases for the real baseline.
3. Annotate core contributions / noise for a 20-case pilot subset.
4. Run the human-in-the-loop `digest_integration` condition on the pilot;
   record reviewer minutes.
5. Publish `EVAL_REPORT_<date>` with the metric table from `docs/EVAL_PLAN.md`.
