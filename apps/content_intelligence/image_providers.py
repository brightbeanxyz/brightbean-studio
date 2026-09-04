import base64
from urllib.parse import urlsplit

import httpx

from .providers import ProviderError, _post

MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _decode_image(data):
    try:
        value = data["data"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Image provider returned invalid data.") from exc
    encoded = value.get("b64_json") if isinstance(value, dict) else None
    if encoded:
        try:
            image = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ProviderError("Image provider returned invalid image data.") from exc
        if len(image) > MAX_IMAGE_BYTES:
            raise ProviderError("Generated image exceeds the size limit.")
        return image
    url = value.get("url", "") if isinstance(value, dict) else ""
    host = (urlsplit(url).hostname or "").lower()
    if urlsplit(url).scheme != "https" or host != "apihub.agnes-ai.com":
        raise ProviderError("Image provider returned an untrusted URL.")
    try:
        response = httpx.get(url, timeout=30, follow_redirects=False)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderError("Generated image download failed.") from exc
    content_type = response.headers.get("content-type", "").split(";", 1)[0]
    if content_type not in {"image/png", "image/jpeg", "image/webp"} or len(response.content) > MAX_IMAGE_BYTES:
        raise ProviderError("Generated image failed validation.")
    return response.content


def generate_image(*, provider, model, prompt, size, api_key, timeout=60):
    if provider == "openai":
        data = _post(
            "https://api.openai.com/v1/images/generations",
            {"Authorization": f"Bearer {api_key}"},
            {"model": model or "gpt-image-1", "prompt": prompt, "size": size, "n": 1, "response_format": "b64_json"},
            timeout,
        )
    elif provider == "agnes":
        data = _post(
            "https://apihub.agnes-ai.com/v1/images/generations",
            {"Authorization": f"Bearer {api_key}"},
            {"model": model or "agnes-image-2.1-flash", "prompt": prompt, "size": size, "n": 1, "return_base64": True},
            timeout,
        )
    else:
        raise ProviderError("Unsupported image provider.")
    return _decode_image(data)
