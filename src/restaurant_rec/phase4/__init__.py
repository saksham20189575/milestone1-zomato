"""Phase 4: HTTP API and static UI."""

from restaurant_rec.phase4.app import app, create_app, default_lifespan, make_test_lifespan, mount_routes, project_root
from restaurant_rec.phase4.schemas import (
    LocationsResponse,
    RecommendItemOut,
    RecommendMetaOut,
    RecommendResponse,
    result_to_response,
)

__all__ = [
    "LocationsResponse",
    "RecommendItemOut",
    "RecommendMetaOut",
    "RecommendResponse",
    "app",
    "create_app",
    "default_lifespan",
    "make_test_lifespan",
    "mount_routes",
    "project_root",
    "result_to_response",
]
