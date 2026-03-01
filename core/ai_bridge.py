"""
AI Bridge — Universal LLM caller for Apex
==========================================
Reads config.yaml and routes call_ai(prompt) to the configured provider.
Drop-in replacement for any llm_caller / ask_llm / query_model function.

Usage:
    from core.ai_bridge import call_ai
    response = call_ai("Summarise this text: ...")

Switching providers: change 'provider' in config.yaml — no code changes needed.
"""

import os
import json
import logging
from pathlib import Path

import yaml
import requests

# ── Config ────────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).parent / "config.yaml"

def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _get_provider_cfg(config: dict) -> tuple[str, dict]:
    provider = config["provider"]
    cfg = config["providers"].get(provider)
    if cfg is None:
        raise ValueError(f"Provider '{provider}' not found in config.yaml")
    return provider, cfg

# ── Provider callers ──────────────────────────────────────────────────────────

def _call_ollama(prompt: str, cfg: dict) -> str:
    url = cfg["endpoint"].rstrip("/") + "/api/generate"
    params = cfg.get("parameters", {})
    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        **params,
    }
    resp = requests.post(url, json=payload, timeout=cfg.get("timeout", 120))
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _call_openai(prompt: str, cfg: dict) -> str:
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise EnvironmentError(
            f"Environment variable '{cfg['api_key_env']}' is not set."
        )
    url = cfg["endpoint"].rstrip("/") + "/chat/completions"
    params = cfg.get("parameters", {})
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        **params,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=cfg.get("timeout", 60))
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(prompt: str, cfg: dict) -> str:
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise EnvironmentError(
            f"Environment variable '{cfg['api_key_env']}' is not set."
        )
    url = cfg["endpoint"].rstrip("/") + "/messages"
    params = cfg.get("parameters", {})
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        **params,
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=cfg.get("timeout", 60))
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()

# ── Dispatch table ─────────────────────────────────────────────────────────────

_CALLERS = {
    "ollama":    _call_ollama,
    "openai":    _call_openai,
    "anthropic": _call_anthropic,
}

# ── Public API ─────────────────────────────────────────────────────────────────

def call_ai(prompt: str, system: str | None = None) -> str:
    """
    Send a prompt to the configured LLM provider and return the response string.

    Args:
        prompt:  The user message / query.
        system:  Optional system prompt. Prepended for Ollama, passed as a
                 system message for OpenAI/Anthropic if provided.

    Returns:
        The model's response as a plain string.

    Raises:
        ValueError:       Unknown provider in config.
        EnvironmentError: API key env var not set (OpenAI / Anthropic).
        requests.HTTPError: Non-2xx response from provider.
    """
    config = _load_config()
    provider, cfg = _get_provider_cfg(config)
    caller = _CALLERS.get(provider)
    if caller is None:
        raise ValueError(
            f"No caller implemented for provider '{provider}'. "
            f"Valid options: {list(_CALLERS)}"
        )

    # Merge system prompt into the user prompt for providers that need it inline
    if system:
        if provider == "ollama":
            prompt = f"{system}\n\n{prompt}"
        elif provider == "openai":
            # Re-route through a wrapper that injects the system message
            return _call_openai_with_system(prompt, system, cfg)
        elif provider == "anthropic":
            return _call_anthropic_with_system(prompt, system, cfg)

    logging.debug("[ai_bridge] provider=%s model=%s", provider, cfg["model"])
    return caller(prompt, cfg)


def _call_openai_with_system(prompt: str, system: str, cfg: dict) -> str:
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"Environment variable '{cfg['api_key_env']}' is not set.")
    url = cfg["endpoint"].rstrip("/") + "/chat/completions"
    params = cfg.get("parameters", {})
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        **params,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=cfg.get("timeout", 60))
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic_with_system(prompt: str, system: str, cfg: dict) -> str:
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"Environment variable '{cfg['api_key_env']}' is not set.")
    url = cfg["endpoint"].rstrip("/") + "/messages"
    params = cfg.get("parameters", {})
    payload = {
        "model": cfg["model"],
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        **params,
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=cfg.get("timeout", 60))
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


# ── CLI smoke test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    test_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Say hello in one sentence."
    print(f"Sending: {test_prompt!r}\n")
    try:
        result = call_ai(test_prompt)
        print(f"Response:\n{result}")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
