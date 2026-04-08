"""
Live Groq integration tests (real API). Run with:

  pytest tests/test_phase3_live_groq.py -v -s

Requires `GROQ_API_KEY` in `.env` and `data/processed/restaurants.parquet`.
At most a few cases to avoid cost/rate limits.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from dotenv import load_dotenv

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase3 import recommend

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CATALOG = ROOT / "data" / "processed" / "restaurants.parquet"
CONFIG = ROOT / "config.yaml"

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set (add to .env)",
)


@pytest.fixture(scope="module")
def app_cfg() -> AppConfig:
    return AppConfig.load(CONFIG)


@pytest.fixture(scope="module")
def catalog_df() -> pd.DataFrame:
    if not CATALOG.is_file():
        pytest.skip(f"Catalog missing: {CATALOG} (run scripts/ingest_zomato.py)")
    return pd.read_parquet(CATALOG)


def _assert_sane_llm_result(result, *, min_items: int = 1) -> None:
    assert result.meta.used_llm is True, "Groq should have been called for non-empty shortlist"
    assert result.meta.llm_parse_failed is False, "Expected valid JSON from model"
    assert len(result.items) >= min_items
    for it in result.items:
        assert it.get("name")
        assert it.get("explanation") and len(str(it["explanation"])) >= 20
        assert it.get("rating") is not None
        assert it.get("cost_display")


def test_live_groq_bangalore_chinese_medium(catalog_df: pd.DataFrame, app_cfg: AppConfig) -> None:
    """Popular filter in this dataset — should return ranked picks with explanations."""
    prefs = UserPreferences(
        location="Bangalore",
        budget_max_inr=1200,
        cuisine="Chinese",
        min_rating=4.0,
    )
    result = recommend(catalog_df, prefs, app_cfg, config_path=CONFIG)
    print("\n--- test_live_groq_bangalore_chinese_medium ---")
    print("summary:", result.summary[:300], "..." if len(result.summary) > 300 else "")
    for it in result.items[:3]:
        print(f"  #{it['rank']} {it['name']} | {it['rating']} | {it['explanation'][:120]}...")
    _assert_sane_llm_result(result, min_items=1)


def test_live_groq_bangalore_north_indian_low(catalog_df: pd.DataFrame, app_cfg: AppConfig) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget_max_inr=900,
        cuisine="North Indian",
        min_rating=3.5,
    )
    result = recommend(catalog_df, prefs, app_cfg, config_path=CONFIG)
    print("\n--- test_live_groq_bangalore_north_indian_low ---")
    print("summary:", result.summary[:280])
    _assert_sane_llm_result(result, min_items=1)


def test_live_groq_bangalore_cafe_broader(catalog_df: pd.DataFrame, app_cfg: AppConfig) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget_max_inr=1200,
        cuisine="Cafe",
        min_rating=3.8,
    )
    result = recommend(catalog_df, prefs, app_cfg, config_path=CONFIG)
    print("\n--- test_live_groq_bangalore_cafe_broader ---")
    print("summary:", result.summary[:280])
    _assert_sane_llm_result(result, min_items=1)
