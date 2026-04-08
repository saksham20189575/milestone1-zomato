"""Restaurant recommendation: Phases 1–3 (catalog, shortlist, Groq LLM)."""

from restaurant_rec.phase1 import (
    BudgetTier,
    RestaurantRecord,
    load_hf_dataframe,
    run_ingest,
)
from restaurant_rec.phase2 import (
    FilterEmptyReason,
    FilterResult,
    UserPreferences,
    filter_restaurants,
    filter_restaurants_with_config,
    load_catalog,
    load_catalog_from_config,
)
from restaurant_rec.phase3 import (
    RecommendationMeta,
    RecommendationResult,
    recommend,
    recommendation_result_as_dict,
)

__all__ = [
    "BudgetTier",
    "FilterEmptyReason",
    "FilterResult",
    "RecommendationMeta",
    "RecommendationResult",
    "RestaurantRecord",
    "UserPreferences",
    "filter_restaurants",
    "filter_restaurants_with_config",
    "load_catalog",
    "load_catalog_from_config",
    "load_hf_dataframe",
    "recommend",
    "recommendation_result_as_dict",
    "run_ingest",
]

__version__ = "0.1.0"
