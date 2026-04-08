from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BudgetTier = Literal["low", "medium", "high"]


class RestaurantRecord(BaseModel):
    """Canonical catalog row (Phase 1). Stored in Parquet; lists serialized per Arrow."""

    id: str
    name: str
    city: str
    locality: str = Field(
        ...,
        description="Main listing area: Zomato listed_in(city), else raw location",
    )
    cuisines: list[str]
    rating: float | None = None
    cost_for_two: int | None = None
    budget_tier: BudgetTier | None = None
    votes: int | None = None
    address: str | None = None
    url: str | None = None
    raw_features: str | None = Field(
        default=None,
        description="JSON string: rest_type, online_order, book_table, listed_in_type, dish_liked, etc.",
    )
