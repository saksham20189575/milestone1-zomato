"""
Load `paths.processed_catalog` if present; otherwise run Phase 1 ingest once.

Streamlit Community Cloud (and similar) mount the repo read-only, so writes must go under
`tempfile.gettempdir()`; local dev can write to `data/processed/` when that tree is writable.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

from restaurant_rec.config import AppConfig
from restaurant_rec.phase1.ingest import run_ingest_with_config
from restaurant_rec.phase2.catalog_loader import load_catalog


def _dir_is_writable(dir_path: Path) -> bool:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        probe = dir_path / ".write_probe"
        probe.write_text("x", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def ensure_catalog_dataframe(cfg: AppConfig) -> pd.DataFrame:
    """
    Return the processed catalog DataFrame.

    If `cfg.paths.processed_catalog` exists, load it. Otherwise run HF ingest, preferring
    the configured paths when the parent directory is writable; else use a temp directory.
    """
    processed = cfg.paths.processed_catalog
    if processed.is_file():
        return load_catalog(processed)

    if _dir_is_writable(processed.parent):
        run_ingest_with_config(cfg)
        return load_catalog(processed)

    tmp_root = Path(os.environ.get("CATALOG_TMP_DIR", tempfile.gettempdir())) / "restaurant_rec_m1_catalog"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_processed = tmp_root / "restaurants.parquet"
    if tmp_processed.is_file():
        return load_catalog(tmp_processed)

    work_cfg = cfg.model_copy(
        update={
            "paths": cfg.paths.model_copy(
                update={
                    "raw_snapshot": tmp_root / "zomato_raw.parquet",
                    "processed_catalog": tmp_processed,
                    "ingest_report": tmp_root / "ingest_report.json",
                }
            )
        }
    )
    run_ingest_with_config(work_cfg)
    return load_catalog(tmp_processed)
