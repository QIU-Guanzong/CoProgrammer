"""Small, explicit HTTP adapters for advisory reviews; never execute model output.

Only ``complete`` reads credentials or performs I/O.  Request previews are safe
to inspect before authorizing a billable call.  Model names are deliberately not
defaulted because availability and account access change independently of us.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PROMPT_BYTES = 1024 * 1024
MAX_OUTPUT_TOKENS = 131072

PROVIDERS = {
    "anthropic": {
        "label": "Claude / Anthropic",
        "protocol": "anthropic-messages",
        "base_url": "https://api.anthropic.com/v1",
        "path": "/messages",
        "key_env": ["ANTHROPIC_API_KEY"],
        "documentation": "https://platform.claude.com/docs/en/api/messages/create",
    },
    "glm": {
        "label": "GLM / Z.AI",
        "protocol": "chat-completions",
        "base_url": "https://api.z.ai/api/paas/v4",
        "path": "/chat/completions",
        "key_env": ["ZAI_API_KEY", "GLM_API_KEY"],
        "alternative_base_urls": ["https://open.bigmodel.cn/api/paas/v4"],
        "documentation": "https://docs.z.ai/api-reference/llm/chat-completion",
    },
    "deepseek": {
        "label": "DeepSeek",
        "protocol": "chat-completions",
        "base_url": "https://api.deepseek.com",
        "path": "/chat/completions",
        "key_env": ["DEEPSEEK_API_KEY"],
        "documentation": "https://api-docs.deepseek.com/api/create-chat-completion/",
    },
}


class ProviderError(ValueError):
    """An error safe to serialize, without server bodies or transport details."""

    def __init__(self, code: str, message: str, *, provider: str | None = None,
                 status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.status_code = status_code

    def as_dict(self) -> dict:
        result = {"code": self.code, "message": str(self)}
        if self.provider is not None:
            result["provider"] = self.provider
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


def provider_info() -> dict:
    """Return independent metadata, without probing the user's environment."""
    return copy.deepcopy(PROVIDERS)


def _base_url(value: object, provider: str) -> str:
    message = "Base URL must be HTTPS without credentials, query, or fragment."
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or any(char in value for char in "\\?#")):
        raise ProviderError("invalid_base_url", message, provider=provider)
    try:
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname or parts.username is not None
                or parts.password is not None or parts.query or parts.fragment):
            raise ValueError
        # Accessing port also validates malformed and out-of-range port numbers.
        if parts.port is not None and parts.port < 1:
            raise ValueError
        value.encode("ascii")
    except (ValueError, UnicodeError):
        raise ProviderError("invalid_base_url", message, provider=provider) from None
    return value.rstrip("/")


def build_request(provider: str, model: str, prompt: str, *,
                  base_url: str | None = None, max_tokens: int = 2048) -> dict:
    """Build a credential-free preview. ``base_url`` is the API root, not a route.

    The output cap is a local bound, not a claim about a model's supported limit.
    Custom HTTPS roots are caller-selected destinations and receive the API key
    when ``complete`` is explicitly invoked. No redirects are ever followed.
    """
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ProviderError("unknown_provider", "Choose a registered provider.")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
        raise ProviderError("invalid_model", "An explicit model identifier is required.", provider=provider)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ProviderError("invalid_prompt", "A nonempty text prompt is required.", provider=provider)
    try:
        prompt_size = len(prompt.encode("utf-8"))
    except UnicodeError:
        raise ProviderError("invalid_prompt", "The prompt must be valid UTF-8 text.", provider=provider) from None
    if prompt_size > MAX_PROMPT_BYTES:
        raise ProviderError("prompt_too_large", "The prompt exceeds the local size limit.", provider=provider)
    if type(max_tokens) is not int or not 1 <= max_tokens <= MAX_OUTPUT_TOKENS:
        raise ProviderError("invalid_max_tokens", "max_tokens must be an integer from 1 to 131072.", provider=provider)
    spec = PROVIDERS[provider]
    root = _base_url(spec["base_url"] if base_url is None else base_url, provider)
    key_env = list(spec["key_env"])
    if provider == "glm" and urlsplit(root).hostname == "open.bigmodel.cn":
        key_env = ["GLM_API_KEY", "ZAI_API_KEY"]
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if spec["protocol"] == "anthropic-messages":
        headers["anthropic-version"] = "2023-06-01"
    return {
        "provider": provider,
        "model": model,
        "url": root + spec["path"],
        "method": "POST",
        "headers": headers,
        "key_env": key_env,
        "body": {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        },
    }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Returning None makes urllib raise HTTPError before forwarding secrets.
        return None


