"""Runtime import kits and Grok response boundaries, without live accounts."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, integrations, onboarding, providers, setup, worker
from test_workspace_workflow import Fixture
from test_providers import FakeResponse


def grok_response(**overrides):
    result = {"status": "completed", "error": None,
              "output": [{"type": "reasoning", "summary": [{"text": "private reasoning"}]},
                         {"type": "message", "role": "assistant",
                          "content": [{"type": "output_text", "text": "First finding"},
                                      {"type": "output_text", "text": "Second finding"}]}],
              "usage": {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12}}
    result.update(overrides)
    return result


class ImportKitTest(unittest.TestCase):
    def test_profiles_distinguish_workspace_loading_and_manual_import(self):
        profiles = integrations.client_profiles()
        self.assertEqual(profiles["openclaw"]["skills_activation"], "workspace")
        for client in ("openclaw", "workbuddy", "harness", "generic"):
            self.assertEqual(profiles[client]["mcp_activation"], "manual_import")
            self.assertEqual(profiles[client]["connection"], "not_checked")
        self.assertEqual(profiles["workbuddy"]["skills_activation"], "manual_import")
        profiles["codex"]["connection"] = "fabricated"
        self.assertEqual(integrations.client_profiles()["codex"]["connection"], "not_checked")

    def test_editions_preserve_client_settings_and_work_in_empty_projects(self):
        for client in ("openclaw", "workbuddy", "harness", "generic"):
            for edition in ("full", "skills", "mcp"):
                with self.subTest(client=client, edition=edition), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    private = root / "openclaw.json"
                    private.write_text('{"private":"marker"}')
                    report = setup.preview(root, client, edition=edition, include_content=True)
                    self.assertEqual(list(root.iterdir()), [private])
                    self.assertNotIn("marker", json.dumps(report))
                    applied = setup.apply(root, client, edition=edition)
                    self.assertTrue(applied["applied"])
                    kinds = {row["kind"] for row in applied["files"]}
                    self.assertEqual(kinds, {"mcp"} if edition == "mcp" else
                                     {"instructions", "template", "skill"} if edition == "skills" else
                                     {"instructions", "template", "skill", "mcp"})
                    self.assertEqual(private.read_text(), '{"private":"marker"}')
                    self.assertTrue(all(row["status"] == "unchanged" for row in
                                        setup.apply(root, client, edition=edition)["files"]))

    def test_import_config_conflict_is_atomic_and_never_discloses_existing_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / integrations.CLIENT_LAYOUTS["workbuddy"][1]
            target.parent.mkdir(parents=True)
            target.write_text("private-config-marker")
            before = set(root.rglob("*"))
            result = setup.apply(root, "workbuddy", include_content=True)
            self.assertFalse(result["applied"])
            self.assertEqual(set(root.rglob("*")), before)
            self.assertNotIn("private-config-marker", json.dumps(result))

    def test_real_mcp_process_from_each_import_profile(self):
        for client in ("openclaw", "workbuddy", "harness", "generic"):
            with self.subTest(client=client), tempfile.TemporaryDirectory(prefix="导入 kit ") as tmp:
                root = Path(tmp)
                (root / "coprogrammer.py").write_text("raise RuntimeError('shadow module executed')\n")
                data = json.loads(integrations.client_config(client, root))
                servers = data["nodeHost"]["mcp"]["servers"] if client == "openclaw" else data["mcpServers"]
                server = servers["coprogrammer"]
                self.assertEqual(server["args"][-1], str(root.resolve()))
                messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                                        "clientInfo": {"name": client, "version": "test"}}},
                            {"jsonrpc": "2.0", "method": "notifications/initialized"},
                            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
                reply = subprocess.run([server["command"], *server["args"]], cwd=tmp, env=os.environ.copy(),
                                       input="".join(json.dumps(row) + "\n" for row in messages),
                                       text=True, capture_output=True, timeout=15)
                self.assertEqual(reply.returncode, 0, reply.stderr)
                rows = [json.loads(row) for row in reply.stdout.splitlines()]
                tools = {row["name"] for row in rows[-1]["result"]["tools"]}
                self.assertIn("worker_step", tools)
                self.assertIn("worker_finish", tools)
                self.assertFalse((root / ".coprogrammer").exists())

    def test_cli_accepts_all_import_profiles_and_grok_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            for client in ("openclaw", "workbuddy", "harness", "generic"):
                with self.subTest(client=client), contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(cli.main(["setup", "--client", client, "--edition", "mcp", "--cwd", tmp]), 0)
                    self.assertEqual(json.loads(out.getvalue())["activation"]["mcp_activation"], "manual_import")
                    self.assertEqual(list(Path(tmp).iterdir()), [])
        args = cli.build_parser().parse_args(["review", "--provider", "grok", "--model", "explicit-model"])
        self.assertEqual(args.provider, "grok")
        self.assertFalse(args.send)


class RuntimeRoutingTest(Fixture):
    def test_new_runtime_labels_share_claim_guard_and_handoff(self):
        from coprogrammer import collaboration as co, scheduler as sc
        onboarding.start(self.path, self.repo, "openclaw", "claw")
        other = self.root / "buddy"
        self.git("worktree", "add", "-b", "buddy", str(other))
        onboarding.start(self.path, other, "workbuddy", "buddy", provider="grok")
        sc.create(self.path, self.repo, "claw", "api", "API", ["src/**"], clients=["openclaw"])
        sc.create(self.path, self.repo, "claw", "review", "Review", ["docs/**"], depends_on=["api"], clients=["grok"])
        first = worker.step(self.path, self.repo, "claw", apply=True)
        self.assertEqual(first["task"]["id"], "api")
        worker.finish(self.path, self.repo, "claw", "api", first["task"]["claim_id"], "done", ["buddy"])
        self.assertEqual(worker.step(self.path, other, "buddy", apply=True)["state"], "inbox")
        inbox = co.inbox(self.path, "buddy")
        co.acknowledge(self.path, other, "buddy", inbox["messages"][0]["id"])
        claimed = worker.step(self.path, other, "buddy", apply=True)
        self.assertEqual(claimed["task"]["id"], "review")
        self.assertTrue(claimed["guard"]["allowed"])

    def test_harness_and_generic_start_resume_keep_provider_identity(self):
        for client in ("harness", "generic"):
            directory = self.root / client
            self.git("worktree", "add", "-b", client, str(directory))
            result = onboarding.start(self.path, directory, client, client, provider="grok")
            self.assertEqual(result["provider"], "grok")
            resumed = onboarding.start(self.path, directory, client, client, resume=True)
            self.assertEqual(resumed["provider"], "grok")
            with self.assertRaisesRegex(RuntimeError, "identity differs"):
                onboarding.start(self.path, directory, client, client, resume=True, provider="deepseek")


class GrokResponsesTest(unittest.TestCase):
    def test_preview_has_explicit_cap_no_tools_or_server_conversation_storage(self):
        with patch("coprogrammer.providers.os.environ") as env:
            preview = providers.build_request("grok", "account-model", "检查代码", max_tokens=77)
        self.assertFalse(env.mock_calls)
        self.assertEqual(preview["url"], "https://api.x.ai/v1/responses")
        self.assertEqual(preview["key_env"], ["XAI_API_KEY"])
        self.assertEqual(preview["body"], {"model": "account-model", "input": [{"role": "user", "content": "检查代码"}],
                                           "max_output_tokens": 77, "stream": False, "store": False})
        self.assertNotIn("Authorization", preview["headers"])

    def test_complete_parses_only_visible_text_and_uses_bearer(self):
        body = grok_response()
        body["output"][1]["content"][0]["text"] += " test-secret"
        with patch.dict("os.environ", {"XAI_API_KEY": "test-secret"}, clear=True), \
                patch("coprogrammer.providers.build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(body, url="https://api.x.ai/v1/responses")
            result = providers.complete("grok", "account-model", "review")
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(result["text"], "First finding [REDACTED]\nSecond finding")
        self.assertEqual(result["usage"], {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12})
        self.assertNotIn("private reasoning", json.dumps(result))
        self.assertFalse(result["truncated"])

    def test_incomplete_text_is_flagged_without_inventing_token_cap_reason(self):
        for details, reason in (({"reason": "max_output_tokens"}, "max_tokens"),
                                ({"reason": "content_filter"}, "incomplete"), (None, "incomplete")):
            result = providers._parse_response(json.dumps(grok_response(status="incomplete", incomplete_details=details)).encode(),
                                               "grok", "model", "secret")
            self.assertTrue(result["truncated"])
            self.assertEqual(result["finish_reason"], reason)

    def test_invalid_pending_error_tool_only_and_malformed_outputs_fail_closed(self):
        for changes in ({"status": "in_progress"}, {"status": "failed"}, {"status": None},
                        {"error": {"message": "private server body"}}, {"output": []},
                        {"output": [{"type": "function_call", "arguments": "execute this"}]},
                        {"output": [None]}, {"output": [{"type": "message", "role": "assistant", "content": [None]}]},
                        {"output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": 1}]}]}):
            with self.subTest(changes=changes), self.assertRaises(providers.ProviderError) as raised:
                providers._parse_response(json.dumps(grok_response(**changes)).encode(), "grok", "model", "secret")
            self.assertEqual(raised.exception.code, "invalid_response")
            self.assertNotIn("private server body", str(raised.exception))

    def test_missing_key_never_calls_network(self):
        with patch.dict("os.environ", {}, clear=True), patch("coprogrammer.providers.build_opener") as opener:
            with self.assertRaises(providers.ProviderError) as raised:
                providers.complete("grok", "model", "review")
            self.assertEqual(raised.exception.code, "missing_api_key")
            opener.assert_not_called()
