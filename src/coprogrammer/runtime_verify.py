"""Explicit connection checks without model calls, account reads or client repair."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import integrations, setup

MAX_REPLY = 2_000_000


def _json_command(argv: list[str], cwd: Path, timeout: int, env: dict) -> dict:
    # Discard diagnostics: third-party clients may include authentication data.
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output,
                                    stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                    timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "reason": "client_command_failed_or_timed_out"}
        output.seek(0)
        raw = output.read(MAX_REPLY + 1)
    if result.returncode or len(raw) > MAX_REPLY:
        return {"ok": False, "reason": "client_command_failed_or_reply_too_large"}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
        return {"ok": True, "data": data}
    except (ValueError, UnicodeError, RecursionError):
        return {"ok": False, "reason": "invalid_client_reply"}


def verify(cwd: Path, client: str, timeout: int = 60,
           native_executable: str | None = None) -> dict:
    if client not in integrations.CLIENTS:
        raise RuntimeError("unknown client")
    if type(timeout) is not int or not 1 <= timeout <= 180:
        raise RuntimeError("verification timeout must be 1..180 seconds")
    if native_executable is not None and (client != "openclaw"
            or not isinstance(native_executable, str) or not native_executable.strip()
            or len(native_executable) > 4000 or "\0" in native_executable):
        raise RuntimeError("native_executable must select one trusted OpenClaw executable")
    cwd = cwd.resolve()
    plan = setup.preview(cwd, client)
    missing = [item["path"] for item in plan["files"] if item["status"] == "create"]
    conflicts = plan["conflicts"]
    data = json.loads(integrations.client_config("claude", cwd))
    server = data["mcpServers"]["coprogrammer"]
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "coprogrammer-verification", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
    ]
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run([server["command"], *server["args"]], cwd=cwd,
                                    input="".join(json.dumps(row) + "\n" for row in messages).encode(),
                                    stdout=output, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
            output.seek(0)
            raw = output.read(MAX_REPLY + 1)
            if result.returncode or len(raw) > MAX_REPLY:
                raise ValueError
            rows = {row["id"]: row for row in map(json.loads, raw.splitlines())}
            tools = rows[2]["result"]["tools"]
            resources = rows[3]["result"]["resources"]
            if any("error" in row for row in rows.values()) or not isinstance(tools, list) or not isinstance(resources, list):
                raise ValueError
            names = [item["name"] for item in tools]
            if not {"worker_step", "worker_finish", "message_inbox", "message_ack"}.issubset(names):
                raise ValueError
            transport = {"status": "verified", "tool_count": len(tools), "resource_count": len(resources)}
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError, RecursionError):
            transport = {"status": "failed", "reason": "stdio_probe_failed"}
    report = {"format": "coprogrammer.runtime-verification.v1", "client": client,
              "installation": {"status": "conflict" if conflicts else "missing" if missing else "ready",
                               "missing_files": missing, "conflicts": conflicts},
              "transport": transport, "native_client": {"status": "not_checked"},
              "model_connection": "not_checked", "network_used": False,
              "note": "Transport discovery does not establish model access, task execution or global client activation."}
    if client != "openclaw":
        return report
    executable = shutil.which(native_executable or "openclaw")
    if not executable:
        report["native_client"] = {"status": "unavailable", "reason": "openclaw_not_installed"}
        return report
    report["network_used"] = "not_checked"
    report["native_executable"] = executable
    with tempfile.TemporaryDirectory(prefix="coprogrammer-openclaw-probe-") as tmp:
        root = Path(tmp)
        profile = root / "openclaw.json"
        profile.write_text(integrations.openclaw_profile(cwd), encoding="utf-8")
        env = {**os.environ, "OPENCLAW_HOME": str(root), "OPENCLAW_STATE_DIR": str(root),
               "OPENCLAW_CONFIG_PATH": str(profile)}
        checked = _json_command([executable, "config", "validate", "--json"], cwd, timeout, env)
        if not checked["ok"] or checked["data"].get("valid") is not True:
            report["native_client"] = {"status": "failed", "reason": "native_profile_validation_failed"}
            return report
        checked_path = checked["data"].get("path")
        try:
            bound = (isinstance(checked_path, str) and
                     os.path.normcase(str(Path(checked_path).resolve())) ==
                     os.path.normcase(str(profile.resolve())))
        except (OSError, RuntimeError, ValueError):
            bound = False
        if not bound:
            report["native_client"] = {"status": "failed", "reason": "isolated_profile_not_used",
                                       "next_step": "Select the trusted native CLI with --native-executable; keep managed-service settings separate."}
            return report
        probed = _json_command([executable, "mcp", "probe", "coprogrammer", "--json"], cwd, timeout, env)
        if not probed["ok"]:
            report["native_client"] = {"status": "failed", "reason": probed["reason"]}
            return report
        data = probed["data"]
        names = data.get("tools", [])
        diagnostics = data.get("diagnostics", [])
        okay = (isinstance(names, list) and all(isinstance(name, str) for name in names)
                and {"coprogrammer__worker_step", "coprogrammer__worker_finish"}.issubset(names)
                and diagnostics == [])
        report["native_client"] = {"status": "verified" if okay else "failed",
                                   "scope": "isolated_config_and_native_mcp_discovery",
                                   "tool_count": len(names) if isinstance(names, list) else 0}
    return report
