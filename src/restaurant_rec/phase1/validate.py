from __future__ import annotations

import pandas as pd


def validate_catalog(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Drop rows that cannot satisfy Phase 2 location filters.
    Returns cleaned frame and drop counts.
    """
    before = len(df)
    reasons: dict[str, int] = {
        "dropped_missing_name": 0,
        "dropped_missing_city": 0,
    }

    name_ok = df["name"].astype(str).str.strip() != ""
    reasons["dropped_missing_name"] = int((~name_ok).sum())

    city_series = df["city"]
    city_ok = city_series.notna() & (city_series.astype(str).str.strip() != "")
    reasons["dropped_missing_city"] = int((name_ok & ~city_ok).sum())

    mask = name_ok & city_ok
    cleaned = df.loc[mask].reset_index(drop=True)
    reasons["rows_before"] = before
    reasons["rows_after"] = len(cleaned)
    reasons["rows_dropped_total"] = before - len(cleaned)
    return cleaned, reasons
