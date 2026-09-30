"""Regression coverage for the MCP transport and Manager tool boundary."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli, mcp_server


class McpRobustnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.state_dir = str(self.cwd / ".coprogrammer")
        self.ctx = mcp_server.ManagerContext(self.cwd, self.state_dir)

    @staticmethod
    def request(method: str, params: object = None, request_id: int = 1) -> dict:
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            request["params"] = params
        return request

    def tool(self, name: str, arguments: object) -> dict:
        return mcp_server.handle_request(
            self.ctx, self.request("tools/call", {"name": name, "arguments": arguments})
        )

    def serve_raw(self, content: str) -> list[dict]:
        stdout = io.StringIO()
        self.assertEqual(
            mcp_server.serve(self.cwd, self.state_dir, io.StringIO(content), stdout), 0
        )
        return [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_invalid_envelopes_do_not_stop_server(self) -> None:
        malformed = [
            [], None, 42, "request", {}, {"method": "ping"},
            {"jsonrpc": "1.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "id": True, "method": "ping"},
            {"jsonrpc": "2.0", "id": None, "method": "ping"},
            {"jsonrpc": "2.0", "id": {}, "method": "ping"},
            {"jsonrpc": "2.0", "id": 1.2, "method": "ping"},
            {"jsonrpc": "2.0", "id": 1, "method": []},
            {"jsonrpc": "2.0", "id": 1, "method": ""},
            {"jsonrpc": "2.0", "id": 1, "method": "ping", "result": {}},
            {"jsonrpc": "2.0", "id": "\ud800", "method": "ping"},
        ]
        stream = "".join(json.dumps(item) + "\n" for item in malformed)
        stream += json.dumps(self.request("ping", request_id=99)) + "\n"
        responses = self.serve_raw(stream)
        self.assertEqual(len(responses), len(malformed) + 1)
        self.assertTrue(all(item["error"]["code"] == -32600 for item in responses[:-1]))
        self.assertEqual(responses[-1], {"jsonrpc": "2.0", "id": 99, "result": {}})
        self.assertFalse(self.ctx.log_path.exists())

    def test_malformed_params_are_protocol_errors_without_writes(self) -> None:
        for params in (None, [], "params", 0, {"name": []}, {"name": "heartbeat", "arguments": []},
                       {"name": "heartbeat", "arguments": None}, {"name": "heartbeat", "extra": True}):
            with self.subTest(params=params):
                request = self.request("tools/call")
                request["params"] = params
                response = mcp_server.handle_request(self.ctx, request)
                self.assertEqual(response["error"]["code"], -32602)
        self.assertFalse(self.ctx.log_path.exists())

    def test_invalid_tool_arguments_cannot_mutate_state(self) -> None:
        cases = [
            ("lease_request", {"holder": "a", "patterns": "src/**"}),
            ("lease_request", {"holder": "a", "patterns": []}),
            ("lease_request", {"holder": "a", "patterns": [123]}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "kind": "invalid"}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "ttl_seconds": True}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "ttl_seconds": 0}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "ttl_seconds": 604801}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "ttl_seconds": 1.5}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"] * 129}),
            ("lease_request", {"holder": "a", "patterns": ["x" * 4097]}),
            ("lease_request", {"holder": " ", "patterns": ["src/**"]}),
            ("lease_request", {"holder": "a", "patterns": ["src/**"], "unknown": True}),
            ("lease_release", {"lease_id": "lease_x"}),
            ("lease_renew", {"lease_id": "lease_x", "actor": "a", "ttl_seconds": False}),
            ("heartbeat", {"agent": "a"}),
            ("heartbeat", {"agent": "a", "task": 1}),
            ("heartbeat", {"agent": "a", "task": ""}),
            ("heartbeat", {"agent": "x" * 257, "task": "work"}),
            ("heartbeat", {"agent": "a", "task": "x\x00y"}),
            ("heartbeat", {"agent": "a", "task": "\ud800"}),
            ("contract_propose", {"proposer": "a", "kind": "api", "name": "x", "summary": "x", "compatibility": "maybe"}),
            ("contract_propose", {"proposer": "a", "kind": "invalid", "name": "x", "summary": "x"}),
            ("manager_status", {"unused": True}),
            ("manager_forecast", {"changed_files": "src/**"}),
            ("manager_forecast", {"changed_files": ["x"] * 1001}),
            ("digest_branch", {"working_tree": "false"}),
            ("digest_branch", {"base": "--output=unexpected"}),
        ]
        for name, arguments in cases:
            with self.subTest(name=name, arguments=repr(arguments)[:120]):
                response = self.tool(name, arguments)
                self.assertTrue(response["result"]["isError"])
                self.assertFalse(self.ctx.log_path.exists())

    def test_notifications_never_respond_or_execute_tools(self) -> None:
        notifications = [
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "method": "ping"},
            {"jsonrpc": "2.0", "method": "unknown"},
            {"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "method": "tools/call", "params": {
                "name": "heartbeat", "arguments": {"agent": "a", "task": "work"}}},
            {"jsonrpc": "2.0", "method": "tools/call", "params": None},
        ]
        stream = "".join(json.dumps(item) + "\n" for item in notifications)
        self.assertEqual(self.serve_raw(stream), [])
        self.assertFalse(self.ctx.log_path.exists())
        for request in notifications:
            self.assertIsNone(mcp_server.handle_request(self.ctx, request))
        self.assertEqual(self.ctx.protocol_version, mcp_server.PROTOCOL_VERSION)

    def test_supported_versions_are_negotiated_and_results_match_version(self) -> None:
        for version in mcp_server.SUPPORTED_PROTOCOL_VERSIONS:
            with self.subTest(version=version):
                response = mcp_server.handle_request(self.ctx, self.request("initialize", {
                    "protocolVersion": version, "capabilities": {},
                    "clientInfo": {"name": "tests", "version": "1.0"},
                }))
                self.assertEqual(response["result"]["protocolVersion"], version)
                listing = mcp_server.handle_request(self.ctx, self.request("tools/list"))
                tools = {tool["name"]: tool for tool in listing["result"]["tools"]}
                self.assertIn("lease_release", tools)
                self.assertIn("lease_renew", tools)
                self.assertEqual("annotations" in tools["heartbeat"], version != "2024-11-05")
                result = self.tool("manager_status", {})["result"]
                self.assertFalse(result["isError"])
                structured_supported = version in ("2025-06-18", "2025-11-25")
                self.assertEqual("structuredContent" in result, structured_supported)
                if structured_supported:
                    self.assertEqual(result["structuredContent"], json.loads(result["content"][0]["text"]))

    def test_unknown_version_negotiates_only_an_implemented_version(self) -> None:
        response = mcp_server.handle_request(
            self.ctx, self.request("initialize", {"protocolVersion": "2026-07-28"})
        )
        self.assertEqual(response["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(response["result"]["capabilities"], {"tools": {}, "resources": {}, "prompts": {}})

    def test_invalid_initialize_does_not_change_negotiated_version(self) -> None:
        for params in ({"protocolVersion": []}, {"capabilities": None}, {"clientInfo": {"name": "x"}}):
            with self.subTest(params=params):
                response = mcp_server.handle_request(self.ctx, self.request("initialize", params))
                self.assertEqual(response["error"]["code"], -32602)
                self.assertEqual(self.ctx.protocol_version, mcp_server.PROTOCOL_VERSION)

    def test_tools_expose_closed_schemas_and_behavior_annotations(self) -> None:
        response = mcp_server.handle_request(self.ctx, self.request("tools/list"))
        for tool in response["result"]["tools"]:
            self.assertFalse(tool["inputSchema"]["additionalProperties"])
            self.assertEqual(tool["annotations"]["readOnlyHint"], tool["name"] in mcp_server.READ_ONLY_TOOLS)
            self.assertFalse(tool["annotations"]["openWorldHint"])

    def test_unknown_cursor_is_rejected(self) -> None:
        response = mcp_server.handle_request(self.ctx, self.request("tools/list", {"cursor": "invalid"}))
        self.assertEqual(response["error"]["code"], -32602)

    def test_parse_errors_and_deep_json_do_not_stop_server(self) -> None:
        malformed = [
            "{", "NaN", '{"jsonrpc":"2.0","id":Infinity,"method":"ping"}',
            '{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}',
            "[" * 1100 + "]" * 1100,
        ]
        stream = "\n".join(malformed) + "\n" + json.dumps(self.request("ping", request_id=99)) + "\n"
        responses = self.serve_raw(stream)
        self.assertEqual(len(responses), len(malformed) + 1)
        self.assertTrue(all(item["error"]["code"] == -32700 for item in responses[:-2]))
        # Python versions differ in how deeply their JSON decoder can parse.
        # Either rejection is valid; the connection must remain usable.
        self.assertIn(responses[-2]["error"]["code"], (-32700, -32600))
        self.assertEqual(responses[-1]["id"], 99)
        self.assertEqual(responses[-1]["result"], {})

    def test_oversized_line_is_fully_discarded_before_next_request(self) -> None:
        hidden_mutation = json.dumps(self.request("tools/call", {
            "name": "heartbeat", "arguments": {"agent": "a", "task": "work"},
        }))
        stream = "x" * 600 + hidden_mutation + "\n"
        stream += json.dumps(self.request("ping", request_id=99)) + "\n"
        with patch.object(mcp_server, "MAX_REQUEST_BYTES", 256):
            responses = self.serve_raw(stream)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["error"]["code"], -32600)
        self.assertEqual(responses[1]["id"], 99)
        self.assertFalse(self.ctx.log_path.exists())

    def test_byte_limit_accounts_for_multibyte_text(self) -> None:
        request = self.request("tools/call", {"name": "heartbeat", "arguments": {"agent": "a", "task": "字" * 100}})
        line = json.dumps(request, ensure_ascii=False) + "\n"
        self.assertLess(len(line), 300)
        self.assertGreater(len(line.encode("utf-8")), 300)
        with patch.object(mcp_server, "MAX_REQUEST_BYTES", 300):
            responses = self.serve_raw(line + json.dumps(self.request("ping", request_id=99)) + "\n")
        self.assertEqual(responses[0]["error"]["code"], -32600)
        self.assertEqual(responses[1]["id"], 99)
        self.assertFalse(self.ctx.log_path.exists())

    def test_oversized_eof_terminates_cleanly(self) -> None:
        with patch.object(mcp_server, "MAX_REQUEST_BYTES", 32):
            responses = self.serve_raw("x" * 1000)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["error"]["code"], -32600)

    def test_handler_failure_is_returned_as_tool_error(self) -> None:
        def failing_handler(ctx, arguments):
            raise RuntimeError("temporary failure")

        with patch.dict(mcp_server.TOOL_HANDLERS, {"manager_status": failing_handler}):
            response = self.tool("manager_status", {})
        self.assertTrue(response["result"]["isError"])
        self.assertIn("temporary failure", response["result"]["content"][0]["text"])
        self.assertEqual(mcp_server.handle_request(self.ctx, self.request("ping"))["result"], {})

    def test_request_renew_release_roundtrip_and_holder_enforcement(self) -> None:
        granted = self.tool("lease_request", {"holder": "a", "patterns": ["src/**"], "ttl_seconds": 60})["result"]
        self.assertFalse(granted["isError"])
        lease = granted["structuredContent"]["lease"]
        self.assertTrue(granted["structuredContent"]["granted"])
        before = self.ctx.log_path.read_bytes()
        denied = self.tool("lease_release", {"lease_id": lease["id"], "actor": "b"})["result"]
        self.assertTrue(denied["isError"])
        self.assertEqual(self.ctx.log_path.read_bytes(), before)
        renewed = self.tool("lease_renew", {"lease_id": lease["id"], "actor": "a", "ttl_seconds": 120})["result"]
        self.assertFalse(renewed["isError"])
        self.assertTrue(renewed["structuredContent"]["renewed"])
        self.assertGreater(renewed["structuredContent"]["lease"]["expires_at"], lease["expires_at"])
        released = self.tool("lease_release", {"lease_id": lease["id"], "actor": "a"})["result"]
        self.assertTrue(released["structuredContent"]["released"])
        self.assertEqual(cli.active_leases(cli.load_events(self.ctx.log_path)), {})

    def test_concurrent_mcp_clients_share_atomic_lease_requests(self) -> None:
        def request_for(holder: str) -> dict:
            context = mcp_server.ManagerContext(self.cwd, self.state_dir)
            response = mcp_server.handle_request(context, self.request("tools/call", {
                "name": "lease_request", "arguments": {"holder": holder, "patterns": ["src/**"]},
            }))
            self.assertFalse(response["result"]["isError"])
            return response["result"]["structuredContent"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(request_for, ["a", "b", "c", "d"]))
        self.assertEqual(sum(result["granted"] for result in results), 1)
        self.assertEqual(len(cli.active_leases(cli.load_events(self.ctx.log_path))), 1)


if __name__ == "__main__":
    unittest.main()
