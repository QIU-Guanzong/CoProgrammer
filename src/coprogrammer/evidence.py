"""Explicit local check receipts bound to working content and command hashes.

Receipts are unauthenticated local evidence. Ignored files, external inputs and
transient edits restored between observations are outside this boundary.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, collaboration as co, workspace as ws


def environment() -> dict:
    return {"tool_version": __version__, "python": platform.python_version(), "platform": sys.platform}


def command_digest(command: list[str]) -> str:
    if not isinstance(command, list) or not 1 <= len(command) <= 128:
        raise RuntimeError("check requires an explicit command argument vector")
    for arg in command:
        co.text(arg, "command argument", 4096, empty=True)
        if "\0" in arg:
            raise RuntimeError("invalid command argument")
    if not command[0].strip():
        raise RuntimeError("command executable is required")
    return ws.digest(command)


def _destination(cwd: Path, path: Path, label: str) -> Path:
    path = path.absolute()
    if path.is_symlink():
        raise RuntimeError("check output must not be a symlink")
    if path.resolve().is_relative_to(cwd):
        relative = path.resolve().relative_to(cwd).as_posix()
        if (ws.git(cwd, "ls-files", "--", relative).strip()
                or not ws.git(cwd, "check-ignore", "--no-index", "--", relative, optional=True).strip()):
            raise RuntimeError("check output must be ignored by Git or outside the repository")
    if path.exists():
        previous = ws.read_artifact(path)
        if previous.get("format") != "coprogrammer.check.v1" or previous.get("label") != label:
            raise RuntimeError("refusing to overwrite a different artifact")
    return path


def run(cwd: Path, command: list[str], label: str, output: Path, timeout_seconds: int = 300) -> dict:
    co.identity(label, "check label")
    co.bounded(timeout_seconds, "timeout_seconds", 3600)
    command_hash = command_digest(command)
    cwd = ws.root(cwd)
    output = _destination(cwd, output, label)
    subject = ws.snapshot(cwd)
    started_at = datetime.now(timezone.utc).isoformat()
    exit_code, timed_out, error = None, False, None
    try:
        # No shell interpretation, interactive input, output/argv persistence,
        # or provider invocation implicit in the recording operation.
        exit_code = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=sys.stderr, stderr=sys.stderr, timeout=timeout_seconds,
                                   check=False).returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        error = "command timed out; inspect any surviving child processes"
    except OSError:
        error = "command could not start"
    after = None
    try:
        after = ws.snapshot(cwd)["content"]["sha256"]
    except (RuntimeError, OSError):
        error = error or "workspace unavailable after command"
    record = {"format": "coprogrammer.check.v1", "label": label,
              "command_sha256": command_hash, "started_at": started_at,
              "finished_at": datetime.now(timezone.utc).isoformat(),
              "exit_code": exit_code, "timed_out": timed_out, "error": error,
              "subject": subject, "after_sha256": after,
              "stable": after == subject["content"]["sha256"], "environment": environment()}
    record["integrity_sha256"] = ws.digest(record)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".coprogrammer-check-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return record


def validate(record: object) -> dict:
    try:
        fields = {"format", "label", "command_sha256", "started_at", "finished_at", "exit_code", "timed_out", "error", "subject", "after_sha256", "stable", "environment", "integrity_sha256"}
        if not isinstance(record, dict) or set(record) != fields or record["format"] != "coprogrammer.check.v1":
            raise ValueError
        co.identity(record["label"], "check label")
        ws.validate_snapshot(record["subject"])
        if not ws.HASH.fullmatch(record["command_sha256"]) or not ws.HASH.fullmatch(record["integrity_sha256"]):
            raise ValueError
        if record["after_sha256"] is not None and not ws.HASH.fullmatch(record["after_sha256"]):
            raise ValueError
        if type(record["timed_out"]) is not bool or type(record["stable"]) is not bool:
            raise ValueError
        if record["exit_code"] is not None and (type(record["exit_code"]) is not int or not -2**31 <= record["exit_code"] < 2**31):
            raise ValueError
        if record["error"] is not None:
            co.text(record["error"], "check error", 256)
        if co.timestamp(record["finished_at"]) < co.timestamp(record["started_at"]):
            raise ValueError
        env = record["environment"]
        if set(env) != {"tool_version", "python", "platform"}:
            raise ValueError
        for value in env.values():
            co.text(value, "check environment", 64)
        if record["stable"] != (record["after_sha256"] == record["subject"]["content"]["sha256"]):
            raise ValueError
        if record["integrity_sha256"] != ws.digest({k: v for k, v in record.items() if k != "integrity_sha256"}):
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
        raise RuntimeError("invalid local check record or integrity mismatch") from exc
    return record


def verify(cwd: Path, path: Path, command: list[str] | None = None, *, current: dict | None = None,
           max_age_seconds: int = 86400) -> dict:
    co.bounded(max_age_seconds, "max_age_seconds", 604800)
    record = validate(ws.read_artifact(path))
    current = ws.snapshot(cwd) if current is None else current
    reasons = []
    age = (datetime.now(timezone.utc) - co.timestamp(record["finished_at"])).total_seconds()
    if age < 0:
        reasons.append("record_from_future")
    elif age > max_age_seconds:
        reasons.append("record_expired")
    if record["exit_code"] != 0 or record["timed_out"] or record["error"]:
        reasons.append("check_failed")
    if not record["stable"]:
        reasons.append("content_changed_during_check")
    if record["subject"]["content"]["sha256"] != current["content"]["sha256"]:
        reasons.append("content_changed")
    if not ws.same_repository(record["subject"], current):
        reasons.append("repository_changed")
    if record["environment"] != environment():
        reasons.append("environment_changed")
    if command is not None and command_digest(command) != record["command_sha256"]:
        reasons.append("command_changed")
    return {"format": "coprogrammer.check-status.v1", "label": record["label"],
            "fresh": not reasons, "reasons": reasons, "exit_code": record["exit_code"],
            "finished_at": record["finished_at"], "command_sha256": record["command_sha256"],
            "expected_command_checked": command is not None,
            "content_sha256": record["subject"]["content"]["sha256"],
            "note": "Unauthenticated local record; ignored files, dependencies and external inputs are not covered."}
