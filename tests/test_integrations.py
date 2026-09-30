from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer.integrations import client_config, doctor, github_context


class ClientConfigurationTest(unittest.TestCase):
    def test_json_clients_use_native_root_and_launch_exact_package(self):
        with tempfile.TemporaryDirectory(prefix="协作 config ") as tmp:
            (Path(tmp) / "coprogrammer.py").write_text("raise RuntimeError('shadow module executed')\n")
            for client, key in (("claude", "mcpServers"), ("copilot", "servers")):
                config = json.loads(client_config(client, Path(tmp)))
                server = config[key]["coprogrammer"]
                self.assertEqual(server["type"], "stdio")
                self.assertEqual(server["args"][-1], str(Path(tmp).resolve()))
                messages = [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                "clientInfo": {"name": "config-test", "version": "1"}}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                ]
                result = subprocess.run([server["command"], *server["args"]],
                                        env=os.environ.copy(), cwd=tmp,
                                        input="".join(json.dumps(x) + "\n" for x in messages),
                                        text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                replies = [json.loads(x) for x in result.stdout.splitlines()]
                names = {x["name"] for x in replies[-1]["result"]["tools"]}
                self.assertIn("manager_status", names)
                self.assertIn("lease_renew", names)

    def test_codex_toml_roundtrip(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("TOML roundtrip uses Python 3.11+ standard parser")
        prefix = '配置 " quoted ' if os.name != "nt" else "配置 spaced "
        with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
            data = tomllib.loads(client_config("codex", Path(tmp)))
            self.assertEqual(data["mcp_servers"]["coprogrammer"]["args"][-1],
                             str(Path(tmp).resolve()))

    def test_doctor_does_not_claim_connection_or_disclose_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-only-secret"}), \
                patch("shutil.which", return_value="/test/client"):
            result = doctor(Path(tmp))
            self.assertFalse(result["network_used"])
            self.assertTrue(result["providers"]["deepseek"]["key_present"])
            self.assertEqual(result["clients"]["claude"]["connection"], "not_checked")
            self.assertNotIn("test-only-secret", json.dumps(result))


class GithubContextTest(unittest.TestCase):
    def metadata(self):
        return {"number": 12, "url": "https://github.com/org/repo/pull/12",
                "baseRefOid": "a" * 40, "headRefOid": "b" * 40,
                "files": [{"path": "src/功能.py"}], "changedFiles": 1}

    def test_read_only_pr_handoff_is_pinned(self):
        reply = subprocess.CompletedProcess([], 0, json.dumps(self.metadata()), "")
        with patch("coprogrammer.integrations.subprocess.run", return_value=reply) as run:
            result = github_context("https://github.com/org/repo/pull/12", Path("."))
            args = run.call_args.args[0]
            self.assertEqual(args[:4], ["gh", "pr", "view", "12"])
            self.assertEqual(args[-2:], ["--repo", "org/repo"])
            self.assertEqual(result["head"], "b" * 40)
            self.assertTrue(result["requires_human_review"])

    def test_untrusted_selectors_are_not_executed(self):
        for selector in ("--help", "https://evil.test/org/repo/pull/12", "0", "$(whoami)"):
            with patch("coprogrammer.integrations.subprocess.run") as run:
                with self.assertRaises(RuntimeError):
                    github_context(selector, Path("."))
                run.assert_not_called()

    def test_incomplete_or_invalid_metadata_fails(self):
        for data in ({**self.metadata(), "changedFiles": 2},
                     {**self.metadata(), "files": [{"path": "a"}, {"path": "a"}], "changedFiles": 2},
                     {**self.metadata(), "headRefOid": "main"}, [],
                     {**self.metadata(), "number": 13}):
            with patch("coprogrammer.integrations.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 0, json.dumps(data), "")):
                with self.assertRaises(RuntimeError):
                    github_context("12", Path("."), "org/repo")

    def test_server_error_does_not_copy_stderr(self):
        with patch("coprogrammer.integrations.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 1, "", "test-only-secret")):
            with self.assertRaises(RuntimeError) as raised:
                github_context("12", Path("."))
            self.assertNotIn("test-only-secret", str(raised.exception))
