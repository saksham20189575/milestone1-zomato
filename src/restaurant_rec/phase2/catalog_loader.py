from __future__ import annotations

from pathlib import Path

import pandas as pd

from restaurant_rec.config import AppConfig

_EXPECTED_COLUMNS = frozenset({
    "id",
    "name",
    "city",
    "locality",
    "cuisines",
    "rating",
    "cost_for_two",
    "budget_tier",
    "votes",
    "address",
    "url",
    "raw_features",
})


def load_catalog(path: Path | str) -> pd.DataFrame:
    """Load Phase 1 processed Parquet into a DataFrame."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Catalog not found: {p}")
    df = pd.read_parquet(p)
    missing = _EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Catalog missing columns: {sorted(missing)}")
    return df


def load_catalog_from_config(cfg: AppConfig) -> pd.DataFrame:
    """Load catalog using `paths.processed_catalog` from AppConfig."""
    return load_catalog(cfg.paths.processed_catalog)
