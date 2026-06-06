"""Resolve the active LLM provider for synthesis."""

from __future__ import annotations

from .config import resolve_api_key, resolve_llm_config
from .providers import build_provider


def build_llm_provider(
    provider: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    keychain_service: str | None = None,
):
    config = resolve_llm_config(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        keychain_service=keychain_service,
    )
    api_key = resolve_api_key(config)
    provider_obj = build_provider(config, api_key)
    provider_obj.config = config
    return provider_obj
