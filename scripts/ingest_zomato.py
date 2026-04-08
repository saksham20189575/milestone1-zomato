#!/usr/bin/env python3
"""Download HF Zomato data, normalize to canonical schema, write Parquet + report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root: parent of scripts/
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from restaurant_rec.phase1.ingest import run_ingest


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1: HF Zomato → catalog Parquet")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="Path to config.yaml",
    )
    args = parser.parse_args()
    report = run_ingest(args.config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
