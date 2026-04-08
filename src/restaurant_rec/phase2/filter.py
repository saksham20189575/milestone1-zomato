from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.preferences import UserPreferences


class FilterEmptyReason(str, Enum):
    OK = "OK"
    NO_LOCATION = "NO_LOCATION"
    NO_CUISINE = "NO_CUISINE"
    NO_RATING = "NO_RATING"
    NO_BUDGET = "NO_BUDGET"


@dataclass
class FilterResult:
    """Deterministic shortlist + diagnostics for UI / Phase 3."""

    items: list[dict[str, Any]]
    reason: FilterEmptyReason
    stage_counts: dict[str, int] = field(default_factory=dict)
    rating_relaxed: bool = False
    effective_min_rating: float | None = None


def _normalize_key(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return " ".join(str(s).lower().split())


def normalize_city_name(name: object, aliases: dict[str, str]) -> str:
    """Map user/catalog text to canonical city using lowercase alias keys."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    raw = str(name).strip()
    if not raw:
        return ""
    key = _normalize_key(raw)
    return aliases.get(key, raw.title())


def _location_mask(df: pd.DataFrame, user_location: str, aliases: dict[str, str]) -> pd.Series:
    target = normalize_city_name(user_location, aliases)
    t_lower = target.lower()
    city_match = df["city"].astype(str).str.strip().str.lower() == t_lower
    loc_match = df["locality"].astype(str).str.strip().str.lower() == _normalize_key(user_location)
    # Also try normalized locality against target
    loc_norm = df["locality"].astype(str).map(lambda x: normalize_city_name(x, aliases).lower())
    loc_match = loc_match | (loc_norm == t_lower)
    city_norm = df["city"].astype(str).map(lambda x: normalize_city_name(x, aliases).lower())
    city_match = city_match | (city_norm == t_lower)
    return city_match | loc_match


def _cuisine_mask(df: pd.DataFrame, terms: list[str]) -> pd.Series:
    if not terms:
        return pd.Series(True, index=df.index)

    def row_matches(cells: object) -> bool:
        if cells is None or (isinstance(cells, float) and pd.isna(cells)):
            return False
        if hasattr(cells, "tolist"):
            cuisines = [str(x) for x in cells.tolist()]
        elif isinstance(cells, (list, tuple)):
            cuisines = [str(x) for x in cells]
        else:
            cuisines = [str(cells)]
        cl = [c.lower() for c in cuisines]
        for u in terms:
            ul = u.lower()
            for r in cl:
                if ul in r or r in ul:
                    return True
        return False

    return df["cuisines"].map(row_matches)


def _rating_mask(df: pd.DataFrame, min_rating: float) -> pd.Series:
    r = df["rating"]
    ok = r.notna() & (r.astype(float) >= min_rating)
    return ok


def _budget_numeric_mask(df: pd.DataFrame, budget_max_inr: int) -> pd.Series:
    """Keep rows where `cost_for_two` is known and at most `budget_max_inr` (INR for two)."""
    c = pd.to_numeric(df["cost_for_two"], errors="coerce")
    return c.notna() & (c <= float(budget_max_inr))


def _run_stages(
    df: pd.DataFrame,
    prefs: UserPreferences,
    min_rating: float,
    *,
    city_aliases: dict[str, str],
) -> tuple[pd.DataFrame, FilterEmptyReason, dict[str, int]]:
    stages: dict[str, int] = {"input_rows": len(df)}

    work = df.loc[_location_mask(df, prefs.location, city_aliases)].copy()
    stages["after_location"] = len(work)
    if len(work) == 0:
        return work, FilterEmptyReason.NO_LOCATION, stages

    terms = prefs.cuisine_terms()
    if terms:
        work = work.loc[_cuisine_mask(work, terms)].copy()
    stages["after_cuisine"] = len(work)
    if len(work) == 0:
        return work, FilterEmptyReason.NO_CUISINE, stages

    work = work.loc[_rating_mask(work, min_rating)].copy()
    stages["after_rating"] = len(work)
    if len(work) == 0:
        return work, FilterEmptyReason.NO_RATING, stages

    work = work.loc[_budget_numeric_mask(work, prefs.budget_max_inr)].copy()
    stages["after_budget"] = len(work)
    if len(work) == 0:
        return work, FilterEmptyReason.NO_BUDGET, stages

    return work, FilterEmptyReason.OK, stages


def _sort_and_limit(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    votes = df["votes"]
    vnum = pd.to_numeric(votes, errors="coerce")
    work = df.assign(_votes_sort=vnum.fillna(-1))
    work = work.sort_values(
        by=["rating", "_votes_sort"],
        ascending=[False, False],
        na_position="last",
    )
    work = work.drop(columns=["_votes_sort"])
    return work.head(limit)


def _rows_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        d = row.to_dict()
        c = d.get("cuisines")
        if hasattr(c, "tolist"):
            d["cuisines"] = list(c.tolist())
        elif isinstance(c, (list, tuple)):
            d["cuisines"] = list(c)
        elif c is None or (isinstance(c, float) and pd.isna(c)):
            d["cuisines"] = []
        else:
            d["cuisines"] = [c]
        for k, v in list(d.items()):
            if v is pd.NA or (isinstance(v, float) and pd.isna(v)):
                d[k] = None
            elif hasattr(v, "item") and callable(getattr(v, "item", None)):
                try:
                    d[k] = v.item()
                except (ValueError, AttributeError):
                    pass
        records.append(d)
    return records


def filter_restaurants(
    catalog: pd.DataFrame,
    preferences: UserPreferences,
    *,
    city_aliases: dict[str, str] | None = None,
    rating_relax_delta: float = 0.5,
    min_candidates_for_relax: int = 5,
    shortlist_limit: int = 40,
) -> FilterResult:
    """
    Apply Phase 2 pipeline: location → cuisine (optional) → rating → budget → sort → top N.

    Rows with null `rating` fail the rating filter. Rows with null `cost_for_two` fail the budget filter.

    If `preferences.enable_rating_relax` and either (a) fewer than `min_candidates_for_relax` rows
    remain after all stages with OK, or (b) the run ends with `NO_RATING`, reruns once with
    ``min_rating - rating_relax_delta`` (floored at 0) when that improves results.
    """
    aliases = city_aliases or {}
    eff_min = float(preferences.min_rating)

    work, reason, stages = _run_stages(catalog, preferences, eff_min, city_aliases=aliases)
    relaxed = False

    sparse_ok = reason == FilterEmptyReason.OK and len(work) < min_candidates_for_relax
    should_try_relax = (
        preferences.enable_rating_relax
        and eff_min > 0
        and (sparse_ok or reason == FilterEmptyReason.NO_RATING)
    )
    if should_try_relax:
        new_min = max(0.0, eff_min - rating_relax_delta)
        if new_min < eff_min:
            work2, reason2, stages2 = _run_stages(catalog, preferences, new_min, city_aliases=aliases)
            if len(work2) > len(work) or (
                reason != FilterEmptyReason.OK and reason2 == FilterEmptyReason.OK
            ):
                work, reason, stages = work2, reason2, stages2
                relaxed = True
                eff_min = new_min

    if reason != FilterEmptyReason.OK:
        return FilterResult(
            items=[],
            reason=reason,
            stage_counts=stages,
            rating_relaxed=relaxed,
            effective_min_rating=eff_min,
        )

    limited = _sort_and_limit(work, shortlist_limit)
    stages["shortlist_returned"] = len(limited)
    return FilterResult(
        items=_rows_to_records(limited),
        reason=FilterEmptyReason.OK,
        stage_counts=stages,
        rating_relaxed=relaxed,
        effective_min_rating=eff_min,
    )


def filter_restaurants_with_config(
    catalog: pd.DataFrame,
    preferences: UserPreferences,
    cfg: AppConfig,
) -> FilterResult:
    """Same as `filter_restaurants` using `city_aliases` and `filter.*` from config."""
    fc = cfg.filter
    return filter_restaurants(
        catalog,
        preferences,
        city_aliases=cfg.city_aliases,
        rating_relax_delta=fc.rating_relax_delta,
        min_candidates_for_relax=fc.min_candidates_for_relax,
        shortlist_limit=fc.max_shortlist_candidates,
    )
