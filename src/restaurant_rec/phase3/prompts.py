from __future__ import annotations

import json
from typing import Any

from restaurant_rec.phase2.preferences import UserPreferences

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """You are an expert restaurant recommender for Indian cities. You MUST only rank and \
describe restaurants that appear in the provided shortlist JSON. Each restaurant has a stable `id` — \
use that exact `restaurant_id` in your output. Do not invent venues or facts. The user gave a maximum \
budget in INR for two (`budget_max_inr`) and a minimum rating; only recommend from the shortlist (already filtered). \
If the shortlist is empty, say there are no matches.

Respond with a single JSON object (no markdown fences) using this exact shape:
{"summary": "<one short overview>", "recommendations": [{"restaurant_id": "<id from data>", "rank": 1, "explanation": "<one paragraph, cite cuisine/rating/cost from data>"}]}

Rank from 1 = best. Keep explanations to one paragraph each."""


def _shortlist_for_prompt(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slim: list[dict[str, Any]] = []
    for row in items:
        cuisines = row.get("cuisines") or []
        if not isinstance(cuisines, list):
            cuisines = list(cuisines) if cuisines is not None else []
        slim.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "city": row.get("city"),
                "locality": row.get("locality"),
                "cuisines": cuisines,
                "rating": row.get("rating"),
                "cost_for_two": row.get("cost_for_two"),
                "budget_tier": row.get("budget_tier"),
            }
        )
    return slim


def build_user_message(
    shortlist: list[dict[str, Any]],
    preferences: UserPreferences,
    top_k: int,
) -> str:
    prefs = {
        "locality": preferences.location,
        "budget_max_inr": preferences.budget_max_inr,
        "cuisine_filter": preferences.cuisine_terms(),
        "min_rating": preferences.min_rating,
        "extras": preferences.extras,
    }
    body = {
        "user_preferences": prefs,
        "shortlist": _shortlist_for_prompt(shortlist),
        "instructions": (
            f"Pick the top {top_k} restaurants for this user from the shortlist only. "
            "Order by true fit (cuisine match, rating, cost, and extras). Output JSON only."
        ),
    }
    return json.dumps(body, ensure_ascii=False, indent=2)


def build_messages(
    shortlist: list[dict[str, Any]],
    preferences: UserPreferences,
    top_k: int,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(shortlist, preferences, top_k)},
    ]


JSON_ONLY_REMINDER = (
    "Your previous reply was not valid JSON. Reply with ONLY a single JSON object, "
    'no markdown, no code fences, matching: {"summary":"...","recommendations":[...]}.'
)
