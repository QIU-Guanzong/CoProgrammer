"""Run merge-evaluation conditions over case files.

Conditions:
  raw_merge           sequentially merge each branch into base; record conflicts.
  digest_integration  placeholder: emits the CoProgrammer commands a human/agent
                      should run; metrics recorded manually for now.

Usage:
    python eval/run_eval.py --cases eval/cases --condition raw_merge
    python eval/run_eval.py --cases /tmp/coprog-eval/cases --condition raw_merge
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, text=True, capture_output=True
    )


def clone_at(repo: str, base_ref: str, workdir: Path, fetch_refs: list[str]) -> Path:
    target = workdir / "repo"
    run_git(["clone", "--quiet", repo, str(target)], cwd=workdir)
    run_git(["config", "user.email", "eval@coprogrammer.local"], cwd=target)
    run_git(["config", "user.name", "CoProgrammer Eval"], cwd=target)
    for ref in fetch_refs:
        # e.g. "pull/612/head" for GitHub PR heads not reachable from clones
        run_git(["fetch", "--quiet", "origin", ref], cwd=target, check=False)
    run_git(["checkout", "--quiet", base_ref], cwd=target)
    run_git(["checkout", "--quiet", "-b", "eval-base"], cwd=target)
    return target


def resolve_merge_ref(repo: Path, branch: str) -> str | None:
    """Resolve a branch name or commit OID to something git merge accepts."""
    for candidate in (branch, f"origin/{branch}"):
        result = run_git(
            ["rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            cwd=repo,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return None


def run_validation(repo: Path, command: str | None) -> dict | None:
    """Run the case's validation command to catch semantic (test) regressions."""
    if not command:
        return None
    result = subprocess.run(
        command, cwd=repo, shell=True, text=True, capture_output=True
    )
    return {
        "command": command,
        "passed": result.returncode == 0,
        "stderr": result.stderr.strip()[:500],
    }


def conflicted_files(repo: Path) -> list[str]:
    result = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=repo)
    return [line for line in result.stdout.splitlines() if line.strip()]


def raw_merge_case(case: dict) -> dict:
    record: dict = {
        "case": case["id"],
        "condition": "raw_merge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "merges": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        repo = clone_at(
            case["repo"],
            case["base_ref"],
            workdir,
            case.get("fetch_refs", []),
        )
        for branch in case["branches"]:
            ref = resolve_merge_ref(repo, branch)
            if ref is None:
                record["merges"].append(
                    {
                        "branch": branch,
                        "status": "error",
                        "conflicts": [],
                        "stderr": "unresolvable ref (missing fetch_refs?)",
                    }
                )
                continue
            merge = run_git(["merge", "--no-edit", ref], cwd=repo, check=False)
            if merge.returncode == 0:
                record["merges"].append(
                    {"branch": branch, "status": "clean", "conflicts": []}
                )
                continue
            conflicts = conflicted_files(repo)
            if conflicts:
                record["merges"].append(
                    {"branch": branch, "status": "conflict", "conflicts": conflicts}
                )
            else:
                record["merges"].append(
                    {
                        "branch": branch,
                        "status": "error",
                        "conflicts": [],
                        "stderr": merge.stderr.strip()[:500],
                    }
                )
            run_git(["merge", "--abort"], cwd=repo, check=False)

        record["clean_merge_count"] = sum(
            1 for merge in record["merges"] if merge["status"] == "clean"
        )
        record["conflict_merge_count"] = sum(
            1 for merge in record["merges"] if merge["status"] == "conflict"
        )
        record["error_merge_count"] = sum(
            1 for merge in record["merges"] if merge["status"] == "error"
        )
        textually_clean = (
            record["conflict_merge_count"] == 0 and record["error_merge_count"] == 0
        )
        # A textually clean merge can still be semantically broken; the case's
        # validate_cmd (e.g. import check or test suite) is the judge.
        record["validation"] = (
            run_validation(repo, case.get("validate_cmd")) if textually_clean else None
        )
    validation = record["validation"]
    record["auto_resolved"] = textually_clean and (
        validation is None or validation["passed"]
    )
    record["semantic_regression"] = bool(validation) and not validation["passed"]
    return record


def digest_integration_case(case: dict) -> dict:
    """Emit the human-in-the-loop protocol for this case (recorded run)."""
    commands = [
        f"git clone {case['repo']} work && cd work && git checkout {case['base_ref']}",
    ]
    for branch in case["branches"]:
        commands.extend(
            [
                f"python -m coprogrammer digest --base {case['base_ref']} --head {branch}",
                "# fill branch intent / core contribution / noise in the digest",
                "# write integration-plan.json (preserve/drop/rebuild decisions)",
                "python -m coprogrammer integration-plan validate integration-plan.json",
                "# rebuild minimal patch on eval-base; run tests; record outcome",
            ]
        )
    return {
        "case": case["id"],
        "condition": "digest_integration",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "manual_protocol_emitted",
        "protocol": commands,
        "labels": case.get("labels", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, help="Directory of case JSON files.")
    parser.add_argument(
        "--condition",
        default="raw_merge",
        choices=("raw_merge", "digest_integration"),
    )
    parser.add_argument(
        "--results",
        default=str(Path(__file__).parent / "results"),
        help="Directory for JSONL results.",
    )
    args = parser.parse_args()

    cases_dir = Path(args.cases).resolve()
    case_files = sorted(cases_dir.glob("*.json"))
    if not case_files:
        print(f"no case files found in {cases_dir}")
        return 2

    results_dir = Path(args.results).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = results_dir / f"{args.condition}-{stamp}.jsonl"

    records = []
    for case_file in case_files:
        case = json.loads(case_file.read_text(encoding="utf-8"))
        if args.condition == "raw_merge":
            record = raw_merge_case(case)
        else:
            record = digest_integration_case(case)
        records.append(record)
        print(json.dumps(record, ensure_ascii=False))

    with out_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    if args.condition == "raw_merge":
        total = len(records)
        auto = sum(1 for record in records if record["auto_resolved"])
        semantic = sum(1 for record in records if record.get("semantic_regression"))
        print(f"\ncases: {total}; auto-resolved by raw merge: {auto} ({auto / total:.0%})")
        print(f"textually clean but semantically broken: {semantic}")
    print(f"results: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
