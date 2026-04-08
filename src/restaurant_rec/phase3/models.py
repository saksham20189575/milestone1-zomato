from __future__ import annotations

from pydantic import BaseModel, Field


class LlmRecommendationItem(BaseModel):
    """Validated shape of each element in the model JSON (§3.3)."""

    restaurant_id: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    explanation: str = Field(..., min_length=1)


class LlmRecommendationsPayload(BaseModel):
    summary: str = ""
    recommendations: list[LlmRecommendationItem] = Field(default_factory=list)