def _http_error(provider: str, status: int) -> ProviderError:
    if 300 <= status < 400:
        code, message = "redirect_rejected", "Provider redirects are not allowed."
    elif status in (401, 403):
        code, message = "authentication_failed", "Provider rejected authentication or account access."
    elif status == 429:
        code, message = "rate_limited", "Provider rate or account limit was reached."
    elif status >= 500:
        code, message = "provider_unavailable", "Provider service is unavailable."
    else:
        code, message = "request_rejected", "Provider rejected the request; check model and parameters."
    return ProviderError(code, message, provider=provider, status_code=status)


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _usage(raw: object, anthropic: bool) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    incoming = _token_count(raw.get("input_tokens" if anthropic else "prompt_tokens"))
    outgoing = _token_count(raw.get("output_tokens" if anthropic else "completion_tokens"))
    # Anthropic reports cached input separately from newly processed input.
    if anthropic and incoming is not None:
        for key in ("cache_creation_input_tokens", "cache_read_input_tokens"):
            cached = _token_count(raw.get(key))
            if cached is not None:
                incoming += cached
    total = _token_count(raw.get("total_tokens")) if not anthropic else None
    if total is None and incoming is not None and outgoing is not None:
        total = incoming + outgoing
    return {"input_tokens": incoming, "output_tokens": outgoing, "total_tokens": total}


def _parse_response(raw: bytes, provider: str, model: str, secret: str) -> dict:
    error = ProviderError("invalid_response", "Provider returned an invalid or empty text response.", provider=provider)
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        raise error from None
    if not isinstance(result, dict) or "error" in result:
        raise error
    anthropic = PROVIDERS[provider]["protocol"] == "anthropic-messages"
    if anthropic:
        blocks = result.get("content")
        if not isinstance(blocks, list) or not all(isinstance(block, dict) for block in blocks):
            raise error
        text_blocks = [block.get("text") for block in blocks if block.get("type") == "text"]
        if not text_blocks or not all(isinstance(text, str) for text in text_blocks):
            raise error
        text = "\n".join(text_blocks)
        reason = result.get("stop_reason")
    else:
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise error
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise error
        text = message.get("content")
        reason = choices[0].get("finish_reason")
    if not isinstance(text, str) or not text.strip():
        raise error
    try:
        text.encode("utf-8")
    except UnicodeError:
        raise error from None
    known_reasons = ("stop", "end_turn", "length", "max_tokens", "stop_sequence",
                     "tool_use", "tool_calls", "content_filter", "sensitive", "refusal",
                     "pause_turn", "model_context_window_exceeded", "network_error")
    reason = reason if isinstance(reason, str) and reason in known_reasons else None
    return {
        "provider": provider,
        "model": model,
        "text": text.replace(secret, "[REDACTED]"),
        "usage": _usage(result.get("usage"), anthropic),
        "finish_reason": reason,
        "truncated": reason in ("length", "max_tokens", "model_context_window_exceeded"),
    }


def complete(provider: str, model: str, prompt: str, *, base_url: str | None = None,
             max_tokens: int = 2048, timeout: float = 60) -> dict:
    """Make one explicit advisory call, without retries, tools, or persistence.

    Credentials are environment-only. Transport and provider errors are reduced
    to safe codes; callers must not persist the in-memory HTTP request object.
    """
    preview = build_request(provider, model, prompt, base_url=base_url, max_tokens=max_tokens)
    if (type(timeout) not in (int, float) or not 0 < timeout <= 600
            or not math.isfinite(timeout)):
        raise ProviderError("invalid_timeout", "timeout must be greater than 0 and at most 600 seconds.", provider=provider)
    secret = next((os.environ[name] for name in preview["key_env"] if os.environ.get(name)), None)
    if secret is None:
        raise ProviderError("missing_api_key", "Set one of: " + ", ".join(preview["key_env"]), provider=provider)
    if not secret.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in secret):
        raise ProviderError("invalid_api_key", "The API key contains invalid header characters.", provider=provider)
    headers = dict(preview["headers"])
    if PROVIDERS[provider]["protocol"] == "anthropic-messages":
        headers["x-api-key"] = secret
    else:
        headers["Authorization"] = "Bearer " + secret
    request = Request(preview["url"], data=json.dumps(preview["body"], ensure_ascii=False).encode("utf-8"),
                      headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            status = response.status
            if type(status) is not int or not 100 <= status <= 599:
                raise ProviderError("invalid_response", "Provider returned an invalid HTTP status.", provider=provider)
            if not 200 <= status < 300:
                raise _http_error(provider, status)
            if response.geturl() != preview["url"]:
                raise ProviderError("redirect_rejected", "Provider redirects are not allowed.", provider=provider)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise _http_error(provider, status) from None
    except TimeoutError:
        raise ProviderError("timeout", "Provider request timed out; completion is unconfirmed.", provider=provider) from None
    except URLError as exc:
        code = "timeout" if isinstance(exc.reason, TimeoutError) else "connection_failed"
        raise ProviderError(code, "Provider connection failed; completion is unconfirmed.", provider=provider) from None
    except (OSError, HTTPException, ValueError) as exc:
        if isinstance(exc, ProviderError):
            raise
        raise ProviderError("connection_failed", "Provider connection failed; completion is unconfirmed.", provider=provider) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("response_too_large", "Provider response exceeds the local size limit.", provider=provider)
    return _parse_response(raw, provider, model, secret)
