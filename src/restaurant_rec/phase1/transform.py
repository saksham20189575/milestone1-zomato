from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import pandas as pd

from restaurant_rec.config import AppConfig

_URL_CITY_RE = re.compile(r"zomato\.com/([^/?#]+)", re.IGNORECASE)
_RATE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*5\s*$", re.IGNORECASE)
_NON_DIGITS_RE = re.compile(r"[^\d]")


def _title_city(token: str) -> str:
    t = token.replace("_", "-").strip()
    if not t:
        return ""
    return " ".join(part.capitalize() for part in t.split("-"))


def _normalize_city_name(name: str, aliases: dict[str, str]) -> str:
    key = name.strip().lower()
    return aliases.get(key, name.strip().title())


def infer_city(url: str | None, address: str | None, aliases: dict[str, str]) -> str | None:
    """Infer metro `city` from Zomato URL path, URL token, or address tail."""
    url = url or ""
    address = address or ""

    m = _URL_CITY_RE.search(url)
    if m:
        raw_seg = m.group(1).strip()
        low = raw_seg.lower()
        # Short URLs often use a single venue slug (e.g. /ChurchStreetSocial), not /city/venue.
        # Never treat an arbitrary alphabetic token as a metro — only match known cities.
        spaced = low.replace("_", "-").replace("-", " ")
        if spaced in aliases:
            return aliases[spaced]
        if low in aliases:
            return aliases[low]
        canon_by_lower = {v.lower(): v for v in aliases.values()}
        if spaced in canon_by_lower:
            return canon_by_lower[spaced]
        if low in canon_by_lower:
            return canon_by_lower[low]

        # Embedded city in token, e.g. SanchurroBangalore
        for alias_key, canonical in aliases.items():
            if alias_key.replace(" ", "") in low.replace(" ", ""):
                return canonical
        # Heuristic: ...bangalore at end
        for alias_key, canonical in aliases.items():
            compact = alias_key.replace(" ", "")
            if len(compact) >= 5 and compact in low.replace("-", ""):
                return canonical

    # Address: walk segments from the end, match alias or known long tokens
    parts = [p.strip() for p in address.split(",") if p.strip()]
    for part in reversed(parts[-4:]):
        normalized = _normalize_city_name(part, aliases)
        if part.lower() in aliases or normalized != part.strip().title():
            return normalized
        if part.lower() in {
            "bangalore",
            "bengaluru",
            "mumbai",
            "delhi",
            "new delhi",
            "hyderabad",
            "chennai",
            "kolkata",
            "pune",
            "ahmedabad",
            "jaipur",
            "noida",
            "gurgaon",
            "gurugram",
            "goa",
        }:
            return _normalize_city_name(part, aliases)

    return None


def infer_primary_locality(row: dict[str, Any]) -> str:
    """
    Main area for the outlet (Phase 2 location filter / UI).

    Prefer Zomato `listed_in(city)` (listing zone, e.g. Banashankari); fall back to
    raw `location` (often a finer sub-area) when the listing field is empty.
    """
    for key in ("listed_in(city)", "location"):
        raw = row.get(key)
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        s = str(raw).strip()
        if s and s.lower() not in {"nan", "none"}:
            return s
    return ""


def parse_rate(raw: Any, min_v: float, max_v: float) -> tuple[float | None, str | None]:
    """Returns (rating, issue) where issue is 'unparsable' | 'out_of_range' | None."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None, None
    s = str(raw).strip()
    if not s or s in {"-", "nan", "None"}:
        return None, None
    low = s.lower()
    if low in {"new", "none", "null"}:
        return None, "unparsable"
    m = _RATE_RE.match(s)
    if not m:
        return None, "unparsable"
    val = float(m.group(1))
    if val < min_v or val > max_v:
        return None, "out_of_range"
    return val, None


def parse_cost(raw: Any) -> int | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    digits = _NON_DIGITS_RE.sub("", str(raw))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def budget_tier_for_cost(cost: int | None, cfg: AppConfig) -> str | None:
    if cost is None:
        return None
    t = cfg.budget_tiers_inr
    if cost < t.low_max:
        return "low"
    if cost >= t.high_min:
        return "high"
    return "medium"


def parse_cuisines(raw: Any) -> list[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    s = str(raw).strip()
    if not s:
        return []
    parts = re.split(r"\s*,\s*|\s*\|\s*", s)
    return [p.strip() for p in parts if p.strip()]


def build_raw_features(row: dict[str, Any]) -> str | None:
    payload = {
        "online_order": row.get("online_order"),
        "book_table": row.get("book_table"),
        "rest_type": row.get("rest_type"),
        "listed_in_type": row.get("listed_in(type)"),
        "listed_in_city": row.get("listed_in(city)"),
        "dish_liked": row.get("dish_liked"),
    }
    if all(v is None or (isinstance(v, float) and pd.isna(v)) or v == "" for v in payload.values()):
        return None
    # Compact JSON for prompt / UI later
    clean = {k: v for k, v in payload.items() if v is not None and not (isinstance(v, float) and pd.isna(v)) and v != ""}
    if not clean:
        return None
    return json.dumps(clean, ensure_ascii=False)


def hf_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def transform_raw_dataframe(df: pd.DataFrame, cfg: AppConfig) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply parsers and derived fields. Does not drop rows (validate step does)."""
    stats: dict[str, int] = {
        "rating_unparsable": 0,
        "rating_out_of_range": 0,
        "missing_city_inference": 0,
    }

    cities: list[str | None] = []
    localities: list[str] = []
    for _, row in df.iterrows():
        rowd = row.to_dict()
        c = infer_city(rowd.get("url"), rowd.get("address"), cfg.city_aliases)
        cities.append(c)
        localities.append(infer_primary_locality(rowd))
        if c is None:
            stats["missing_city_inference"] += 1

    out = pd.DataFrame(
        {
            "name": df["name"].astype(str).str.strip(),
            "locality": localities,
            "city": cities,
            "cuisines": [parse_cuisines(x) for x in df.get("cuisines", [])],
            "votes": pd.to_numeric(df.get("votes"), errors="coerce").astype("Int64"),
            "address": df.get("address"),
            "url": df.get("url"),
        }
    )

    ratings: list[float | None] = []
    r_min, r_max = cfg.rating.min_valid, cfg.rating.max_valid
    for raw in df.get("rate", []):
        val, issue = parse_rate(raw, r_min, r_max)
        if issue == "unparsable":
            stats["rating_unparsable"] += 1
        elif issue == "out_of_range":
            stats["rating_out_of_range"] += 1
        ratings.append(val)
    out["rating"] = ratings

    cost_col = "approx_cost(for two people)"
    costs = [parse_cost(x) for x in df.get(cost_col, [])] if cost_col in df.columns else [None] * len(df)
    out["cost_for_two"] = costs
    out["budget_tier"] = [budget_tier_for_cost(c, cfg) for c in costs]

    raw_features_col: list[str | None] = []
    for _, row in df.iterrows():
        raw_features_col.append(build_raw_features(row.to_dict()))
    out["raw_features"] = raw_features_col

    def stable_id(row: pd.Series) -> str:
        key = f"{row.get('url', '')}|{row.get('name', '')}|{row.get('address', '')}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    out["id"] = [stable_id(df.iloc[i]) for i in range(len(df))]

    return out, stats
