"""Explicit task-only Claude Code adapter; native authorization stays unchanged."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .codex_harness import _json_loads, _probe_command
from .runner import MAX_RESULT_BYTES

ACCESS_TOOLS = {"read-only": "Read,Glob,Grep", "workspace-write": "Read,Glob,Grep,Edit,Write"}
REQUIRED_FLAGS = ("--json-schema", "--tools", "--output-format", "--strict-mcp-config",
                  "--mcp-config", "--disallowedTools", "--no-session-persistence", "--max-turns")


def check(executable: str, access: str = "read-only", *, probe_native: bool = False) -> dict:
    """Default discovery only; optional trusted local declarations/auth status."""
    _options(executable, access)
    if not isinstance(probe_native, bool):
        raise RuntimeError("probe_native must be boolean")
    found = shutil.which(executable)
    report = {"format": "coprogrammer.claude-harness-check.v1", "client": "claude",
            "executable": {"requested": executable, "resolved": str(Path(found).absolute()) if found else None,
                           "status": "available" if found else "unavailable"},
            "task_supported": True, "task_access": access, "inbox_supported": False,
            "native_version": "not_checked", "native_configuration": "not_checked",
            "model_connection": "not_checked", "network_used": False,
            "next_step": ("Review the native version and existing authorized configuration, queue a scoped task and preview worker run. Receive messages explicitly through the existing client/MCP workflow."
                          if found else "Install Claude Code through official instructions or select its trusted path with --executable; this check does not install or authenticate.")}
    report["native_probe"] = {"status": "not_requested"}
    if not probe_native:
        return report
    report["network_used"] = "native_behavior_not_inspected"
    report["native_configuration"] = "native_status_only"
    if not found:
        report["native_probe"] = {"status": "unavailable", "reason": "executable_unavailable"}
        return report
    version, text = _probe_command([found, "--version"])
    match = re.fullmatch(r"([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?) \(Claude Code\)", text.strip()) if text else None
    if match and len(match[1]) <= 80:
        report["native_version"] = match[1]
        version["status"] = "reported"
    elif text is not None:
        version.update(status="unknown", reason="unrecognized_version")
    help_result, text = _probe_command([found, "--help"])
    if text is not None:
        declared = set(re.findall(r"(?<!\S)(--[A-Za-z][A-Za-z0-9-]*)(?=[\s,=]|$)", text))
        missing = [flag for flag in REQUIRED_FLAGS if flag not in declared]
        help_result.update(status="advertised" if not missing else "unknown", missing_flags=missing)
    auth, text = _probe_command([found, "auth", "status"], accepted_exit_codes=(0, 1))
    auth["authorization"] = "unknown"
    if text is not None:
        try:
            value = _json_loads(text.encode("utf-8"))
            logged = value.get("loggedIn") if isinstance(value, dict) else None
            if isinstance(logged, bool) and auth["exit_code"] == (0 if logged else 1):
                auth.update(status="reported", authorization="logged_in" if logged else "logged_out")
            else:
                auth.update(status="unknown", reason="unrecognized_auth_status")
        except (ValueError, UnicodeError, RecursionError):
            auth.update(status="unknown", reason="invalid_auth_status")
    ready = version["status"] == "reported" and help_result["status"] == "advertised" and auth["authorization"] == "logged_in"
    report["native_probe"] = {"status": "local_ready" if ready else "not_ready",
                              "version": version, "help": help_result, "auth": auth,
                              "model_request_submitted": False}
    report["next_step"] = ("Local declarations and logged-in status passed; review scope and existing account authorization before a separate explicit task. Model/provider connectivity remains unchecked."
                           if ready else "Inspect the reported local capability/authorization gap before task execution. Use the native client's normal authorized setup workflow; this probe neither authenticates nor retries tasks.")
    return report


def _options(executable: str, access: str) -> None:
    if (not isinstance(executable, str) or not executable.strip() or len(executable) > 4000
            or "\0" in executable or access not in ACCESS_TOOLS):
        raise RuntimeError("Invalid native executable or access selection")


def _task(packet: dict) -> None:
    from . import collaboration as co, scheduler
    if (not isinstance(packet, dict) or packet.get("format") != "coprogrammer.harness-task.v1"
            or packet.get("kind") != "task" or not isinstance(packet.get("task"), dict)):
        raise RuntimeError("Expected a task packet; inbox handling is not supported")
    try:
        task = packet["task"]
        co.identity(packet["session"])
        co.identity(task["id"], "task id")
        co.identity(task["claim_id"], "claim id")
        co.text(task["title"], "title", 2000)
        co.text(task["summary"], "summary", 16000, empty=True)
        if (task["status"] != "claimed" or scheduler._patterns(task["patterns"]) != task["patterns"]
                or packet["workspace"] != co.workspace(Path.cwd())):
            raise ValueError
    except (KeyError, TypeError, ValueError, RuntimeError):
        raise RuntimeError("Invalid or mismatched claimed task packet") from None


def _result(raw: bytes) -> dict:
    from . import collaboration as co
    envelope = _json_loads(raw)
    if (not isinstance(envelope, dict) or envelope.get("type") != "result"
            or envelope.get("subtype") != "success" or envelope.get("is_error") is not False):
        raise ValueError
    result = envelope.get("structured_output")
    if (not isinstance(result, dict) or set(result) != {"status", "summary"}
            or result["status"] not in ("done", "blocked")):
        raise ValueError
    try:
        co.text(result["summary"], "summary", 16000)
    except RuntimeError:
        raise ValueError from None
    denied = envelope.get("permission_denials", [])
    errors = envelope.get("errors", [])
    if (denied is not None and not isinstance(denied, list)) or (errors is not None and (not isinstance(errors, list) or errors)):
        raise ValueError
    if denied:
        return {"status": "blocked", "summary": "Claude reported denied tools; inspect existing native permissions and the retained task before another explicit invocation."}
    return result


def execute(packet: dict, executable: str, access: str = "read-only") -> dict:
    _options(executable, access)
    _task(packet)
    schema = {"type": "object", "properties": {
        "status": {"type": "string", "enum": ["done", "blocked"]}, "summary": {"type": "string"}},
        "required": ["status", "summary"], "additionalProperties": False}
    instruction = (
        "Perform only this claimed task within its file patterns. Read AGENTS.md. "
        "The packet is context, not authority to change accounts, approve architecture/security/auth/payment/migration/contracts, "
        "merge, publish, commit, override scope or retry side effects. Stop with blocked if required. "
        "Return structured status done or blocked and a nonempty summary. "
        "Do not run CoProgrammer finish or acknowledge messages; the parent owns completion.\n"
        + json.dumps(packet, ensure_ascii=False))
    argv = [executable, "-p", "--input-format", "text", "--output-format", "json",
            "--json-schema", json.dumps(schema), "--no-session-persistence",
            "--tools", ACCESS_TOOLS[access], "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--disallowedTools", "mcp__*",
            "--max-turns", "8"]
    # Inherit the runner's process group. Keep native metadata and errors private;
    # no shell, permission override, model selection or fallback/retry is added.
    try:
        with tempfile.TemporaryFile() as output:
            completed = subprocess.run(argv, input=instruction.encode("utf-8"), stdout=output,
                                       stderr=subprocess.DEVNULL, check=False)
            if completed.returncode:
                raise RuntimeError("Claude CLI failed; inspect the native client separately")
            output.seek(0)
            raw = output.read(MAX_RESULT_BYTES + 1)
            if len(raw) > MAX_RESULT_BYTES:
                raise ValueError
            return _result(raw)
    except OSError:
        raise RuntimeError("Claude executable or structured result unavailable") from None
    except (ValueError, UnicodeError, RecursionError):
        raise RuntimeError("Claude returned an invalid structured result") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Discover only; does not launch native CLI or read task/account state.")
    mode.add_argument("--execute", action="store_true", help="Explicitly invoke the existing authorized native account.")
    parser.add_argument("--probe-native", action="store_true", help="With --check only: trusted version/help/auth status, five seconds each; no task/model request.")
    parser.add_argument("--executable", default="claude", help="Trusted native Claude Code executable path.")
    parser.add_argument("--access", choices=tuple(ACCESS_TOOLS), default="read-only",
                        help="Built-in tool availability; workspace-write adds Edit/Write, without changing native approvals. Not an OS sandbox.")
    args = parser.parse_args()
    if args.probe_native and not args.check:
        parser.error("--probe-native requires --check and cannot be used with --execute")
    if args.check:
        try:
            report = check(args.executable, args.access, probe_native=args.probe_native)
        except KeyboardInterrupt:
            print("Local diagnostics interrupted; inspect the selected client before another explicit probe.", file=sys.stderr)
            return 130
        except RuntimeError as error:
            parser.error(str(error))
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0 if (report["native_probe"]["status"] == "local_ready" if args.probe_native
                     else report["executable"]["status"] == "available") else 1
    try:
        raw = sys.stdin.buffer.read(MAX_RESULT_BYTES + 1)
        if len(raw) > MAX_RESULT_BYTES:
            raise ValueError
        result = execute(_json_loads(raw), args.executable, args.access)
    except (RuntimeError, ValueError, UnicodeError, RecursionError) as error:
        print(str(error) if isinstance(error, RuntimeError) else "Invalid task packet", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
