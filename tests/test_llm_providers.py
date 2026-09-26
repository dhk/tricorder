from __future__ import annotations

import signal
import sys
import time
import types
import unittest

from tricorder.llm import providers


class AnthropicProviderTest(unittest.TestCase):
    def test_generate_passes_request_timeout(self):
        calls = {}

        class Messages:
            def create(self, **kwargs):
                calls.update(kwargs)
                return types.SimpleNamespace(
                    content=[types.SimpleNamespace(text="ok")]
                )

        provider = providers.AnthropicProvider(
            model="claude-test",
            client=types.SimpleNamespace(messages=Messages()),
        )

        text = provider.generate("system", "user", 123)

        self.assertEqual(text, "ok")
        self.assertEqual(calls["timeout"], providers.ANTHROPIC_REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(calls["max_tokens"], 123)

    @unittest.skipUnless(hasattr(signal, "SIGALRM"), "requires SIGALRM")
    def test_generate_raises_timeout_for_hung_call(self):
        original = providers.ANTHROPIC_WALL_CLOCK_TIMEOUT_SECONDS

        class Messages:
            def create(self, **kwargs):
                time.sleep(2)
                return types.SimpleNamespace(
                    content=[types.SimpleNamespace(text="late")]
                )

        provider = providers.AnthropicProvider(
            model="claude-test",
            client=types.SimpleNamespace(messages=Messages()),
        )

        try:
            providers.ANTHROPIC_WALL_CLOCK_TIMEOUT_SECONDS = 1
            with self.assertRaises(providers.LLMCallTimeout):
                provider.generate("system", "user", 123)
        finally:
            providers.ANTHROPIC_WALL_CLOCK_TIMEOUT_SECONDS = original


class BuildProviderTest(unittest.TestCase):
    def test_build_provider_configures_anthropic_client(self):
        original = sys.modules.get("anthropic")
        calls = {}

        class FakeAnthropicClient:
            def __init__(self, **kwargs):
                calls.update(kwargs)

        sys.modules["anthropic"] = types.SimpleNamespace(Anthropic=FakeAnthropicClient)
        config = types.SimpleNamespace(provider="anthropic", model="claude-test")

        try:
            provider = providers.build_provider(config, "secret")
        finally:
            if original is None:
                del sys.modules["anthropic"]
            else:
                sys.modules["anthropic"] = original

        self.assertIsInstance(provider, providers.AnthropicProvider)
        self.assertEqual(calls["api_key"], "secret")
        self.assertEqual(calls["max_retries"], providers.ANTHROPIC_MAX_RETRIES)
        self.assertEqual(calls["timeout"], providers.ANTHROPIC_REQUEST_TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
