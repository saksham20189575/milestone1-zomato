from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.filter import FilterEmptyReason
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase3.orchestrate import recommend
from restaurant_rec.phase3.parse import extract_json_object, parse_and_validate_llm_payload


def test_extract_json_raw() -> None:
    d = extract_json_object('  {"summary": "x", "recommendations": []}  ')
    assert d == {"summary": "x", "recommendations": []}


def test_extract_json_fenced() -> None:
    text = 'Here:\n```json\n{"summary": "s", "recommendations": [{"restaurant_id": "a", "rank": 1, "explanation": "e"}]}\n```'
    d = extract_json_object(text)
    assert d["summary"] == "s"
    assert len(d["recommendations"]) == 1


def test_parse_and_validate_filters_unknown_ids() -> None:
    text = json.dumps(
        {
            "summary": "ok",
            "recommendations": [
                {"restaurant_id": "good", "rank": 1, "explanation": "x"},
                {"restaurant_id": "bad", "rank": 2, "explanation": "y"},
            ],
        }
    )
    p = parse_and_validate_llm_payload(text, allowed_ids={"good"})
    assert p is not None
    assert len(p.recommendations) == 1
    assert p.recommendations[0].restaurant_id == "good"


def test_parse_empty_recommendations_returns_none() -> None:
    text = json.dumps({"summary": "x", "recommendations": []})
    assert parse_and_validate_llm_payload(text, allowed_ids={"a"}) is None


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def app_cfg(repo_root: Path) -> AppConfig:
    return AppConfig.load(repo_root / "config.yaml")


def tiny_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "r1",
                "name": "Test Cafe",
                "city": "TestCity",
                "locality": "T1",
                "cuisines": ["Cafe"],
                "rating": 4.5,
                "cost_for_two": 400,
                "budget_tier": "low",
                "votes": 10,
                "address": None,
                "url": None,
                "raw_features": None,
            },
            {
                "id": "r2",
                "name": "Other",
                "city": "TestCity",
                "locality": "T1",
                "cuisines": ["Cafe"],
                "rating": 4.0,
                "cost_for_two": 500,
                "budget_tier": "low",
                "votes": 5,
                "address": None,
                "url": None,
                "raw_features": None,
            },
        ]
    )


def test_recommend_empty_filter_no_llm(app_cfg: AppConfig, repo_root: Path) -> None:
    df = tiny_catalog()
    prefs = UserPreferences(
        location="NowhereCity",
        budget_max_inr=2000,
        cuisine="Cafe",
        min_rating=4.0,
    )
    out = recommend(df, prefs, app_cfg, config_path=repo_root / "config.yaml")
    assert out.items == []
    assert out.meta.filter_reason == FilterEmptyReason.NO_LOCATION.value
    assert out.meta.used_llm is False


def test_recommend_mock_groq_merges_facts(app_cfg: AppConfig, repo_root: Path) -> None:
    df = tiny_catalog()
    prefs = UserPreferences(
        location="TestCity",
        budget_max_inr=600,
        cuisine="Cafe",
        min_rating=4.0,
    )
    llm_out = json.dumps(
        {
            "summary": "Great cafes.",
            "recommendations": [
                {"restaurant_id": "r2", "rank": 1, "explanation": "Solid choice for budget."},
                {"restaurant_id": "r1", "rank": 2, "explanation": "Higher rating."},
            ],
        }
    )
    with patch("restaurant_rec.phase3.orchestrate.complete_chat", return_value=llm_out):
        out = recommend(df, prefs, app_cfg, config_path=repo_root / "config.yaml")
    assert out.meta.used_llm is True
    assert out.meta.llm_parse_failed is False
    assert out.summary == "Great cafes."
    assert len(out.items) == 2
    assert out.items[0]["id"] == "r2"
    assert out.items[0]["name"] == "Other"
    assert out.items[0]["cost_display"].startswith("₹")
    assert "Solid" in out.items[0]["explanation"]


def test_recommend_parse_fail_falls_back(app_cfg: AppConfig, repo_root: Path) -> None:
    df = tiny_catalog()
    prefs = UserPreferences(
        location="TestCity",
        budget_max_inr=600,
        cuisine="Cafe",
        min_rating=4.0,
    )
    with patch(
        "restaurant_rec.phase3.orchestrate.complete_chat",
        return_value="not json at all",
    ):
        out = recommend(df, prefs, app_cfg, config_path=repo_root / "config.yaml")
    assert out.meta.used_llm is True
    assert out.meta.llm_parse_failed is True
    assert len(out.items) >= 1
    assert "fallback" in out.items[0]["explanation"].lower()
