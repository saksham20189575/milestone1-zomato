from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from restaurant_rec.phase2.cities import distinct_cities
from restaurant_rec.phase2.localities import distinct_localities
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase3.orchestrate import recommend
from restaurant_rec.phase4.schemas import (
    LocalitiesResponse,
    LocationsResponse,
    RecommendResponse,
    result_to_response,
)

if TYPE_CHECKING:
    import pandas as pd

    from restaurant_rec.config import AppConfig


def project_root() -> Path:
    """`m1/` repo root when installed as `src/restaurant_rec/phase4/app.py`."""
    return Path(__file__).resolve().parents[3]


@asynccontextmanager
async def default_lifespan(app: FastAPI):
    from restaurant_rec.config import AppConfig
    from restaurant_rec.phase2.catalog_loader import load_catalog
    from restaurant_rec.phase3.env_util import load_project_dotenv

    root = project_root()
    cfg_path = root / "config.yaml"
    load_project_dotenv(cfg_path)
    cfg = AppConfig.load(cfg_path)
    catalog = load_catalog(cfg.paths.processed_catalog)
    app.state.config = cfg
    app.state.catalog = catalog
    app.state.config_path = cfg_path
    yield


def mount_routes(app: FastAPI) -> None:
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/locations", response_model=LocationsResponse)
    async def list_locations(request: Request) -> LocationsResponse:
        catalog = request.app.state.catalog
        return LocationsResponse(locations=distinct_cities(catalog))

    @app.get("/api/v1/localities", response_model=LocalitiesResponse)
    async def list_localities(request: Request) -> LocalitiesResponse:
        catalog = request.app.state.catalog
        return LocalitiesResponse(localities=distinct_localities(catalog))

    @app.post("/api/v1/recommend", response_model=RecommendResponse)
    async def recommend_endpoint(body: UserPreferences, request: Request) -> RecommendResponse:
        cfg = request.app.state.config
        catalog = request.app.state.catalog
        config_path = getattr(request.app.state, "config_path", None)
        raw = recommend(catalog, body, cfg, config_path=config_path)
        return result_to_response(raw)


def mount_static_ui(app: FastAPI) -> None:
    """Serve `web/` at `/` and `/static/*` for end-to-end browser testing."""
    web_dir = project_root() / "web"
    if not web_dir.is_dir():
        return

    @app.get("/")
    async def index_page() -> FileResponse:
        return FileResponse(web_dir / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


def create_app(*, lifespan: Any = None) -> FastAPI:
    """
    Create FastAPI app. Default lifespan loads `config.yaml` and catalog from `project_root()`.

    For tests, pass a custom asynccontextmanager lifespan that sets
    `app.state.config`, `app.state.catalog`, and optionally `app.state.config_path`.
    """
    if lifespan is None:
        lifespan = default_lifespan

    app = FastAPI(title="Restaurant Recommendation API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_routes(app)
    mount_static_ui(app)
    return app


# Uvicorn: `uvicorn restaurant_rec.phase4.app:app --app-dir src` or `pip install -e .` then same without --app-dir
app = create_app()


def make_test_lifespan(
    cfg: "AppConfig",
    catalog: "pd.DataFrame",
    config_path: Path | None = None,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.config = cfg
        app.state.catalog = catalog
        app.state.config_path = config_path
        yield

    return lifespan
