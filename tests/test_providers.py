import io
import json
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request
from unittest.mock import patch

from coprogrammer import providers


class FakeResponse(io.BytesIO):
    def __init__(self, body, *, url="https://api.deepseek.com/chat/completions", status=200):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.url = url
        self.status = status
        self.read_size = None

    def geturl(self):
        return self.url

    def read(self, size=-1):
        self.read_size = size
        return super().read(size)


def chat_response(**overrides):
    result = {"choices": [{"message": {"content": "Review complete", "reasoning_content": "private reasoning"},
                           "finish_reason": "stop"}],
              "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12}}
    result.update(overrides)
    return result


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.opener = patch("coprogrammer.providers.build_opener")
        self.build_opener = self.opener.start()
        self.addCleanup(self.opener.stop)

    def run_complete(self, body=None, provider="deepseek", **kwargs):
        preview = providers.build_request(provider, "explicit-model", "Review this diff", **kwargs)
        response = FakeResponse(chat_response() if body is None else body, url=preview["url"])
        self.build_opener.return_value.open.return_value = response
        with patch.dict("os.environ", {preview["key_env"][0]: "test-secret-value"}):
            result = providers.complete(provider, "explicit-model", "Review this diff", **kwargs)
        return result, self.build_opener.return_value.open.call_args.args[0], response

    def test_metadata_and_previews_do_not_read_environment(self):
        with patch("coprogrammer.providers.os.environ") as env:
            info = providers.provider_info()
            preview = providers.build_request("glm", "explicit-model", "检查")
        self.assertFalse(env.mock_calls)
        self.assertEqual(info["glm"]["key_env"], ["ZAI_API_KEY", "GLM_API_KEY"])
        info["glm"]["key_env"].append("MUTATED")
        self.assertNotIn("MUTATED", providers.provider_info()["glm"]["key_env"])
        self.assertEqual(preview["url"], "https://api.z.ai/api/paas/v4/chat/completions")
        self.assertEqual(preview["body"]["messages"], [{"role": "user", "content": "检查"}])
        self.assertFalse(preview["body"]["stream"])
        self.assertNotIn("Authorization", preview["headers"])
        self.assertNotIn("x-api-key", preview["headers"])
        self.build_opener.assert_not_called()

    def test_anthropic_request_and_text_blocks(self):
        body = {"content": [{"type": "thinking", "thinking": "not user-facing"},
                            {"type": "text", "text": "First finding"},
                            {"type": "text", "text": "Second finding"}],
                "usage": {"input_tokens": 7, "output_tokens": 5,
                          "cache_read_input_tokens": 3, "cache_creation_input_tokens": 2},
                "stop_reason": "end_turn"}
        result, request, _ = self.run_complete(body, "anthropic", max_tokens=777)
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-api-key"), "test-secret-value")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(json.loads(request.data), {"model": "explicit-model", "max_tokens": 777,
                                                  "messages": [{"role": "user", "content": "Review this diff"}],
                                                  "stream": False})
        self.assertEqual(result["text"], "First finding\nSecond finding")
        self.assertEqual(result["usage"], {"input_tokens": 12, "output_tokens": 5, "total_tokens": 17})
        self.assertFalse(result["truncated"])

    def test_chat_providers_send_bearer_and_return_only_text(self):
        for provider in ("glm", "deepseek"):
            with self.subTest(provider=provider):
                result, request, response = self.run_complete(provider=provider)
                self.assertEqual(request.get_header("Authorization"), "Bearer test-secret-value")
                self.assertEqual(json.loads(request.data)["model"], "explicit-model")
                self.assertEqual(result["provider"], provider)
                self.assertEqual(result["text"], "Review complete")
                self.assertEqual(result["usage"], {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12})
                self.assertEqual(response.read_size, providers.MAX_RESPONSE_BYTES + 1)
                self.assertNotIn("private reasoning", json.dumps(result))
                self.assertIsInstance(self.build_opener.call_args.args[0], providers._NoRedirect)

    def test_china_root_is_explicit_and_prefers_glm_key(self):
        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        preview = providers.build_request("glm", "explicit-model", "review", base_url=base_url)
        self.assertEqual(preview["key_env"], ["GLM_API_KEY", "ZAI_API_KEY"])
        self.assertEqual(preview["url"], "https://open.bigmodel.cn/api/paas/v4/chat/completions")
        self.build_opener.return_value.open.return_value = FakeResponse(chat_response(), url=preview["url"])
        with patch.dict("os.environ", {"GLM_API_KEY": "china-key", "ZAI_API_KEY": "international-key"}):
            providers.complete("glm", "explicit-model", "review", base_url=base_url)
        request = self.build_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer china-key")

    def test_glm_alternative_key_and_explicit_proxy_root(self):
        url = "https://models.example.test/api/v4/chat/completions"
        self.build_opener.return_value.open.return_value = FakeResponse(chat_response(), url=url)
        with patch.dict("os.environ", {"GLM_API_KEY": "glm-key"}):
            providers.complete("glm", "explicit-model", "review", base_url="https://models.example.test/api/v4")
        request = self.build_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, url)
        self.assertEqual(request.get_header("Authorization"), "Bearer glm-key")

    def test_missing_key_is_actionable_and_does_not_call_network(self):
        with self.assertRaises(providers.ProviderError) as caught:
            providers.complete("deepseek", "explicit-model", "review")
        self.assertEqual(caught.exception.code, "missing_api_key")
        self.assertIn("DEEPSEEK_API_KEY", str(caught.exception))
        self.build_opener.assert_not_called()

    def test_input_validation_precedes_credentials_and_network(self):
        cases = [({"provider": []}, "unknown_provider"), ({"provider": "unknown"}, "unknown_provider"),
                 ({"model": None}, "invalid_model"), ({"model": ""}, "invalid_model"),
                 ({"model": "bad model"}, "invalid_model"), ({"model": "m" * 201}, "invalid_model"),
                 ({"prompt": []}, "invalid_prompt"), ({"prompt": "  "}, "invalid_prompt"),
                 ({"prompt": "\ud800"}, "invalid_prompt"),
                 ({"max_tokens": True}, "invalid_max_tokens"), ({"max_tokens": 0}, "invalid_max_tokens"),
                 ({"max_tokens": 2.5}, "invalid_max_tokens"), ({"max_tokens": 131073}, "invalid_max_tokens"),
                 ({"timeout": True}, "invalid_timeout"), ({"timeout": 0}, "invalid_timeout"),
                 ({"timeout": float("nan")}, "invalid_timeout"), ({"timeout": 601}, "invalid_timeout"),
                 ({"timeout": 10 ** 500}, "invalid_timeout")]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                args = {"provider": "deepseek", "model": "explicit-model", "prompt": "review"}
                args.update(changes)
                with self.assertRaises(providers.ProviderError) as caught:
                    providers.complete(**args)
                self.assertEqual(caught.exception.code, expected)
        self.build_opener.assert_not_called()

    def test_prompt_byte_limit_accounts_for_unicode(self):
        with patch.object(providers, "MAX_PROMPT_BYTES", 5):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.build_request("glm", "explicit-model", "检查")
        self.assertEqual(caught.exception.code, "prompt_too_large")

    def test_unsafe_base_urls_are_rejected_without_echo(self):
        urls = ["http://example.test", "https://secret@example.test", "https://user:secret@example.test",
                "https://example.test?key=secret", "https://example.test/#secret", "https://example.test?",
                "https://example.test#", "https:///path", "https://example.test:99999", "https://[bad",
                "https://example.test:0", "https://example.test/\nsecret", "https://example.test\\secret", 5]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(providers.ProviderError) as caught:
                    providers.build_request("deepseek", "explicit-model", "review", base_url=url)
                self.assertEqual(caught.exception.code, "invalid_base_url")
                self.assertNotIn("secret", json.dumps(caught.exception.as_dict()))

    def test_invalid_credential_characters_do_not_escape(self):
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "secret\nheader"}):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.complete("deepseek", "explicit-model", "review")
        self.assertEqual(caught.exception.code, "invalid_api_key")
        self.assertNotIn("secret", json.dumps(caught.exception.as_dict()))
        self.build_opener.assert_not_called()

    def test_http_errors_are_sanitized_and_never_retried(self):
        for status, code in [(301, "redirect_rejected"), (307, "redirect_rejected"),
                             (400, "request_rejected"), (401, "authentication_failed"),
                             (403, "authentication_failed"), (429, "rate_limited"),
                             (503, "provider_unavailable")]:
            with self.subTest(status=status):
                self.build_opener.reset_mock()
                error_body = io.BytesIO(b'{"message":"secret-key-and-diff"}')
                self.build_opener.return_value.open.side_effect = HTTPError(
                    "https://secret-key-and-diff", status, "secret-key-and-diff", {}, error_body)
                with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "secret-key-and-diff"}):
                    with self.assertRaises(providers.ProviderError) as caught:
                        providers.complete("deepseek", "explicit-model", "review")
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn("secret-key-and-diff", json.dumps(caught.exception.as_dict()))
                self.assertTrue(caught.exception.__suppress_context__)
                self.assertTrue(error_body.closed)
                self.build_opener.return_value.open.assert_called_once()

    def test_timeout_and_connection_errors_do_not_expose_transport_details(self):
        for error, code in [(TimeoutError("secret"), "timeout"),
                            (URLError(TimeoutError("secret")), "timeout"),
                            (URLError("secret"), "connection_failed"),
                            (OSError("secret"), "connection_failed")]:
            with self.subTest(error=type(error)):
                self.build_opener.return_value.open.side_effect = error
                with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "secret"}):
                    with self.assertRaises(providers.ProviderError) as caught:
                        providers.complete("deepseek", "explicit-model", "review")
                self.assertEqual(caught.exception.code, code)
                self.assertIn("unconfirmed", str(caught.exception))
                self.assertNotIn("secret", json.dumps(caught.exception.as_dict()))

    def test_redirect_handler_refuses_all_redirect_targets(self):
        handler = providers._NoRedirect()
        request = Request("https://api.deepseek.com/chat/completions", data=b"{}",
                          headers={"Authorization": "Bearer secret"})
        for code in (301, 302, 303, 307, 308):
            self.assertIsNone(handler.redirect_request(request, None, code, "redirect", {}, "https://other.test"))

    def test_redirected_response_is_rejected_even_with_replaced_transport(self):
        self.build_opener.return_value.open.return_value = FakeResponse(chat_response(), url="https://other.test")
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "secret"}):
            with self.assertRaises(providers.ProviderError) as caught:
                providers.complete("deepseek", "explicit-model", "review")
        self.assertEqual(caught.exception.code, "redirect_rejected")

    def test_invalid_json_and_response_shapes_fail_closed(self):
        cases = [b"not JSON secret", b"\xff", [], {}, {"error": "secret"}, {"choices": []},
                 {"choices": [None]}, {"choices": [{"message": None}]},
                 {"choices": [{"message": {"content": None}}]},
                 {"choices": [{"message": {"content": "  "}}]},
                 {"choices": [{"message": {"content": "\ud800"}}]},
                 {"choices": [{"message": {"content": ["secret"]}}]}]
        for body in cases:
            with self.subTest(body=body):
                with self.assertRaises(providers.ProviderError) as caught:
                    self.run_complete(body)
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertNotIn("secret", str(caught.exception))
        for body in [{"content": [None]}, {"content": [{"type": "text", "text": 42}]},
                     {"content": [{"type": "tool_use", "input": "secret"}]}]:
            with self.subTest(body=body):
                with self.assertRaises(providers.ProviderError):
                    self.run_complete(body, "anthropic")

    def test_response_read_is_bounded(self):
        with patch.object(providers, "MAX_RESPONSE_BYTES", 16):
            response = FakeResponse(b"x" * 200)
            self.build_opener.return_value.open.return_value = response
            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "secret"}):
                with self.assertRaises(providers.ProviderError) as caught:
                    providers.complete("deepseek", "explicit-model", "review")
        self.assertEqual(response.read_size, 17)
        self.assertEqual(caught.exception.code, "response_too_large")

    def test_unknown_usage_remains_unknown_and_missing_total_is_derived(self):
        for usage, expected in [(None, {"input_tokens": None, "output_tokens": None, "total_tokens": None}),
                                ({"prompt_tokens": True, "completion_tokens": -1},
                                 {"input_tokens": None, "output_tokens": None, "total_tokens": None}),
                                ({"prompt_tokens": 5, "completion_tokens": 6},
                                 {"input_tokens": 5, "output_tokens": 6, "total_tokens": 11})]:
            with self.subTest(usage=usage):
                result, _, _ = self.run_complete(chat_response(usage=usage))
                self.assertEqual(result["usage"], expected)

    def test_truncation_is_not_misreported_as_completed_review(self):
        body = chat_response(choices=[{"message": {"content": "Partial finding"}, "finish_reason": "length"}])
        result, _, _ = self.run_complete(body)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["finish_reason"], "length")

    def test_response_cannot_echo_secret_in_persisted_fields(self):
        body = chat_response(choices=[{"message": {"content": "Key: test-secret-value"},
                                      "finish_reason": "test-secret-value"}],
                             model="test-secret-value", usage={"prompt_tokens": "test-secret-value"})
        result, _, _ = self.run_complete(body)
        self.assertEqual(result["text"], "Key: [REDACTED]")
        self.assertNotIn("test-secret-value", json.dumps(result))
        self.assertEqual(result["model"], "explicit-model")
        self.assertIsNone(result["finish_reason"])


if __name__ == "__main__":
    unittest.main()
