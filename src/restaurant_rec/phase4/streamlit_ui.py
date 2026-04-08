"""Streamlit UI: same Phase 2–4 pipeline as the FastAPI app (for Streamlit Community Cloud)."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from restaurant_rec.config import AppConfig
from restaurant_rec.phase2.catalog_bootstrap import ensure_catalog_dataframe
from restaurant_rec.phase2.localities import distinct_localities
from restaurant_rec.phase2.preferences import UserPreferences
from restaurant_rec.phase3.env_util import load_project_dotenv
from restaurant_rec.phase3.orchestrate import recommend
from restaurant_rec.phase4.schemas import result_to_response
from restaurant_rec.phase4.streamlit_secrets import hydrate_groq_key_from_streamlit_secrets


@st.cache_resource(show_spinner="Loading catalog (first run may download from Hugging Face)…")
def _load_cfg_and_catalog(cfg_path_str: str) -> tuple[AppConfig, pd.DataFrame]:
    cfg_path = Path(cfg_path_str)
    load_project_dotenv(cfg_path)
    hydrate_groq_key_from_streamlit_secrets()
    cfg = AppConfig.load(cfg_path)
    catalog = ensure_catalog_dataframe(cfg)
    return cfg, catalog


def run_app(repo_root: Path) -> None:
    st.set_page_config(page_title="Restaurant recommendations", page_icon="🍽️", layout="wide")
    hydrate_groq_key_from_streamlit_secrets()

    cfg_path = (repo_root / "config.yaml").resolve()
    if not cfg_path.is_file():
        st.error(f"Missing **config.yaml** at `{cfg_path}`.")
        st.stop()

    try:
        cfg, catalog = _load_cfg_and_catalog(str(cfg_path))
    except FileNotFoundError as e:
        st.error("Catalog could not be loaded or built.")
        st.caption(str(e))
        st.info(
            "Ensure network access to Hugging Face (dataset in `config.yaml`), or place "
            "**`data/processed/restaurants.parquet`** next to `config.yaml`."
        )
        st.stop()
    except Exception as e:
        st.exception(e)
        st.stop()

    localities = distinct_localities(catalog)
    if not localities:
        st.error("No localities found in catalog.")
        st.stop()

    st.title("AI restaurant recommendations")
    st.caption("Phase 2 filter → Groq ranking (same logic as the FastAPI backend).")

    col_a, col_b = st.columns(2)
    with col_a:
        location = st.selectbox("Locality", options=localities, index=0)
        budget_max_inr = st.number_input("Max budget (INR for two)", min_value=100, max_value=100_000, value=2000, step=100)
        cuisine_raw = st.text_input("Cuisine (optional, comma-separated)", placeholder="e.g. Italian, Chinese")
    with col_b:
        min_rating = st.slider("Minimum rating", min_value=0.0, max_value=5.0, value=3.5, step=0.1)
        enable_rating_relax = st.checkbox("Allow rating relax if few matches", value=True)
        extras = st.text_area("Extras / cravings (optional, for the AI)", placeholder="family-friendly, outdoor seating…")

    submitted = st.button("Get recommendations", type="primary")

    if not submitted:
        return

    if not os.getenv("GROQ_API_KEY"):
        st.warning("**GROQ_API_KEY** is not set. Add it to `.env` locally or to Streamlit **Secrets** for deployment.")

    try:
        prefs = UserPreferences(
            location=location,
            budget_max_inr=int(budget_max_inr),
            cuisine=cuisine_raw or None,
            min_rating=float(min_rating),
            extras=extras or None,
            enable_rating_relax=enable_rating_relax,
        )
    except ValidationError as e:
        st.error("Invalid preferences")
        st.json(e.errors())
        return

    with st.spinner("Filtering and calling the model…"):
        raw = recommend(catalog, prefs, cfg, config_path=cfg_path)
        resp = result_to_response(raw)

    st.subheader("Summary")
    st.write(resp.summary)

    meta = resp.meta
    st.caption(
        f"Shortlist: {meta.shortlist_size} · model: {meta.model} · prompt: {meta.prompt_version} · "
        f"filter: {meta.filter_reason} · LLM: {meta.used_llm}"
        + (f" · relaxed rating to {meta.effective_min_rating}" if meta.rating_relaxed else "")
    )

    if not resp.items:
        st.info("No items to show — try relaxing filters or another locality.")
        return

    st.subheader("Personalized picks")
    for it in sorted(resp.items, key=lambda x: x.rank):
        with st.expander(f"#{it.rank} — {it.name or it.id}", expanded=(it.rank <= 3)):
            c1, c2, c3 = st.columns(3)
            c1.metric("Rating", f"{it.rating:.1f}" if it.rating is not None else "—")
            c2.write(f"**Cuisines:** {', '.join(it.cuisines) if it.cuisines else '—'}")
            c3.write(f"**Cost:** {it.cost_display or it.estimated_cost or '—'}")
            st.markdown(f"**AI reason:** {it.explanation}")
