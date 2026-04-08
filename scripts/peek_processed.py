#!/usr/bin/env python3
"""Print the first N rows of the processed restaurant catalog (Parquet)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from restaurant_rec.config import AppConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Show first rows of processed catalog")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="config.yaml (for processed_catalog path)",
    )
    parser.add_argument(
        "-n",
        "--rows",
        type=int,
        default=10,
        help="number of rows to print (default: 10)",
    )
    args = parser.parse_args()

    cfg = AppConfig.load(args.config)
    path = cfg.paths.processed_catalog
    if not path.is_file():
        print(f"Missing catalog: {path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(path)
    n = min(max(1, args.rows), len(df))
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 60)
    print(f"{path} — {len(df)} rows, showing first {n}:\n")
    print(df.head(n).to_string())


if __name__ == "__main__":
    main()
