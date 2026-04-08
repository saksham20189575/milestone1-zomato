from __future__ import annotations

import json
import re
from typing import Any

from restaurant_rec.phase3.models import LlmRecommendationsPayload


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse: raw JSON, fenced block, or first balanced object."""
    t = text.strip()
    try:
        out = json.loads(t)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        pass

    m = _FENCE_RE.search(text)
    if m:
        try:
            out = json.loads(m.group(1))
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(text[start:])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def parse_and_validate_llm_payload(
    text: str,
    *,
    allowed_ids: set[str],
) -> LlmRecommendationsPayload | None:
    raw = extract_json_object(text)
    if raw is None:
        return None
    try:
        payload = LlmRecommendationsPayload.model_validate(raw)
    except Exception:
        return None

    # Drop hallucinated ids; keep order by rank
    filtered = [r for r in payload.recommendations if r.restaurant_id in allowed_ids]
    filtered.sort(key=lambda x: x.rank)
    if not filtered:
        return None
    return LlmRecommendationsPayload(summary=payload.summary, recommendations=filtered)
