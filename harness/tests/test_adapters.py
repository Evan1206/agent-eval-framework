from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from agent_eval.adapters import AnthropicAPIAgent, HTTPAgent, MockAgent, create_agent


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class AdapterTests(unittest.TestCase):
    def test_factory_switches_all_supported_types(self):
        self.assertIsInstance(create_agent({"type": "mock"}), MockAgent)
        self.assertIsInstance(
            create_agent({"type": "http", "url": "https://agent.invalid"}),
            HTTPAgent,
        )
        self.assertIsInstance(
            create_agent({"type": "anthropic_api", "model": "test-model"}),
            AnthropicAPIAgent,
        )

    @mock.patch("agent_eval.adapters.urllib.request.urlopen")
    def test_http_agent_posts_prompt_and_normalizes_response(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "text": "response",
                "tool_calls": [{"name": "lookup", "args": {}}],
                "usage": {"input_tokens": 10, "output_tokens": 4},
            }
        )
        agent = HTTPAgent(
            {
                "url": "https://agent.invalid",
                "timeout_seconds": 5,
                "input_cost_per_million_usd": 2,
                "output_cost_per_million_usd": 4,
            }
        )

        result = agent.respond("hello")

        self.assertEqual(result["text"], "response")
        self.assertEqual(result["usage"]["input_tokens"], 10)
        self.assertEqual(result["usage"]["output_tokens"], 4)
        self.assertEqual(result["usage"]["cost_usd"], 0.000036)
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"prompt": "hello"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)

    def test_anthropic_rejects_nonempty_config_key(self):
        with self.assertRaisesRegex(ValueError, "Do not put an API key in config"):
            AnthropicAPIAgent(
                {"model": "test-model", "api_key": "must-not-be-used"}
            )

    def test_anthropic_requires_environment_key_at_call_time(self):
        agent = AnthropicAPIAgent(
            {"model": "test-model", "api_key_env": "TEST_ANTHROPIC_ENV"}
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TEST_ANTHROPIC_ENV"):
                agent.respond("hello")

    @mock.patch("agent_eval.adapters.urllib.request.urlopen")
    def test_anthropic_maps_text_and_tool_blocks(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "content": [
                    {"type": "text", "text": "response"},
                    {"type": "tool_use", "name": "lookup", "input": {"id": 1}},
                ],
                "usage": {"input_tokens": 12, "output_tokens": 3},
            }
        )
        agent = AnthropicAPIAgent(
            {"model": "test-model", "api_key_env": "TEST_ANTHROPIC_ENV"}
        )
        with mock.patch.dict(os.environ, {"TEST_ANTHROPIC_ENV": "runtime-secret"}):
            result = agent.respond("hello")

        self.assertEqual(result["text"], "response")
        self.assertEqual(
            result["tool_calls"], [{"name": "lookup", "args": {"id": 1}}]
        )
        self.assertEqual(result["usage"]["input_tokens"], 12)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["X-api-key"], "runtime-secret")
        self.assertNotIn("runtime-secret", request.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
