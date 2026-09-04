"""Provider implementations for synthesis-time LLM calls."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests


class LLMProvider:
    name: str
    model: str

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        raise NotImplementedError


MIN_HARD_TIMEOUT_S = 90       # wall-clock ceiling for an ordinary call
SECONDS_PER_OUTPUT_TOKEN = 1 / 40  # generous generation-rate allowance for large max_tokens


def call_budget_s(max_tokens: int) -> int:
    """Wall-clock ceiling for one call: 90s, or longer when a large response is requested.

    A normal Phase 1 call finishes in seconds; a Phase 4 call asking for 8192
    output tokens can legitimately run two to three minutes. A flat ceiling
    would kill the second kind, so the budget scales with max_tokens.
    """
    return max(MIN_HARD_TIMEOUT_S, int(30 + max_tokens * SECONDS_PER_OUTPUT_TOKEN))


class LLMCallTimeout(RuntimeError):
    """Raised when a single model call exceeds its wall-clock budget."""


@dataclass
class AnthropicProvider(LLMProvider):
    model: str
    client: object
    name: str = "anthropic"

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        # The SDK's own timeout has been observed not to end a call whose TLS
        # read blocks (2026-09-03: one call held a socket for an hour at zero
        # CPU), and an alarm raised inside the SDK's read is caught by its retry
        # loop. So the call runs on a daemon thread and the caller waits with a
        # hard wall-clock budget; a call that never returns is abandoned and
        # reported as LLMCallTimeout, which the scripts' retry path handles.
        import threading

        budget = call_budget_s(max_tokens)
        box: dict = {}

        def _call():
            try:
                msg = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    timeout=float(max(30, budget - 15)),
                )
                box["text"] = msg.content[0].text
            except BaseException as e:  # noqa: BLE001 - surface anything the SDK raises
                box["error"] = e

        worker = threading.Thread(target=_call, name="anthropic-call", daemon=True)
        worker.start()
        worker.join(budget)
        if worker.is_alive():
            raise LLMCallTimeout(f"model call exceeded {budget}s wall clock; abandoned")
        if "error" in box:
            raise box["error"]
        return box["text"]


@dataclass
class GeminiProvider(LLMProvider):
    model: str
    api_key: str
    session: requests.Session
    name: str = "gemini"

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        response = self.session.post(
            url,
            params={"key": self.api_key},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini response had no candidates: {json.dumps(data)[:500]}")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError(f"Gemini response had no text parts: {json.dumps(data)[:500]}")

        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError(f"Gemini response text was empty: {json.dumps(data)[:500]}")
        return text


def build_provider(config, api_key: str):
    if config.provider == "anthropic":
        try:
            import anthropic
        except ImportError:
            raise SystemExit("Missing dependency: pip install anthropic")

        return AnthropicProvider(
            model=config.model,
            client=anthropic.Anthropic(api_key=api_key, timeout=float(MIN_HARD_TIMEOUT_S - 15), max_retries=1),
        )

    if config.provider == "gemini":
        return GeminiProvider(
            model=config.model,
            api_key=api_key,
            session=requests.Session(),
        )

    raise SystemExit(f"Unsupported LLM provider: {config.provider}")
