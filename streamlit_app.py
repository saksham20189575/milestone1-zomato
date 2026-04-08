"""
Streamlit Community Cloud entrypoint.

Set **Main file** to `streamlit_app.py`, Python 3.11+.
Add **Secrets**: `GROQ_API_KEY = "..."`.

If `data/processed/restaurants.parquet` is missing (typical on Cloud), the app downloads the
Hugging Face dataset once and writes the catalog under the container temp dir (requires network).
"""
from pathlib import Path

from restaurant_rec.phase4.streamlit_ui import run_app

run_app(Path(__file__).resolve().parent)
