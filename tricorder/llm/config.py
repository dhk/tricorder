"""LLM provider configuration and key resolution."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".learn-from-work" / "config"

DEFAULTS = {
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "keychain_service": "anthropic_api_key",
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "keychain_service": None,
    },
}

ENV_OVERRIDES = {
    "provider": "TRICORDER_LLM_PROVIDER",
    "model": "TRICORDER_LLM_MODEL",
    "api_key_env": "TRICORDER_LLM_API_KEY_ENV",
    "keychain_service": "TRICORDER_LLM_KEYCHAIN_SERVICE",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_env: str
    keychain_service: str | None = None


def _read_key_value_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _config_value(values: dict[str, str], key: str) -> str | None:
    env_key = ENV_OVERRIDES.get(key)
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    if key in values and values[key]:
        return values[key]
    return None


def detect_all_available_providers() -> list[str]:
    """Return all providers for which an API key is present in the environment."""
    return [p for p, d in DEFAULTS.items() if os.environ.get(d["api_key_env"])]


def _detect_provider_from_env() -> str | None:
    detected = []
    for provider, defaults in DEFAULTS.items():
        if os.environ.get(defaults["api_key_env"]):
            detected.append(provider)

    if len(detected) == 1:
        return detected[0]

    if len(detected) > 1:
        sys.exit(
            "❌  Both Anthropic and Gemini credentials are present. "
            "Pass --provider or set TRICORDER_LLM_PROVIDER explicitly."
        )

    return None


def resolve_llm_config(
    provider: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    keychain_service: str | None = None,
) -> LLMConfig:
    shared_config = _read_key_value_config(CONFIG_PATH)

    resolved_provider = (
        provider
        or _config_value(shared_config, "provider")
        or _detect_provider_from_env()
        or "anthropic"
    ).strip().lower()

    if resolved_provider not in DEFAULTS:
        sys.exit(
            f"❌  Unsupported LLM provider '{resolved_provider}'. "
            f"Supported: {', '.join(DEFAULTS)}"
        )

    defaults = DEFAULTS[resolved_provider]
    resolved_model = (
        model
        or _config_value(shared_config, "model")
        or defaults["model"]
    )
    resolved_api_key_env = (
        api_key_env
        or _config_value(shared_config, "api_key_env")
        or defaults["api_key_env"]
    )
    resolved_keychain_service = (
        keychain_service
        or _config_value(shared_config, "keychain_service")
        or defaults["keychain_service"]
    )

    return LLMConfig(
        provider=resolved_provider,
        model=resolved_model,
        api_key_env=resolved_api_key_env,
        keychain_service=resolved_keychain_service,
    )


def resolve_api_key(config: LLMConfig) -> str:
    key = os.environ.get(config.api_key_env, "")
    if key:
        return key

    if config.keychain_service:
        try:
            result = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-a",
                    os.environ.get("USER", ""),
                    "-s",
                    config.keychain_service,
                    "-w",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    sys.exit(
        f"❌  API key not found. Set {config.api_key_env} "
        + (
            f"or store it in the keychain service '{config.keychain_service}'."
            if config.keychain_service
            else "for this provider."
        )
    )
