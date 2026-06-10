"""Build synthetic merge-conflict cases for harness development.

Creates a tiny git repository with a main branch and two agent branches that
conflict both textually (same lines) and semantically (one branch renames a
shared helper the other branch starts using). Emits a case JSON consumable by
run_eval.py.

Usage:
    python eval/make_synthetic_case.py --out /tmp/coprog-eval
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        args, cwd=cwd, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def git(cwd: Path, *args: str) -> str:
    return run(["git", *args], cwd)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_repo(repo: Path) -> dict:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "--initial-branch", "main")
    git(repo, "config", "user.email", "eval@coprogrammer.local")
    git(repo, "config", "user.name", "CoProgrammer Eval")

    write(
        repo / "src/util.py",
        "def fetch(url):\n    return url\n\n\ndef parse(data):\n    return data\n",
    )
    write(repo / "src/app.py", "from src.util import fetch\n\n\ndef main():\n    return fetch('x')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "initial")
    base_sha = git(repo, "rev-parse", "HEAD")

    # Agent A: adds retry logic to fetch (core contribution) and reformats
    # the whole util module (noise).
    git(repo, "checkout", "-b", "agent-a", base_sha)
    write(
        repo / "src/util.py",
        '"""Utilities (reformatted)."""\n\n\n'
        "def fetch(url, retries=3):\n"
        "    for _ in range(retries):\n"
        "        result = url\n"
        "        if result:\n"
        "            return result\n"
        "    return None\n\n\n"
        "def parse(data):\n    return data\n",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "agent-a: add retry logic to fetch; reformat util")

    # Agent B: renames parse -> parse_json (contract change) and edits the
    # same fetch lines (textual conflict with agent A).
    git(repo, "checkout", "main")
    git(repo, "checkout", "-b", "agent-b", base_sha)
    write(
        repo / "src/util.py",
        "def fetch(url, timeout=10):\n    return url\n\n\ndef parse_json(data):\n    return data\n",
    )
    write(
        repo / "src/app.py",
        "from src.util import fetch, parse_json\n\n\ndef main():\n    return parse_json(fetch('x'))\n",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "agent-b: rename parse to parse_json; add timeout")

    git(repo, "checkout", "main")
    return {
        "base_sha": base_sha,
        "branches": ["agent-a", "agent-b"],
    }


def build_repo_clean_but_broken(repo: Path) -> dict:
    """Case 002: both branches merge textually clean, but the result is broken.

    Agent A renames parse -> parse_json (updating the only existing caller).
    Agent B adds a *new* file that imports the old `parse` name. Git sees no
    overlapping edits, so the merge is clean — and the merged tree fails on
    import. This is the semantic-conflict class that textual merge cannot see.
    """
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "--initial-branch", "main")
    git(repo, "config", "user.email", "eval@coprogrammer.local")
    git(repo, "config", "user.name", "CoProgrammer Eval")

    write(repo / "src/__init__.py", "")
    write(repo / "src/util.py", "def parse(data):\n    return data\n")
    write(repo / "src/app.py", "from src.util import parse\n\n\ndef main():\n    return parse('x')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "initial")
    base_sha = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "-b", "agent-a", base_sha)
    write(repo / "src/util.py", "def parse_json(data):\n    return data\n")
    write(
        repo / "src/app.py",
        "from src.util import parse_json\n\n\ndef main():\n    return parse_json('x')\n",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "agent-a: rename parse to parse_json")

    git(repo, "checkout", "main")
    git(repo, "checkout", "-b", "agent-b", base_sha)
    write(
        repo / "src/consumer.py",
        "from src.util import parse\n\n\ndef consume():\n    return parse('y')\n",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "agent-b: add consumer using parse")

    git(repo, "checkout", "main")
    return {"base_sha": base_sha, "branches": ["agent-a", "agent-b"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output directory.")
    args = parser.parse_args()

    out = Path(args.out).resolve()

    repo_001 = out / "repos/synthetic-001"
    info_001 = build_repo(repo_001)
    case_001 = {
        "id": "synthetic-001",
        "repo": str(repo_001),
        "base_ref": info_001["base_sha"],
        "branches": info_001["branches"],
        "language": "python",
        "labels": {
            "core_contributions": [
                "fetch retry logic (agent-a)",
                "fetch timeout parameter (agent-b)",
                "parse -> parse_json rename with call-site update (agent-b)",
            ],
            "noise": ["whole-file reformat of src/util.py (agent-a)"],
        },
        "source": "synthetic",
        "notes": "Textual conflict on fetch(); semantic conflict via rename.",
    }

    repo_002 = out / "repos/synthetic-002"
    info_002 = build_repo_clean_but_broken(repo_002)
    case_002 = {
        "id": "synthetic-002",
        "repo": str(repo_002),
        "base_ref": info_002["base_sha"],
        "branches": info_002["branches"],
        "language": "python",
        "validate_cmd": "python -c 'import src.app, src.consumer'",
        "labels": {
            "core_contributions": [
                "parse -> parse_json rename with call-site update (agent-a)",
                "new consumer module (agent-b)",
            ],
            "noise": [],
        },
        "source": "synthetic",
        "notes": (
            "Textually clean merge that is semantically broken: agent-b's new "
            "file imports a name agent-a renamed. Raw merge reports success; "
            "validate_cmd exposes the regression."
        ),
    }

    for case in (case_001, case_002):
        case_path = out / f"cases/{case['id']}.json"
        write(case_path, json.dumps(case, indent=2, ensure_ascii=False) + "\n")
        print(f"case: {case_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
