from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.filter import (
    FilterEmptyReason,
    filter_restaurants,
    filter_restaurants_with_config,
    normalize_city_name,
)
from restaurant_rec.phase2.preferences import UserPreferences


@pytest.fixture
def tiny_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "1",
                "name": "A",
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
                "name": "B",
                "city": "Delhi",
                "locality": "CP",
                "cuisines": ["Italian"],
                "rating": 3.5,
                "cost_for_two": 1500,
                "budget_tier": "high",
                "votes": 50,
                "address": None,
                "url": None,
                "raw_features": None,
            },
            {
                "id": "3",
                "name": "C",
                "city": "Mumbai",
                "locality": "Bandra",
                "cuisines": ["Chinese"],
                "rating": 4.8,
                "cost_for_two": 400,
                "budget_tier": "low",
                "votes": 200,
                "address": None,
                "url": None,
                "raw_features": None,
            },
        ]
    )


def test_normalize_city_name_alias() -> None:
    aliases = {"bengaluru": "Bangalore"}
    assert normalize_city_name("Bengaluru", aliases) == "Bangalore"


def test_no_location(tiny_catalog: pd.DataFrame) -> None:
    p = UserPreferences(location="Goa", budget_max_inr=2000, cuisine="Chinese", min_rating=3.0)
    r = filter_restaurants(tiny_catalog, p)
    assert r.reason == FilterEmptyReason.NO_LOCATION
    assert r.items == []


def test_no_cuisine(tiny_catalog: pd.DataFrame) -> None:
    p = UserPreferences(location="Delhi", budget_max_inr=2000, cuisine="Mexican", min_rating=3.0)
    r = filter_restaurants(tiny_catalog, p)
    assert r.reason == FilterEmptyReason.NO_CUISINE


def test_no_rating() -> None:
    df = pd.DataFrame(
        [
            {
                "id": "4",
                "name": "D",
                "city": "Delhi",
                "locality": "CP",
                "cuisines": ["Thai"],
                "rating": None,
                "cost_for_two": 600,
                "budget_tier": "medium",
                "votes": 1,
                "address": None,
                "url": None,
                "raw_features": None,
            },
        ]
    )
    p = UserPreferences(location="Delhi", budget_max_inr=2000, cuisine="Thai", min_rating=4.0)
    r = filter_restaurants(df, p)
    assert r.reason == FilterEmptyReason.NO_RATING


def test_no_budget(tiny_catalog: pd.DataFrame) -> None:
    """North Indian only at A with cost 800; cap 600 excludes it."""
    p = UserPreferences(location="Delhi", budget_max_inr=600, cuisine="North Indian", min_rating=3.0)
    r = filter_restaurants(tiny_catalog, p)
    assert r.reason == FilterEmptyReason.NO_BUDGET


def test_happy_path_sorted(tiny_catalog: pd.DataFrame) -> None:
    p = UserPreferences(
        location="Delhi",
        budget_max_inr=1000,
        cuisine="Indian",
        min_rating=3.0,
    )
    r = filter_restaurants(tiny_catalog, p, shortlist_limit=10)
    assert r.reason == FilterEmptyReason.OK
    assert len(r.items) == 1
    assert r.items[0]["name"] == "A"


def test_skip_cuisine_filter_when_omitted(tiny_catalog: pd.DataFrame) -> None:
    p = UserPreferences(location="Mumbai", budget_max_inr=500, cuisine=None, min_rating=0.0)
    r = filter_restaurants(tiny_catalog, p)
    assert r.reason == FilterEmptyReason.OK
    assert r.items[0]["name"] == "C"


def test_locality_match_not_only_city(tiny_catalog: pd.DataFrame) -> None:
    p = UserPreferences(location="Bandra", budget_max_inr=500, cuisine=None, min_rating=0.0)
    r = filter_restaurants(tiny_catalog, p)
    assert r.reason == FilterEmptyReason.OK
    assert r.items[0]["name"] == "C"


def test_sort_by_rating_then_votes() -> None:
    df = pd.DataFrame(
        [
            {
                "id": "a",
                "name": "LowVotes",
                "city": "X",
                "locality": "L",
                "cuisines": ["Cafe"],
                "rating": 4.5,
                "cost_for_two": 300,
                "budget_tier": "low",
                "votes": 10,
                "address": None,
                "url": None,
                "raw_features": None,
            },
            {
                "id": "b",
                "name": "HighVotes",
                "city": "X",
                "locality": "L",
                "cuisines": ["Cafe"],
                "rating": 4.5,
                "cost_for_two": 300,
                "budget_tier": "low",
                "votes": 999,
                "address": None,
                "url": None,
                "raw_features": None,
            },
        ]
    )
    p = UserPreferences(location="X", budget_max_inr=500, cuisine="Cafe", min_rating=0.0)
    r = filter_restaurants(df, p, shortlist_limit=5)
    assert [x["name"] for x in r.items] == ["HighVotes", "LowVotes"]


def test_filter_with_config_uses_aliases(tiny_catalog: pd.DataFrame, tmp_path: Path) -> None:
    df = tiny_catalog.copy()
    df.loc[0, "city"] = "Bangalore"
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
dataset:
  id: x
  split: train
paths:
  raw_snapshot: raw.parquet
  processed_catalog: out.parquet
  ingest_report: rep.json
city_aliases:
  bengaluru: Bangalore
filter:
  rating_relax_delta: 0.5
  min_candidates_for_relax: 5
  max_shortlist_candidates: 40
groq:
  model: llama-3.3-70b-versatile
  top_k_recommendations: 5
""",
        encoding="utf-8",
    )
    cfg = AppConfig.load(cfg_path)
    p = UserPreferences(location="Bengaluru", budget_max_inr=1000, cuisine="Indian", min_rating=3.0)
    r = filter_restaurants_with_config(df, p, cfg)
    assert r.reason == FilterEmptyReason.OK
    assert r.items[0]["name"] == "A"


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[1].joinpath("data/processed/restaurants.parquet").is_file(),
    reason="processed catalog not built (run scripts/ingest_zomato.py)",
)
def test_real_catalog_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    df = pd.read_parquet(root / "data/processed/restaurants.parquet")
    p = UserPreferences(
        location="Bangalore",
        budget_max_inr=1200,
        cuisine="Chinese",
        min_rating=4.0,
    )
    r = filter_restaurants(
        df,
        p,
        city_aliases={"bengaluru": "Bangalore"},
        shortlist_limit=20,
    )
    assert r.reason == FilterEmptyReason.OK
    assert 1 <= len(r.items) <= 20
    assert all(x["rating"] is not None and x["rating"] >= 4.0 for x in r.items)
    assert all(x["cost_for_two"] is not None and x["cost_for_two"] <= 1200 for x in r.items)
