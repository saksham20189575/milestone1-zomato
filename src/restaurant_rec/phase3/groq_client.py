from __future__ import annotations

import os

from groq import Groq

from restaurant_rec.config import AppConfig


def get_groq_api_key() -> str | None:
    return os.environ.get("GROQ_API_KEY")


def complete_chat(
    messages: list[dict[str, str]],
    cfg: AppConfig,
) -> str:
    """Call Groq chat completions; raises if API key is missing."""
    key = get_groq_api_key()
    if not key or not key.strip():
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to a .env file in the project root or export it in the environment."
        )
    client = Groq(api_key=key.strip())
    g = cfg.groq
    resp = client.chat.completions.create(
        model=g.model,
        messages=messages,
        temperature=g.temperature,
        max_tokens=g.max_tokens,
        timeout=g.request_timeout_seconds,
    )
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        return ""
    return content.strip()
