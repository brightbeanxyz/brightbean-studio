from typing import Any

import httpx
from django.conf import settings


class ProviderError(RuntimeError):
    pass


def _post(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("AI provider request failed.") from exc
    if not isinstance(data, dict):
        raise ProviderError("AI provider returned invalid data.")
    return data


def _text(data: dict[str, Any], provider: str) -> str:
    try:
        if provider in {"openai", "openrouter"}:
            value = data["choices"][0]["message"]["content"]
        elif provider == "ollama":
            value = data["message"]["content"]
        elif provider == "anthropic":
            value = data["content"][0]["text"]
        else:
            value = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("AI provider returned no text.") from exc
    if not isinstance(value, str) or not value.strip():
        raise ProviderError("AI provider returned empty content.")
    return value.strip()


def generate_text(*, provider: str, model: str, system: str, prompt: str) -> str:
    if provider not in {"openai", "anthropic", "gemini", "openrouter", "ollama"}:
        raise ProviderError("Unsupported AI provider.")
    messages = [{"role": "user", "content": prompt}]
    if provider in {"openai", "openrouter"}:
        key_name = "OPENAI_API_KEY" if provider == "openai" else "OPENROUTER_API_KEY"
        key = getattr(settings, key_name, "")
        if not key:
            raise ProviderError(f"{key_name} is not configured.")
        url = (
            "https://api.openai.com/v1/chat/completions"
            if provider == "openai"
            else "https://openrouter.ai/api/v1/chat/completions"
        )
        default = "gpt-4o-mini" if provider == "openai" else "openai/gpt-4o-mini"
        return _text(
            _post(
                url,
                {"Authorization": f"Bearer {key}"},
                {"model": model or default, "messages": [{"role": "system", "content": system}, *messages]},
            ),
            provider,
        )
    if provider == "anthropic":
        key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured.")
        return _text(
            _post(
                "https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
                {
                    "model": model or "claude-3-5-haiku-latest",
                    "max_tokens": 1200,
                    "system": system,
                    "messages": messages,
                },
            ),
            provider,
        )
    if provider == "gemini":
        key = getattr(settings, "GEMINI_API_KEY", "")
        if not key:
            raise ProviderError("GEMINI_API_KEY is not configured.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-2.0-flash'}:generateContent?key={key}"
        return _text(
            _post(
                url,
                {},
                {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                },
            ),
            provider,
        )
    base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    return _text(
        _post(
            f"{base}/api/chat",
            {},
            {
                "model": model or "llama3.2",
                "stream": False,
                "messages": [{"role": "system", "content": system}, *messages],
            },
        ),
        provider,
    )
