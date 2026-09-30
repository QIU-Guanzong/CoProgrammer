from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from coprogrammer import cli


class UpgradeCliTest(unittest.TestCase):
    def test_mcp_encoding_failure_does_not_end_stream(self):
        from coprogrammer import mcp_server
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "manager_status"}},
                    {"jsonrpc": "2.0", "id": 2, "method": "ping"}]
        stdin = io.StringIO("".join(json.dumps(item) + "\n" for item in messages))
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(mcp_server.TOOL_HANDLERS, {
                "manager_status": lambda *_: '{"invalid": NaN}'}):
            mcp_server.serve(Path(tmp), None, stdin, stdout)
        results = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(results[0]["error"]["code"], -32603)
        self.assertEqual(results[-1]["id"], 2)

    def test_config_output_never_overwrites_existing_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "client.json"
            args = ["integrations", "config", "--client", "claude", "--cwd", tmp,
                    "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(args), 0)
            before = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(args), 2)
            self.assertEqual(before, output.read_bytes())

    def test_review_cli_has_no_network_without_send(self):
        with patch("coprogrammer.review.create_review", return_value={"status": "prepared"}) as review, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["review", "--provider", "glm", "--model", "explicit"]), 0)
        self.assertFalse(review.call_args.kwargs["send"])

    def test_provider_error_is_safe_cli_error(self):
        from coprogrammer.providers import ProviderError
        with patch("coprogrammer.review.create_review", side_effect=ProviderError("missing_api_key", "Set key env")), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(cli.main(["review", "--provider", "glm", "--model", "explicit"]), 2)
        self.assertIn("missing_api_key", stderr.getvalue())

    def test_raw_event_cannot_bypass_lease_or_decision_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            for event_type in ("lease.granted", "lease.released", "decision.recorded"):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cli.main(["manager", "event", "append", "--cwd", tmp,
                                               "--type", event_type, "--actor", "other"]), 2)
            self.assertFalse((Path(tmp) / ".coprogrammer/events.jsonl").exists())

    def test_path_aliases_do_not_get_two_leases(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index, alias in enumerate(("./src/**", "src//**", "src/./**", "SRC/**", "src\\**")):
                path = Path(tmp) / str(index) / "events.jsonl"
                self.assertTrue(cli.request_lease(path, "first", "path", ["src/**"])["granted"])
                self.assertFalse(cli.request_lease(path, "second", "path", [alias])["granted"], alias)

    def test_lease_traversal_and_absolute_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pattern in ("../src/**", "src/../other/**", "/src/**", "C:\\src\\**", "\x00"):
                with self.assertRaises(RuntimeError):
                    cli.request_lease(Path(tmp) / "events.jsonl", "first", "path", [pattern])
            self.assertFalse((Path(tmp) / "events.jsonl").exists())

    def test_decision_can_only_be_recorded_once_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            decision = cli.new_decision("Fixture decision", "Concurrency test")
            cli.append_event(path, cli.make_event("decision.requested", "fixture", "repo:fixture", {"decision": decision}))
            barrier = threading.Barrier(2)
            def record(outcome):
                args = cli.build_parser().parse_args([
                    "manager", "decision", "record", "--cwd", tmp, "--state-dir", tmp,
                    "--id", decision["id"], "--decision", outcome, "--decider", "fixture-reviewer"])
                barrier.wait()
                try:
                    cli.command_manager_decision_record(args)
                    return True
                except RuntimeError:
                    return False
            with contextlib.redirect_stdout(io.StringIO()), concurrent.futures.ThreadPoolExecutor(2) as pool:
                outcomes = list(pool.map(record, ("approve", "deny")))
            self.assertEqual(sum(outcomes), 1)
            self.assertEqual(sum(e["type"] == "decision.recorded" for e in cli.load_events(path)), 1)
