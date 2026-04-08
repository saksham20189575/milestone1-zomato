"""City inference from Zomato URLs and addresses (Phase 1 transform)."""

from __future__ import annotations

from pathlib import Path

import pytest

from restaurant_rec.config import AppConfig
from restaurant_rec.phase1.transform import infer_city, infer_primary_locality


@pytest.fixture
def cfg() -> AppConfig:
    return AppConfig.load(Path(__file__).resolve().parents[1] / "config.yaml")


def test_infer_city_venue_slug_url_uses_address(cfg: AppConfig) -> None:
    """Short /VenueName URLs must not become the metro; address wins."""
    url = "https://www.zomato.com/ChurchStreetSocial?context=abc"
    address = "46/1, Cobalt Building, Church Street, Bangalore"
    assert infer_city(url, address, cfg.city_aliases) == "Bangalore"


def test_infer_city_classic_city_path(cfg: AppConfig) -> None:
    assert (
        infer_city(
            "https://www.zomato.com/bangalore/some-restaurant",
            "",
            cfg.city_aliases,
        )
        == "Bangalore"
    )


def test_infer_city_embedded_metro_in_slug(cfg: AppConfig) -> None:
    assert (
        infer_city("https://www.zomato.com/SanchurroBangalore", "", cfg.city_aliases)
        == "Bangalore"
    )


def test_infer_city_hyphenated_metro_slug(cfg: AppConfig) -> None:
    assert (
        infer_city("https://www.zomato.com/new-delhi/foo", "", cfg.city_aliases)
        == "Delhi"
    )


def test_infer_primary_locality_prefers_listed_in_city() -> None:
    row = {
        "location": "Basavanagudi",
        "listed_in(city)": "Banashankari",
    }
    assert infer_primary_locality(row) == "Banashankari"


def test_infer_primary_locality_falls_back_to_location() -> None:
    row = {"location": "Koramangala 5th Block", "listed_in(city)": ""}
    assert infer_primary_locality(row) == "Koramangala 5th Block"


def test_infer_primary_locality_missing_listed_in_key() -> None:
    assert infer_primary_locality({"location": "Indiranagar"}) == "Indiranagar"
