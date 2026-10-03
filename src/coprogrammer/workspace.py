"""Bounded, content-based Git workspace observations; no fetch or file writes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__

MAX_FILES = 10000
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024
HASH = re.compile(r"^[0-9a-f]{64}$")
OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git(cwd: Path, *args: str, optional: bool = False) -> bytes:
    # Explicit cwd wins over inherited Git redirection variables.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True,
                                timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("cannot inspect Git workspace") from exc
    if len(result.stdout) > 2_000_000:
        raise RuntimeError("Git workspace metadata exceeds supported size")
    if result.returncode:
        if optional:
            return b""
        raise RuntimeError("cannot inspect Git workspace; check repository and revision")
    return result.stdout


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise RuntimeError("workspace paths must be valid UTF-8") from exc


def root(cwd: Path) -> Path:
    return Path(decode(git(cwd, "rev-parse", "--show-toplevel")).strip()).resolve()


def revision(cwd: Path, ref: str) -> str:
    if (not isinstance(ref, str) or not ref.strip() or len(ref) > 512
            or ref.startswith("-") or any(ord(c) < 32 for c in ref)):
        raise RuntimeError("invalid workspace revision")
    return decode(git(cwd, "rev-parse", "--verify", f"{ref}^{{commit}}")).strip()


def origin_identity(value: str) -> str | None:
    """Drop credentials, query strings and local filesystem paths."""
    if "://" in value:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return None
        if parsed.scheme not in ("https", "http", "ssh", "git") or not parsed.hostname:
            return None
        host, path = parsed.hostname.casefold(), parsed.path
    else:
        match = re.fullmatch(r"(?:[^/@:]+@)?([^/:]+):(.+)", value)
        if not match or len(match[1]) == 1:  # Windows drive, not an SSH host
            return None
        host, path = match[1].casefold(), match[2]
    path = path.strip("/").removesuffix(".git")
    return f"{host}/{path}" if path else None


def changed_paths(cwd: Path) -> list[str]:
    entries = decode(git(cwd, "status", "--porcelain=v1", "-z", "--untracked-files=all")).split("\0")
    paths, i = [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise RuntimeError("invalid Git status record")
        paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if i >= len(entries) or not entries[i]:
                raise RuntimeError("invalid Git rename record")
            paths.append(entries[i])
            i += 1
    return sorted(set(paths))


def _content(cwd: Path) -> dict:
    modes = {}
    for row in decode(git(cwd, "ls-files", "--stage", "-z")).split("\0"):
        if not row:
            continue
        meta, name = row.split("\t", 1)
        mode, _, stage = meta.split()
        if stage != "0":
            raise RuntimeError("workspace has unresolved index conflicts")
        if mode == "160000":
            raise RuntimeError("content snapshots do not support submodules")
        modes[name] = mode
    for name in decode(git(cwd, "ls-files", "--others", "--exclude-standard", "-z")).split("\0"):
        if name:
            modes.setdefault(name, "100644")
    if len(modes) > MAX_FILES:
        raise RuntimeError("workspace exceeds content snapshot file limit")
    filemode = decode(git(cwd, "config", "--get", "core.filemode", optional=True)).strip() == "true"
    rows, total = [], 0
    for name, mode in sorted(modes.items()):
        path = cwd / name
        if not path.parent.resolve().is_relative_to(cwd):
            raise RuntimeError("workspace path escapes repository")
        # Directory symlinks are an external input, not a covered file tree.
        if any(parent.is_symlink() for parent in path.parents if parent != cwd and parent.is_relative_to(cwd)):
            raise RuntimeError("workspace contains a symlink directory")
        try:
            before = path.lstat()
        except FileNotFoundError:
            continue  # a deleted file also disappears after its deletion is committed
        if stat.S_ISLNK(before.st_mode):
            data = os.fsencode(os.readlink(path))
            mode = "120000"
        elif stat.S_ISREG(before.st_mode):
            if before.st_size > MAX_FILE_BYTES or total + before.st_size > MAX_TOTAL_BYTES:
                raise RuntimeError("workspace exceeds content snapshot byte limit")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(path, flags), "rb") as handle:
                opened = os.fstat(handle.fileno())
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    raise RuntimeError("workspace changed during observation")
                data = handle.read(MAX_FILE_BYTES + 1)
            if filemode:
                mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        else:
            raise RuntimeError("workspace contains an unsupported special file")
        after = path.lstat()
        if (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RuntimeError("workspace changed during observation")
        total += len(data)
        if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise RuntimeError("workspace exceeds content snapshot byte limit")
        rows.append([name, mode, hashlib.sha256(data).hexdigest()])
    return {"sha256": digest(rows), "files": len(rows), "bytes": total}


def snapshot(cwd: Path, base: str = "HEAD") -> dict:
    cwd = root(cwd)

    def observe():
        head = revision(cwd, "HEAD")
        branch = decode(git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD", optional=True)).strip() or "HEAD"
        base_head = revision(cwd, base)
        counts = decode(git(cwd, "rev-list", "--left-right", "--count", f"{base_head}...{head}")).split()
        changes = changed_paths(cwd)
        shallow = decode(git(cwd, "rev-parse", "--is-shallow-repository")).strip() == "true"
        roots = [] if shallow else sorted(decode(git(cwd, "rev-list", "--max-parents=0", head)).splitlines())
        if len(roots) > 128:
            raise RuntimeError("workspace exceeds repository lineage limit")
        remote = decode(git(cwd, "config", "--get", "remote.origin.url", optional=True)).strip()
        return {"format": "coprogrammer.workspace.v1", "tool_version": __version__,
                "repository": {"origin": origin_identity(remote), "roots": roots, "shallow": shallow},
                "head": head, "branch": branch,
                "base": {"ref": base, "head": base_head, "behind": int(counts[0]), "ahead": int(counts[1])},
                "content": _content(cwd),
                "dirty": {"count": len(changes), "paths": changes[:200], "omitted": max(0, len(changes) - 200)}}

    first, second = observe(), observe()
    if first != second:
        raise RuntimeError("workspace changed during observation; retry when stable")
    return second


def read_artifact(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise RuntimeError("artifact must be a bounded regular JSON file")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("non-finite JSON number")

    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_ARTIFACT_BYTES + 1)
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("oversized artifact")
        data = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        if not isinstance(data, dict):
            raise ValueError("expected object")
        return data
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RuntimeError("invalid artifact JSON") from exc


def validate_snapshot(value: object) -> dict:
    """Validate portable input before comparing it or using its revision."""
    try:
        if not isinstance(value, dict) or set(value) != {"format", "tool_version", "repository", "head", "branch", "base", "content", "dirty"}:
            raise ValueError
        if value["format"] != "coprogrammer.workspace.v1" or not OID.fullmatch(value["head"]):
            raise ValueError
        for key in ("tool_version", "branch"):
            if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 512 or any(ord(c) < 32 for c in value[key]):
                raise ValueError
        repo, base, content, dirty = (value[k] for k in ("repository", "base", "content", "dirty"))
        if set(repo) != {"origin", "roots", "shallow"} or type(repo["shallow"]) is not bool:
            raise ValueError
        if repo["origin"] is not None and (not isinstance(repo["origin"], str) or not 1 <= len(repo["origin"]) <= 4096):
            raise ValueError
        if not isinstance(repo["roots"], list) or len(repo["roots"]) > 128 or any(not OID.fullmatch(v) for v in repo["roots"]):
            raise ValueError
        if set(base) != {"ref", "head", "ahead", "behind"} or not OID.fullmatch(base["head"]):
            raise ValueError
        if not isinstance(base["ref"], str) or not 1 <= len(base["ref"]) <= 512 or base["ref"].startswith("-") or any(ord(c) < 32 for c in base["ref"]):
            raise ValueError
        if set(content) != {"sha256", "files", "bytes"} or not HASH.fullmatch(content["sha256"]):
            raise ValueError
        for item, key, maximum in ((base, "ahead", 10**12), (base, "behind", 10**12),
                                   (content, "files", MAX_FILES), (content, "bytes", MAX_TOTAL_BYTES),
                                   (dirty, "count", 10**12), (dirty, "omitted", 10**12)):
            if type(item[key]) is not int or not 0 <= item[key] <= maximum:
                raise ValueError
        if set(dirty) != {"count", "paths", "omitted"} or not isinstance(dirty["paths"], list) or len(dirty["paths"]) > 200:
            raise ValueError
        if dirty["count"] != len(dirty["paths"]) + dirty["omitted"]:
            raise ValueError
        if any(not isinstance(p, str) or not p or len(p) > 4096 or Path(p).is_absolute() or ".." in Path(p).parts for p in dirty["paths"]):
            raise ValueError
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise RuntimeError("invalid workspace snapshot") from exc
    return value


def same_repository(left: dict, right: dict) -> bool:
    a, b = left["repository"], right["repository"]
    if a["roots"] and b["roots"]:
        return set(a["roots"]) == set(b["roots"])
    return left["head"] == right["head"] or bool(a["origin"] and a["origin"] == b["origin"])
