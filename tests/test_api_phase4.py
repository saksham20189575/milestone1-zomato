from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from restaurant_rec.config import AppConfig
from restaurant_rec.phase4.app import create_app, make_test_lifespan


def _write_config(tmp_path: Path, catalog_filename: str = "catalog.parquet") -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
dataset:
  id: placeholder
  split: train
paths:
  raw_snapshot: raw.parquet
  processed_catalog: {catalog_filename}
  ingest_report: ingest.json
filter:
  rating_relax_delta: 0.5
  min_candidates_for_relax: 5
  max_shortlist_candidates: 40
groq:
  model: llama-3.3-70b-versatile
  top_k_recommendations: 3
""",
        encoding="utf-8",
    )
    return cfg


@pytest.fixture
def sample_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "1",
                "name": "Alpha",
                "city": "Delhi",
                "locality": "CP",
                "cuisines": ["North Indian", "Chinese"],
                "rating": 4.2,
                "cost_for_two": 800,
                "budget_tier": "medium",
                "votes": 100,
                "address": None,
                "url": None,
                "raw_features": None,
            },
            {
                "id": "2",
                "name": "Beta",
                "city": "Delhi",
                "locality": "CP",
                "cuisines": ["Italian"],
                "rating": 3.8,
                "cost_for_two": 600,
                "budget_tier": "medium",
                "votes": 50,
                "address": None,
                "url": None,
                "raw_features": None,
            },
        ]
    )


@pytest.fixture
def test_client(tmp_path: Path, sample_catalog: pd.DataFrame):
    sample_catalog.to_parquet(tmp_path / "catalog.parquet")
    cfg_path = _write_config(tmp_path)
    cfg = AppConfig.load(cfg_path)
    app = create_app(lifespan=make_test_lifespan(cfg, sample_catalog, cfg_path))
    with TestClient(app) as client:
        yield client


def test_recommend_validation_422_missing_budget_max(test_client: TestClient) -> None:
    r = test_client.post("/api/v1/recommend", json={"location": "Delhi", "min_rating": 4.0})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body


def test_recommend_no_matches_returns_200_empty_items(test_client: TestClient) -> None:
    """Bangalore not in tiny catalog → filter NO_LOCATION, no LLM."""
    body = {
        "location": "Bangalore",
        "budget_max_inr": 5000,
        "cuisine": "Chinese",
        "min_rating": 4.0,
    }
    r = test_client.post("/api/v1/recommend", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "No restaurants matched" in data["summary"] or "location" in data["summary"].lower()
    assert data["meta"]["filter_reason"] == "NO_LOCATION"
    assert data["meta"]["used_llm"] is False


def test_recommend_success_with_mocked_groq(test_client: TestClient) -> None:
    llm_json = json.dumps(
        {
            "summary": "Nice picks in Delhi.",
            "recommendations": [
                {"restaurant_id": "2", "rank": 1, "explanation": "Italian focus and solid value for medium budget."},
                {"restaurant_id": "1", "rank": 2, "explanation": "Strong North Indian and Chinese with high rating."},
            ],
        }
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GROQ_API_KEY", "test-key-for-mock")
        from unittest.mock import patch

        with patch("restaurant_rec.phase3.orchestrate.complete_chat", return_value=llm_json):
            # Omit cuisine so both Delhi / medium rows enter the shortlist (Indian would only match North Indian).
            r = test_client.post(
                "/api/v1/recommend",
                json={
                    "location": "Delhi",
                    "budget_max_inr": 2000,
                    "min_rating": 3.5,
                },
            )
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["used_llm"] is True
    assert data["meta"]["llm_parse_failed"] is False
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "2"
    assert data["items"][0]["name"] == "Beta"
    assert "Italian" in data["items"][0]["explanation"]
    assert data["summary"] == "Nice picks in Delhi."


def test_locations_endpoint(test_client: TestClient) -> None:
    r = test_client.get("/api/v1/locations")
    assert r.status_code == 200
    data = r.json()
    assert data["locations"] == ["Delhi"]


def test_localities_endpoint(test_client: TestClient) -> None:
    r = test_client.get("/api/v1/localities")
    assert r.status_code == 200
    data = r.json()
    assert data["localities"] == ["CP"]


def test_index_page_served(test_client: TestClient) -> None:
    r = test_client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Restaurant recommendations" in r.content
    assert b"Select a locality" in r.content


def test_static_css_served(test_client: TestClient) -> None:
    r = test_client.get("/static/styles.css")
    assert r.status_code == 200
    assert b"--accent" in r.content
