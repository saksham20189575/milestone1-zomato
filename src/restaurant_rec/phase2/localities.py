from __future__ import annotations

import pandas as pd


def distinct_localities(catalog: pd.DataFrame) -> list[str]:
    """
    Unique `locality` values for UI dropdowns (non-empty).
    Case-insensitive deduplication keeps the first seen spelling.
    """
    seen: dict[str, str] = {}
    for raw in catalog["locality"].dropna().astype(str).str.strip():
        if not raw:
            continue
        key = raw.casefold()
        if key not in seen:
            seen[key] = raw
    return sorted(seen.values(), key=str.casefold)
