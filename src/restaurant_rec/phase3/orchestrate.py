from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.filter import FilterEmptyReason, filter_restaurants_with_config
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase3 import prompts
from restaurant_rec.phase3.env_util import load_project_dotenv
from restaurant_rec.phase3.groq_client import complete_chat
from restaurant_rec.phase3.models import LlmRecommendationsPayload
from restaurant_rec.phase3.parse import parse_and_validate_llm_payload


def _cost_display(cost: int | None, tier: str | None) -> str:
    if cost is not None:
        return f"₹{cost} for two"
    if tier:
        return f"{tier} tier (cost not listed)"
    return "unknown"


def _empty_summary(reason: FilterEmptyReason) -> str:
    return {
        FilterEmptyReason.NO_LOCATION: "No restaurants matched that location.",
        FilterEmptyReason.NO_CUISINE: "No restaurants matched the cuisine filter in that area.",
        FilterEmptyReason.NO_RATING: "No restaurants met the minimum rating with your other filters.",
        FilterEmptyReason.NO_BUDGET: "No restaurants matched your maximum budget (cost for two) in this area.",
        FilterEmptyReason.OK: "No candidates remained after filtering.",
    }.get(reason, "No recommendations available.")


@dataclass
class RecommendationMeta:
    shortlist_size: int
    model: str
    prompt_version: str
    filter_reason: str
    used_llm: bool
    rating_relaxed: bool = False
    effective_min_rating: float | None = None
    llm_parse_failed: bool = False


@dataclass
class RecommendationResult:
    """Phase 3 (+ Phase 2) output; aligns with Phase 4 response body."""

    summary: str
    items: list[dict[str, Any]]
    meta: RecommendationMeta


def _rows_by_id(shortlist: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r["id"]): r for r in shortlist if r.get("id") is not None}


def _build_items_from_llm(
    shortlist: list[dict[str, Any]],
    payload: LlmRecommendationsPayload,
) -> list[dict[str, Any]]:
    by_id = _rows_by_id(shortlist)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in payload.recommendations:
        rid = rec.restaurant_id
        if rid in seen or rid not in by_id:
            continue
        seen.add(rid)
        row = by_id[rid]
        cuisines = row.get("cuisines") or []
        if not isinstance(cuisines, list):
            cuisines = list(cuisines) if cuisines is not None else []
        out.append(
            {
                "id": rid,
                "name": row.get("name"),
                "cuisines": cuisines,
                "rating": row.get("rating"),
                "estimated_cost": row.get("budget_tier"),
                "cost_display": _cost_display(row.get("cost_for_two"), row.get("budget_tier")),
                "explanation": rec.explanation.strip(),
                "rank": rec.rank,
            }
        )
    out.sort(key=lambda x: x["rank"])
    for i, it in enumerate(out, start=1):
        it["rank"] = i
    return out


def _heuristic_items(shortlist: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, row in enumerate(shortlist[:top_k], start=1):
        cuisines = row.get("cuisines") or []
        if not isinstance(cuisines, list):
            cuisines = list(cuisines) if cuisines is not None else []
        items.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "cuisines": cuisines,
                "rating": row.get("rating"),
                "estimated_cost": row.get("budget_tier"),
                "cost_display": _cost_display(row.get("cost_for_two"), row.get("budget_tier")),
                "explanation": "Ranked by rating and review volume (automated fallback).",
                "rank": i,
            }
        )
    return items


def recommend(
    catalog: pd.DataFrame,
    preferences: UserPreferences,
    cfg: AppConfig,
    *,
    config_path: Path | str | None = None,
) -> RecommendationResult:
    """
    Phase 3 orchestration: Phase 2 shortlist → Groq → merge with catalog facts.

    Loads `.env` (for `GROQ_API_KEY`) relative to `config_path` or project root.
    """
    load_project_dotenv(config_path)

    fr = filter_restaurants_with_config(catalog, preferences, cfg)
    top_k = cfg.groq.top_k_recommendations
    base_meta = RecommendationMeta(
        shortlist_size=len(fr.items),
        model=cfg.groq.model,
        prompt_version=cfg.groq.prompt_version,
        filter_reason=fr.reason.value,
        used_llm=False,
        rating_relaxed=fr.rating_relaxed,
        effective_min_rating=fr.effective_min_rating,
    )

    if fr.reason != FilterEmptyReason.OK or not fr.items:
        return RecommendationResult(
            summary=_empty_summary(fr.reason),
            items=[],
            meta=base_meta,
        )

    allowed_ids = {str(x["id"]) for x in fr.items if x.get("id") is not None}
    messages = prompts.build_messages(fr.items, preferences, top_k)

    try:
        text = complete_chat(messages, cfg)
    except RuntimeError as e:
        # Missing API key — still return heuristic so local dev works when key absent
        if "GROQ_API_KEY" in str(e):
            items = _heuristic_items(fr.items, top_k)
            return RecommendationResult(
                summary="Showing top picks by rating (Groq API key not configured).",
                items=items,
                meta=replace(base_meta, used_llm=False, llm_parse_failed=False),
            )
        raise

    parsed = parse_and_validate_llm_payload(text, allowed_ids=allowed_ids)
    if parsed is None:
        messages_retry = messages + [
            {"role": "user", "content": prompts.JSON_ONLY_REMINDER},
        ]
        text2 = complete_chat(messages_retry, cfg)
        parsed = parse_and_validate_llm_payload(text2, allowed_ids=allowed_ids)

    if parsed is None:
        items = _heuristic_items(fr.items, top_k)
        return RecommendationResult(
            summary="Here are strong options from your shortlist (could not parse model JSON).",
            items=items,
            meta=replace(base_meta, used_llm=True, llm_parse_failed=True),
        )

    items = _build_items_from_llm(fr.items, parsed)
    if not items:
        items = _heuristic_items(fr.items, top_k)
        return RecommendationResult(
            summary=parsed.summary or "Here are top picks from your shortlist.",
            items=items,
            meta=replace(base_meta, used_llm=True, llm_parse_failed=True),
        )

    return RecommendationResult(
        summary=parsed.summary or "Recommendations based on your preferences.",
        items=items[:top_k],
        meta=replace(base_meta, used_llm=True, llm_parse_failed=False),
    )
