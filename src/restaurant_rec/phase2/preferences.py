from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UserPreferences(BaseModel):
    """Structured user input for Phase 2 shortlist (see docs/phase-wise-architecture.md)."""

    location: str = Field(
        ...,
        min_length=1,
        description="Area filter: matches catalog `locality` or `city` (UI: chosen from GET /api/v1/localities)",
    )
    budget_max_inr: int = Field(
        ...,
        ge=100,
        le=100_000,
        description="Maximum approximate cost for two (INR); rows with cost above this are excluded",
    )
    cuisine: list[str] | None = Field(
        default=None,
        description="If set and non-empty, require at least one match against `cuisines`; else skip cuisine filter",
    )
    min_rating: float = Field(..., ge=0.0, le=5.0)
    extras: str | None = Field(default=None, description="Free text for Phase 3 LLM prompt / keyword boost")
    enable_rating_relax: bool = Field(
        default=True,
        description="If True and results are sparse, lower min_rating once by filter.rating_relax_delta",
    )

    @field_validator("location")
    @classmethod
    def strip_location(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("location cannot be empty")
        return s

    @field_validator("cuisine", mode="before")
    @classmethod
    def cuisine_to_list(cls, v: str | list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts or None
        out = [str(x).strip() for x in v if str(x).strip()]
        return out or None

    def cuisine_terms(self) -> list[str]:
        """Normalized list; empty means 'no cuisine filter'."""
        if not self.cuisine:
            return []
        return list(self.cuisine)
