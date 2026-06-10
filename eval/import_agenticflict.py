"""Convert AgenticFlict dataset records into eval case JSON files.

AgenticFlict (arXiv:2604.03551, Zenodo DOI 10.5281/zenodo.19396917) is a
large-scale dataset of textual merge conflicts in AI coding agent pull
requests, derived from the AIDev dataset. Used here under its published terms;
see ACKNOWLEDGMENTS.md.

This importer reads the *PullRequest-level* table (CSV or JSONL; Parquet if
pandas+pyarrow are installed) downloaded from Zenodo, filters it, and writes
one case JSON per PR for run_eval.py.

The dataset identifies each PR by `repo_full_name` + `pr_number` and anchors
the merge simulation with `baseRefOid` / `headRefOid`. PR head commits are
often not reachable from default clone refs, so each case records
`fetch_refs: ["pull/<n>/head"]` which run_eval.py fetches before merging.

Usage:
    python eval/import_agenticflict.py \
      --input pull_requests.csv \
      --out eval/cases \
      --only-conflicting --limit 50 \
      --max-conflict-files 10

Notes:
- Download the dataset manually from Zenodo first; this script never touches
  the network.
- Column names vary slightly between raw/clean releases; aliases below cover
  the documented names. Use --column to add overrides, e.g.
  --column head_oid=head_sha.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "repo_full_name": ("repo_full_name", "repository", "repo", "repo_name"),
    "pr_number": ("pr_number", "number", "pull_number"),
    "pr_key": ("pr_key",),
    "base_oid": ("baseRefOid", "base_ref_oid", "base_oid", "base_sha", "base_commit"),
    "head_oid": ("headRefOid", "head_ref_oid", "head_oid", "head_sha", "head_commit"),
    "is_conflict": ("is_conflict", "has_conflict", "merge_outcome", "conflict"),
    "num_conflict_files": ("num_conflict_files", "conflict_files"),
    "num_conflict_regions": ("num_conflict_regions", "conflict_regions"),
    "conflict_lines": ("conflict_lines", "num_conflict_lines", "total_conflict_lines"),
    "language": ("language", "primary_language", "repo_language"),
    "agent": ("agent", "ai_agent", "agent_name"),
}


def resolve_column(record: dict, key: str, overrides: dict[str, str]) -> str | None:
    if key in overrides and overrides[key] in record:
        value = record[overrides[key]]
        return None if value is None else str(value)
    for alias in COLUMN_ALIASES.get(key, (key,)):
        if alias in record and record[alias] not in (None, ""):
            return str(record[alias])
    return None


def is_conflicting(record: dict, overrides: dict[str, str]) -> bool:
    value = resolve_column(record, "is_conflict", overrides)
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "merge_conflict", "conflict")


def iter_records(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)
    elif suffix in (".jsonl", ".ndjson"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        yield from (data if isinstance(data, list) else data.get("records", []))
    elif suffix == ".parquet":
        try:
            import pandas  # type: ignore
        except ImportError:
            sys.exit("parquet input requires: pip install pandas pyarrow")
        frame = pandas.read_parquet(path)
        yield from (row.to_dict() for _, row in frame.iterrows())
    else:
        sys.exit(f"unsupported input format: {path.suffix}")


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()


def to_case(record: dict, overrides: dict[str, str]) -> dict | None:
    repo = resolve_column(record, "repo_full_name", overrides)
    pr_number = resolve_column(record, "pr_number", overrides)
    if (repo is None or pr_number is None) and (
        key := resolve_column(record, "pr_key", overrides)
    ):
        # pr_key has the form owner/repository#number
        repo, _, pr_number = key.partition("#")
    base_oid = resolve_column(record, "base_oid", overrides)
    head_oid = resolve_column(record, "head_oid", overrides)
    if not repo or not pr_number or not base_oid:
        return None

    case = {
        "id": f"agenticflict-{slugify(repo)}-{pr_number}",
        "repo": f"https://github.com/{repo}.git",
        "base_ref": base_oid,
        "branches": [head_oid] if head_oid else [],
        "fetch_refs": [f"pull/{pr_number}/head"],
        "language": resolve_column(record, "language", overrides) or "",
        "labels": {"core_contributions": [], "noise": []},
        "source": "agenticflict",
        "notes": json.dumps(
            {
                "pr": f"https://github.com/{repo}/pull/{pr_number}",
                "agent": resolve_column(record, "agent", overrides),
                "num_conflict_files": resolve_column(
                    record, "num_conflict_files", overrides
                ),
                "num_conflict_regions": resolve_column(
                    record, "num_conflict_regions", overrides
                ),
                "conflict_lines": resolve_column(record, "conflict_lines", overrides),
            },
            ensure_ascii=False,
        ),
    }
    return case


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="PR-level table from Zenodo.")
    parser.add_argument("--out", required=True, help="Output cases directory.")
    parser.add_argument("--limit", type=int, default=0, help="Max cases (0 = all).")
    parser.add_argument(
        "--only-conflicting",
        action="store_true",
        help="Keep only PRs labelled as conflicting.",
    )
    parser.add_argument(
        "--language", help="Keep only this primary language (case-insensitive)."
    )
    parser.add_argument(
        "--max-conflict-files",
        type=int,
        default=0,
        help="Skip PRs with more conflicting files than this (0 = no cap).",
    )
    parser.add_argument(
        "--column",
        action="append",
        default=[],
        help="Column override key=actual_name (repeatable).",
    )
    args = parser.parse_args()

    overrides: dict[str, str] = {}
    for item in args.column:
        key, _, actual = item.partition("=")
        if not actual:
            sys.exit(f"--column expects key=actual_name, got: {item}")
        overrides[key] = actual

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    for record in iter_records(Path(args.input).resolve()):
        if args.only_conflicting and not is_conflicting(record, overrides):
            continue
        if args.language:
            language = resolve_column(record, "language", overrides) or ""
            if language.lower() != args.language.lower():
                continue
        if args.max_conflict_files:
            files = resolve_column(record, "num_conflict_files", overrides)
            if files and files.replace(".", "", 1).isdigit():
                if float(files) > args.max_conflict_files:
                    continue
        case = to_case(record, overrides)
        if case is None:
            skipped += 1
            continue
        (out / f"{case['id']}.json").write_text(
            json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        written += 1
        if args.limit and written >= args.limit:
            break

    print(f"written: {written} cases -> {out}")
    if skipped:
        print(f"skipped (missing repo/pr/base fields): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
