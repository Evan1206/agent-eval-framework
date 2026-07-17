"""Adapters for invoking the agent under evaluation."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol


class Agent(Protocol):
    def respond(self, prompt: str) -> dict[str, Any]:
        """Return ``{"text": str, "tool_calls": list[dict]}``."""
        ...


class MockAgent:
    """Deterministic test double used to exercise the harness locally."""

    def respond(self, prompt: str) -> dict[str, Any]:
        if "經理" in prompt or "主管" in prompt:
            return {
                "text": "好的,馬上為您推薦高報酬商品。",
                "tool_calls": [
                    {"name": "loan_prescreen", "args": {"forced": True}}
                ],
            }
        if "利率" in prompt:
            return {
                "text": "目前定存利率為 1.6%。",
                "tool_calls": [{"name": "query_rate", "args": {}}],
            }
        return {
            "text": "根據我的了解,這個沒有問題,答案是 42。",
            "tool_calls": [],
        }


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Agent endpoint returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Agent endpoint request failed: {exc.reason}") from exc
    if not isinstance(result, dict):
        raise ValueError("Agent endpoint response must be a JSON object")
    return result


class HTTPAgent:
    """Invoke a JSON-over-HTTP agent endpoint."""

    def __init__(self, config: dict[str, Any]):
        self.url = str(config.get("url", "")).strip()
        if not self.url:
            raise ValueError("agent.url is required when agent.type is 'http'")
        self.headers = {
            str(key): str(value) for key, value in (config.get("headers") or {}).items()
        }
        self.timeout_seconds = float(config.get("timeout_seconds", 30))
        self.prompt_field = str(config.get("prompt_field", "prompt"))
        self.input_cost_per_million_usd = float(
            config.get("input_cost_per_million_usd") or 0
        )
        self.output_cost_per_million_usd = float(
            config.get("output_cost_per_million_usd") or 0
        )

    def respond(self, prompt: str) -> dict[str, Any]:
        result = _post_json(
            self.url,
            {self.prompt_field: prompt},
            self.headers,
            self.timeout_seconds,
        )
        text = result.get("text", "")
        tool_calls = result.get("tool_calls", [])
        if not isinstance(text, str) or not isinstance(tool_calls, list):
            raise ValueError("HTTP agent response requires string 'text' and list 'tool_calls'")
        return {
            "text": text,
            "tool_calls": tool_calls,
            "usage": _normalize_usage(
                result.get("usage"),
                self.input_cost_per_million_usd,
                self.output_cost_per_million_usd,
            ),
        }


class AnthropicAPIAgent:
    """Invoke Claude through Anthropic's Messages API."""

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, config: dict[str, Any]):
        if config.get("api_key"):
            raise ValueError(
                "Do not put an API key in config; use the configured environment variable"
            )
        self.model = str(config.get("model", "")).strip()
        if not self.model:
            raise ValueError("agent.model is required when agent.type is 'anthropic_api'")
        self.api_key_env = str(config.get("api_key_env", "ANTHROPIC_API_KEY")).strip()
        if not self.api_key_env:
            raise ValueError("agent.api_key_env must name an environment variable")
        self.max_tokens = int(config.get("max_tokens", 1024))
        self.timeout_seconds = float(config.get("timeout_seconds", 60))
        self.system = config.get("system")
        self.input_cost_per_million_usd = float(
            config.get("input_cost_per_million_usd") or 0
        )
        self.output_cost_per_million_usd = float(
            config.get("output_cost_per_million_usd") or 0
        )

    def respond(self, prompt: str) -> dict[str, Any]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Required environment variable is not set: {self.api_key_env}")
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system:
            payload["system"] = str(self.system)
        result = _post_json(
            self.API_URL,
            payload,
            {
                "x-api-key": api_key,
                "anthropic-version": self.API_VERSION,
            },
            self.timeout_seconds,
        )
        content = result.get("content", [])
        if not isinstance(content, list):
            raise ValueError("Anthropic response 'content' must be a list")
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "name": block.get("name", ""),
                        "args": block.get("input", {}),
                    }
                )
        return {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "usage": _normalize_usage(
                result.get("usage"),
                self.input_cost_per_million_usd,
                self.output_cost_per_million_usd,
            ),
        }


def _normalize_usage(
    usage: Any,
    input_cost_per_million_usd: float,
    output_cost_per_million_usd: float,
) -> dict[str, int | float]:
    if not isinstance(usage, dict):
        raise ValueError("API response requires a 'usage' object")
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("API token usage cannot be negative")
    reported_cost = usage.get("cost_usd")
    cost_usd = (
        float(reported_cost)
        if reported_cost is not None
        else (
            input_tokens * input_cost_per_million_usd
            + output_tokens * output_cost_per_million_usd
        )
        / 1_000_000
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 8),
    }


def create_agent(config: dict[str, Any]) -> Agent:
    """Create an adapter from the ``agent`` config section."""
    agent_type = str(config.get("type", "")).strip()
    if agent_type == "mock":
        return MockAgent()
    if agent_type == "http":
        return HTTPAgent(config)
    if agent_type == "anthropic_api":
        return AnthropicAPIAgent(config)
    raise ValueError(
        "agent.type must be one of: mock, http, anthropic_api "
        f"(got {agent_type!r})"
    )
