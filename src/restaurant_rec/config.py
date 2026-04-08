from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class DatasetConfig(BaseModel):
    id: str
    split: str = "train"


class PathsConfig(BaseModel):
    raw_snapshot: Path
    processed_catalog: Path
    ingest_report: Path


class RatingConfig(BaseModel):
    min_valid: float = 0.0
    max_valid: float = 5.0


class BudgetTiersInrConfig(BaseModel):
    low_max: int = 500
    high_min: int = 1200


class FilterConfig(BaseModel):
    """Phase 2 deterministic shortlist tuning."""

    rating_relax_delta: float = Field(default=0.5, ge=0.0, le=5.0)
    min_candidates_for_relax: int = Field(default=5, ge=1)
    max_shortlist_candidates: int = Field(
        default=40,
        ge=5,
        le=200,
        description="Fixed cap on rows passed from filter to the LLM (not user-controlled)",
    )


class GroqConfig(BaseModel):
    """Phase 3 Groq LLM (non-secret settings; API key via GROQ_API_KEY in .env)."""

    model: str = "llama-3.3-70b-versatile"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=256, le=32768)
    top_k_recommendations: int = Field(default=5, ge=1, le=20)
    request_timeout_seconds: float = Field(default=60.0, ge=5.0)
    prompt_version: str = "v1"


class AppConfig(BaseModel):
    dataset: DatasetConfig
    paths: PathsConfig
    rating: RatingConfig = Field(default_factory=RatingConfig)
    budget_tiers_inr: BudgetTiersInrConfig = Field(default_factory=BudgetTiersInrConfig)
    city_aliases: dict[str, str] = Field(default_factory=dict)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    groq: GroqConfig = Field(default_factory=GroqConfig)

    @classmethod
    def load(cls, path: Path | str) -> AppConfig:
        p = Path(path)
        raw: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8"))
        base = p.parent.resolve()

        paths = raw.get("paths", {})
        resolved_paths = {
            k: (base / v).resolve() if not Path(v).is_absolute() else Path(v).resolve()
            for k, v in paths.items()
        }
        raw["paths"] = resolved_paths
        return cls.model_validate(raw)
