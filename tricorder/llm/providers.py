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


@dataclass
class AnthropicProvider(LLMProvider):
    model: str
    client: object
    name: str = "anthropic"

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text


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
            client=anthropic.Anthropic(api_key=api_key),
        )

    if config.provider == "gemini":
        return GeminiProvider(
            model=config.model,
            api_key=api_key,
            session=requests.Session(),
        )

    raise SystemExit(f"Unsupported LLM provider: {config.provider}")
