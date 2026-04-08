from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import load_dataset

from restaurant_rec.config import AppConfig
from restaurant_rec.phase1.transform import hf_to_dataframe, transform_raw_dataframe
from restaurant_rec.phase1.validate import validate_catalog


def load_hf_dataframe(cfg: AppConfig) -> pd.DataFrame:
    ds = load_dataset(cfg.dataset.id, split=cfg.dataset.split)
    rows: list[dict[str, Any]] = [dict(ds[i]) for i in range(len(ds))]
    return hf_to_dataframe(rows)


def run_ingest_with_config(cfg: AppConfig) -> dict[str, Any]:
    """Download HF dataset, transform, validate, write Parquet + report using paths on `cfg`."""
    cfg.paths.raw_snapshot.parent.mkdir(parents=True, exist_ok=True)
    cfg.paths.processed_catalog.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "dataset_id": cfg.dataset.id,
        "split": cfg.dataset.split,
    }

    raw_df = load_hf_dataframe(cfg)
    report["rows_loaded"] = len(raw_df)
    raw_df.to_parquet(cfg.paths.raw_snapshot, index=False)
    report["raw_snapshot_path"] = str(cfg.paths.raw_snapshot)

    transformed, transform_stats = transform_raw_dataframe(raw_df, cfg)
    report["transform_stats"] = transform_stats

    cleaned, validate_stats = validate_catalog(transformed)
    report["validate_stats"] = validate_stats

    cleaned["cost_for_two"] = pd.to_numeric(cleaned["cost_for_two"], errors="coerce").astype("Int64")

    # Column order for stable downstream reads
    col_order = [
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
    ]
    cleaned = cleaned[[c for c in col_order if c in cleaned.columns]]

    cleaned.to_parquet(cfg.paths.processed_catalog, index=False)
    report["processed_catalog_path"] = str(cfg.paths.processed_catalog)
    report["rows_written"] = len(cleaned)

    cfg.paths.ingest_report.parent.mkdir(parents=True, exist_ok=True)
    cfg.paths.ingest_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["ingest_report_path"] = str(cfg.paths.ingest_report)
    return report


def run_ingest(config_path: Path | str) -> dict[str, Any]:
    cfg = AppConfig.load(config_path)
    return run_ingest_with_config(cfg)
