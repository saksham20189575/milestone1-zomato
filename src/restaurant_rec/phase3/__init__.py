"""Phase 3: Groq LLM prompts, parsing, and recommend orchestration."""

from dataclasses import asdict

from restaurant_rec.phase3.models import LlmRecommendationItem, LlmRecommendationsPayload
from restaurant_rec.phase3.orchestrate import (
    RecommendationMeta,
    RecommendationResult,
    recommend,
)
from restaurant_rec.phase3.parse import extract_json_object, parse_and_validate_llm_payload
from restaurant_rec.phase3.prompts import PROMPT_VERSION, build_messages

__all__ = [
    "LlmRecommendationItem",
    "LlmRecommendationsPayload",
    "PROMPT_VERSION",
    "RecommendationMeta",
    "RecommendationResult",
    "build_messages",
    "extract_json_object",
    "parse_and_validate_llm_payload",
    "recommend",
    "recommendation_result_as_dict",
]


def recommendation_result_as_dict(result: RecommendationResult) -> dict:
    """JSON-serializable shape for APIs (Phase 4)."""
    return {
        "summary": result.summary,
        "items": result.items,
        "meta": asdict(result.meta),
    }
