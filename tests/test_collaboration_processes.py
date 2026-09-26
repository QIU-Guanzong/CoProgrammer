"""Exercise real stdio processes and linked Git worktrees, without model calls."""
from __future__ import annotations

import json
import queue
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from coprogrammer import cli, integrations


class Client:
    def __init__(self, cwd, client):
        config = integrations.client_config(client, cwd)
        if client == "codex":
            # The generator deliberately uses JSON-compatible TOML strings/arrays.
            fields = dict(line.split(" = ", 1) for line in config.splitlines() if " = " in line)
            command, args = json.loads(fields["command"]), json.loads(fields["args"])
        else:
            config = json.loads(config)["mcpServers"]["coprogrammer"]
            command, args = config["command"], config["args"]
        self.process = subprocess.Popen([command, *args], cwd=cwd, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding="utf-8")
        self.responses = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.next_id = 0

    def _read(self):
        for line in self.process.stdout:
            self.responses.put(line)
        self.responses.put(None)

    def rpc(self, method, params):
        self.next_id += 1
        request = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        line = self.responses.get(timeout=20)
        if line is None:
            raise AssertionError("MCP process ended before replying")
        response = json.loads(line)
        if response.get("id") != self.next_id or "error" in response:
            raise AssertionError(response)
        return response["result"]

    def initialize(self):
        return self.rpc("initialize", {"protocolVersion": "2025-11-25",
                                       "capabilities": {}, "clientInfo": {"name": "integration-test", "version": "1"}})

    def tool(self, name, **args):
        result = self.rpc("tools/call", {"name": name, "arguments": args})
        if result.get("isError"):
            raise AssertionError(result)
        return json.loads(result["content"][0]["text"])

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.reader.join(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()


class CollaborationProcessesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "main"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-m", "initial")
        self.worktree = self.root / "other"
        self.git("worktree", "add", "-b", "feature", str(self.worktree))

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True,
                              capture_output=True, text=True, timeout=20).stdout.strip()

    def client(self, cwd, name):
        client = Client(cwd, name)
        self.addCleanup(client.close)
        client.initialize()
        return client

    def test_two_client_processes_exchange_handoff_and_recover_after_restart(self):
        codex = self.client(self.repo, "codex")
        claude = self.client(self.worktree, "claude")
        advertised = {tool["name"] for tool in codex.rpc("tools/list", {})["tools"]}
        self.assertTrue({"session_register", "session_pulse", "message_send", "message_inbox",
                         "message_ack", "manager_sync"}.issubset(advertised))
        codex.tool("session_register", session="codex-api", client="codex", task="api-42")
        claude.tool("session_register", session="claude-ui", client="claude", task="api-42")
        baseline = claude.tool("manager_sync", session="claude-ui")
        self.assertEqual({s["branch"] for s in baseline["sessions"]}, {"main", "feature"})
        self.assertEqual(baseline["state_path"], str(cli.event_log_path(self.repo)))
        self.assertFalse((self.worktree / ".coprogrammer/events.jsonl").exists())

        sent = codex.tool("message_send", sender="codex-api", recipient="claude-ui",
                          task="api-42", kind="handoff", body="字段已调整；请更新调用方并回报检查结果。", key="api-first")
        claude.close()
        claude = self.client(self.worktree, "claude")
        page = claude.tool("manager_sync", session="claude-ui", after=baseline["next_cursor"])
        self.assertEqual(page["pending_total"], 1)
        self.assertEqual(page["changes"][0]["type"], "message.sent")
        self.assertEqual(page["inbox"][0]["id"], sent["message"]["id"])
        # Reading and restarting did not change receipt state.
        self.assertIsNone(page["inbox"][0]["acknowledged_at"])
        claude.tool("message_ack", session="claude-ui", message_id=sent["message"]["id"])
        reply = claude.tool("message_send", sender="claude-ui", recipient="codex-api", task="api-42",
                            kind="update", body="收到，开始检查。", reply_to=sent["message"]["id"], key="reply-first")
        received = codex.tool("message_inbox", session="codex-api")
        self.assertEqual(received["messages"][0]["id"], reply["message"]["id"])
        duplicate = codex.tool("message_send", sender="codex-api", recipient="claude-ui",
                               task="api-42", kind="handoff", body="字段已调整；请更新调用方并回报检查结果。", key="api-first")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(claude.tool("message_inbox", session="claude-ui")["pending_total"], 0)
        claude.tool("session_pulse", session="claude-ui", status="blocked", note="等待接口决策")
        snapshot = codex.tool("manager_sync")
        remote = next(s for s in snapshot["sessions"] if s["id"] == "claude-ui")
        self.assertEqual(remote["status"], "blocked")
        self.assertEqual(remote["freshness"], "fresh")
        self.assertEqual(codex.rpc("ping", {}), {})

    def test_simultaneous_process_retries_produce_single_message(self):
        from concurrent.futures import ThreadPoolExecutor
        first = self.client(self.repo, "codex")
        second = self.client(self.repo, "claude")
        first.tool("session_register", session="sender", client="codex", task="race")
        second.tool("session_register", session="recipient", client="claude", task="race")
        def send(client):
            return client.tool("message_send", sender="sender", recipient="recipient", task="race",
                               body="One retry-safe handoff", key="same-request")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(send, [first, second]))
        self.assertEqual(sum(not result["duplicate"] for result in results), 1)
        self.assertEqual(len(first.tool("message_inbox", session="recipient")["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
