"""
Streamlit Community Cloud entrypoint.

Set **Main file** to `streamlit_app.py`, Python 3.11+.
Add **Secrets**: `GROQ_API_KEY = "..."`.
Ensure `data/processed/restaurants.parquet` exists at deploy time if `config.yaml` points there.
"""
from pathlib import Path

from restaurant_rec.phase4.streamlit_ui import run_app

run_app(Path(__file__).resolve().parent)
