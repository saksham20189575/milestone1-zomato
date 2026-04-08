from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from restaurant_rec.phase3.orchestrate import RecommendationResult


class LocationsResponse(BaseModel):
    """Distinct catalog cities (legacy / diagnostics)."""

    locations: list[str]


class LocalitiesResponse(BaseModel):
    """Distinct catalog localities for UI dropdowns."""

    localities: list[str]


class RecommendItemOut(BaseModel):
    id: str
    name: str | None = None
    cuisines: list[str] = Field(default_factory=list)
    rating: float | None = None
    estimated_cost: str | None = None
    cost_display: str = ""
    explanation: str = ""
    rank: int


class RecommendMetaOut(BaseModel):
    """Response meta (architecture §4.2 + Phase 3 diagnostics)."""

    shortlist_size: int
    model: str
    prompt_version: str
    filter_reason: str = "OK"
    used_llm: bool = False
    rating_relaxed: bool = False
    effective_min_rating: float | None = None
    llm_parse_failed: bool = False


class RecommendResponse(BaseModel):
    summary: str
    items: list[RecommendItemOut]
    meta: RecommendMetaOut


def result_to_response(result: RecommendationResult) -> RecommendResponse:
    items: list[RecommendItemOut] = []
    for it in result.items:
        cuisines = it.get("cuisines") or []
        if not isinstance(cuisines, list):
            cuisines = list(cuisines) if cuisines is not None else []
        items.append(
            RecommendItemOut(
                id=str(it.get("id", "")),
                name=it.get("name"),
                cuisines=cuisines,
                rating=_maybe_float(it.get("rating")),
                estimated_cost=it.get("estimated_cost"),
                cost_display=str(it.get("cost_display") or ""),
                explanation=str(it.get("explanation") or ""),
                rank=int(it.get("rank", 0)),
            )
        )
    m = result.meta
    meta = RecommendMetaOut(
        shortlist_size=m.shortlist_size,
        model=m.model,
        prompt_version=m.prompt_version,
        filter_reason=m.filter_reason,
        used_llm=m.used_llm,
        rating_relaxed=m.rating_relaxed,
        effective_min_rating=m.effective_min_rating,
        llm_parse_failed=m.llm_parse_failed,
    )
    return RecommendResponse(summary=result.summary, items=items, meta=meta)


def _maybe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
