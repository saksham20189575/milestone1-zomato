"""Phase 2: user preferences, catalog loading, deterministic shortlist."""

from restaurant_rec.phase2.catalog_loader import load_catalog, load_catalog_from_config
from restaurant_rec.phase2.cities import distinct_cities
from restaurant_rec.phase2.localities import distinct_localities
from restaurant_rec.phase2.filter import (
    FilterEmptyReason,
    FilterResult,
    filter_restaurants,
    filter_restaurants_with_config,
    normalize_city_name,
)
from restaurant_rec.phase2.preferences import UserPreferences

__all__ = [
    "FilterEmptyReason",
    "FilterResult",
    "UserPreferences",
    "distinct_cities",
    "distinct_localities",
    "filter_restaurants",
    "filter_restaurants_with_config",
    "load_catalog",
    "load_catalog_from_config",
    "normalize_city_name",
]
