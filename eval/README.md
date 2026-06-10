# Evaluation Harness

See `docs/EVAL_PLAN.md` for methodology. This directory holds the runnable
harness.

## Layout

```text
eval/
├── README.md                 this file
├── make_synthetic_case.py    build tiny git repos with conflicting branches
├── import_agenticflict.py    convert AgenticFlict records into case files
├── run_eval.py               run merge conditions over cases, emit results
├── cases/                    one JSON file per case
└── results/                  JSONL outputs (gitignored)
```

## Case Schema

```json
{
  "id": "synthetic-001",
  "repo": "/abs/path/or/clone-url",
  "base_ref": "<sha or branch of main at conflict time>",
  "branches": ["<sha or branch>", "..."],
  "fetch_refs": ["pull/612/head"],
  "validate_cmd": "python -m pytest -q",
  "language": "python",
  "labels": {
    "core_contributions": ["short description per core change"],
    "noise": ["short description per noise change"]
  },
  "source": "synthetic | agenticflict",
  "notes": ""
}
```

Optional fields: `fetch_refs` (refs to fetch before merging — required for
GitHub PR head OIDs not reachable from a plain clone) and `validate_cmd`
(run after a textually clean merge; a failure is recorded as
`semantic_regression`, the conflict class textual merge cannot see).

## Quick Start (synthetic smoke test)

```bash
python eval/make_synthetic_case.py --out /tmp/coprog-eval
python eval/run_eval.py --cases /tmp/coprog-eval/cases --condition raw_merge
```

Expected output: a per-case record showing whether plain `git merge` of each
branch conflicts, the conflicting files, and aggregate stats.

Expected output: synthetic-001 conflicts on `src/util.py`; synthetic-002
merges clean but fails `validate_cmd` (`semantic_regression: true`).

## Importing AgenticFlict

1. Download the dataset from Zenodo (DOI 10.5281/zenodo.19396917) — the
   importer never touches the network.
2. Convert the PR-level table:

   ```bash
   python eval/import_agenticflict.py \
     --input path/to/pull_requests.csv \
     --out eval/cases \
     --only-conflicting --limit 50 --max-conflict-files 10
   ```

3. Run the baseline: `python eval/run_eval.py --cases eval/cases --condition raw_merge`

Column names differ slightly across releases; use `--column key=actual_name`
overrides if the defaults miss (keys: repo_full_name, pr_number, base_oid,
head_oid, is_conflict, num_conflict_files, language, agent).

First results: `docs/EVAL_REPORT_2026-06-10.md`.
