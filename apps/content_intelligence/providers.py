from typing import Any

import httpx
from django.conf import settings


class ProviderError(RuntimeError):
    pass


def _post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("AI provider request failed.") from exc
    if not isinstance(data, dict):
        raise ProviderError("AI provider returned invalid data.")
    return data


def _text(data: dict[str, Any], provider: str) -> str:
    try:
        if provider in {"openai", "openrouter", "agnes"}:
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


def generate_text(*, provider: str, model: str, system: str, prompt: str, api_key: str = "", base_url: str = "", timeout: int = 60) -> str:
    if provider not in {"openai", "anthropic", "gemini", "openrouter", "ollama", "agnes"}:
        raise ProviderError("Unsupported AI provider.")
    messages = [{"role": "user", "content": prompt}]
    if provider in {"openai", "openrouter", "agnes"}:
        key_names = {"openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "agnes": "AGNES_API_KEY"}
        key_name = key_names[provider]
        key = api_key or getattr(settings, key_name, "")
        if not key:
            raise ProviderError(f"{key_name} is not configured.")
        urls = {"openai": "https://api.openai.com/v1/chat/completions", "openrouter": "https://openrouter.ai/api/v1/chat/completions", "agnes": "https://apihub.agnes-ai.com/v1/chat/completions"}
        defaults = {"openai": "gpt-4o-mini", "openrouter": "openai/gpt-4o-mini", "agnes": "agnes-2.5-flash"}
        url = f"{base_url.rstrip('/')}/v1/chat/completions" if base_url else urls[provider]
        return _text(
            _post(
                url,
                {"Authorization": f"Bearer {key}"},
                {"model": model or defaults[provider], "messages": [{"role": "system", "content": system}, *messages]}, timeout,
            ),
            provider,
        )
    if provider == "anthropic":
        key = api_key or getattr(settings, "ANTHROPIC_API_KEY", "")
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
                timeout,
            ),
            provider,
        )
    if provider == "gemini":
        key = api_key or getattr(settings, "GEMINI_API_KEY", "")
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
                timeout,
            ),
            provider,
        )
    base = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    return _text(
        _post(
            f"{base}/api/chat",
            {},
            {
                "model": model or "llama3.2",
                "stream": False,
                "messages": [{"role": "system", "content": system}, *messages],
            },
            timeout,
        ),
        provider,
    )
