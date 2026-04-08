# Phase-Wise Architecture: AI-Powered Restaurant Recommendation System

This document expands the build plan for the Zomato-style recommendation service described in [problemStatement.md](./problemStatement.md). Each phase lists objectives, components, interfaces, data artifacts, and exit criteria.

---

## System context

**Purpose:** Combine a real restaurant dataset with user preferences and an LLM to produce ranked recommendations with natural-language explanations.

**High-level flow:**

1. Offline or on-demand: load and normalize restaurant records.
2. Online: accept preferences → filter catalog to a shortlist → prompt **Groq** (Phase 3) → return structured UI payload.

**Non-goals (unless you add them later):** user accounts, live Zomato scraping, training custom embedding models.

---

## Phase 1 — Foundation, dataset contract, and catalog

### 1.1 Objectives

- Establish a **single source of truth** for restaurant data after Hugging Face ingest.
- Define a **canonical schema** so filtering, prompting, and UI do not depend on raw column names.
- Make ingestion **repeatable** (same command → same artifact).

### 1.2 Dataset source

- **Primary:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) via `datasets` library or export script.

### 1.3 Canonical schema (recommended fields)

Map HF columns to internal names (exact mapping depends on dataset columns; validate after first load):

| Internal field        | Role |
|-----------------------|------|
| `id`                  | Stable string or hash (if missing, derive from name+location) |
| `name`                | Restaurant name |
| `city`                | Metro (from URL/address); alias-normalized |
| `locality`            | Main listing area: prefer HF `listed_in(city)`, else `location` (see `catalog-schema.md`) |
| `cuisines`            | List of strings or single pipe/comma-separated field parsed to list |
| `rating`              | Float 0–5 (or dataset scale; document and normalize) |
| `cost_for_two` or `approx_cost` | Numeric or categorical; derive `budget_tier`: `low` \| `medium` \| `high` |
| `votes` / `review_count` | Optional; use for tie-breaking in shortlist |
| `address` or `locality` | Optional; richer prompts and UI |
| `raw_features`        | Optional blob for “family-friendly” style hints if present in text columns |

### 1.4 Components

| Component | Responsibility |
|-----------|----------------|
| **Ingestion script** | Download/load split, select columns, rename to canonical schema |
| **Validators** | Row-level checks (rating range, required name/location), quarantine or drop bad rows with counts logged |
| **Transformers** | Parse cuisines, normalize city, compute `budget_tier` from rules (e.g. quantiles or fixed thresholds) |
| **Catalog store** | Versioned file: Parquet (preferred), SQLite, or JSON Lines for small prototypes |

Implementation lives under `restaurant_rec.phase1` (`ingest`, `transform`, `validate`, `schema`) and `scripts/ingest_zomato.py`.

### 1.5 Artifacts and layout (suggested)

```
data/
  raw/              # optional: snapshot of downloaded slice
  processed/
    restaurants.parquet   # or restaurants.db
scripts/
  ingest_zomato.py   # or notebooks/01_ingest.ipynb for exploration-only phase
web/
  index.html, styles.css, app.js   # Phase 4 UI (served at / and /static/)
src/restaurant_rec/
  config.py          # shared: AppConfig, paths, dataset + filter tuning
  phase1/            # catalog ingest + schema
  phase2/            # preferences, load catalog, deterministic filter
  phase3/            # Groq prompts, JSON parse, `recommend()` orchestration
  phase4/            # FastAPI backend: `POST /api/v1/recommend`, `GET /health`
```

### 1.6 Configuration

- Path to catalog file, encoding, and threshold constants (rating scale, budget cutoffs) in `config.yaml` or environment variables.

### 1.7 Exit criteria

- Documented schema with example row (JSON).
- One command reproduces `processed/restaurants.*` from HF.
- Documented row counts before/after cleaning and top reasons for drops.

---

## Phase 2 — Preference model and deterministic filtering

### 2.1 Objectives

- Convert user input into a **typed preference object**.
- Produce a **bounded shortlist** (e.g. 20–50 venues) that is small enough for one LLM call but diverse enough to rank.

### 2.2 Preference model (API / domain)

Structured input (align with problem statement):

| Field | Type | Notes |
|-------|------|--------|
| `location` | string | Match on catalog `locality` or `city` (UI: dropdown from `GET /api/v1/localities`) |
| `budget_max_inr` | integer | Max approximate **cost for two** in INR; rows with `cost_for_two > budget_max_inr` or unknown cost are excluded |
| `cuisine` | string or list | Match against `cuisines` (substring or token match); omit or empty → no cuisine filter |
| `min_rating` | float | Hard filter: `rating >= min_rating` |
| `enable_rating_relax` | bool (optional) | If sparse matches, one optional downgrade of `min_rating` (see `filter.rating_relax_delta`) |
| `extras` | string (optional) | Free text for LLM prompt (e.g. family-friendly) |

Shortlist length sent to the LLM is **not** a user field: `filter.max_shortlist_candidates` in `config.yaml` (default 40).

### 2.3 Filtering pipeline (order matters)

1. **Location filter:** Exact or normalized match on `city` / `location`.
2. **Cuisine filter:** At least one cuisine matches user selection (case-insensitive).
3. **Rating filter:** `rating >= min_rating`; if too few results, optional relax step (document policy: e.g. lower min by 0.5 once).
4. **Budget filter:** `cost_for_two` present and `cost_for_two <= budget_max_inr` (unknown cost excluded).
5. **Ranking for shortlist:** Sort by `rating` desc, then `votes` desc; take top **`filter.max_shortlist_candidates`** (`N`).

### 2.4 Component boundaries

| Module (package path) | Responsibility |
|------------------------|----------------|
| `restaurant_rec.phase2.preferences` | Pydantic validation, defaults (`UserPreferences`) |
| `restaurant_rec.phase2.filter` | `filter_restaurants(catalog_df, prefs) -> FilterResult` |
| `restaurant_rec.phase2.catalog_loader` | Load Parquet into a DataFrame at startup |
| `restaurant_rec.phase2.cities` / `localities` | `distinct_cities` / `distinct_localities(catalog)` for dropdowns |

### 2.5 Edge cases

- **Zero matches:** Return empty shortlist with reason codes (`NO_LOCATION`, `NO_CUISINE`, etc.) for UI messaging.
- **Missing rating:** Excluded when `min_rating` filter applies. **Missing `cost_for_two`:** Excluded from numeric budget filter.

### 2.6 Exit criteria

- Unit tests for filter combinations and empty results.
- Shortlist size and latency predictable (log timing for 100k rows if applicable).

---

## Phase 3 — LLM integration: prompt contract and orchestration

Phase 3 uses **Groq** (GroqCloud / Groq API) as the LLM for ranking, explanations, and optional summaries. The Groq **API key is loaded from a `.env` file** (see §3.6); never commit real keys to version control.

### 3.1 Objectives

- Given **preferences + shortlist JSON**, produce **ordered recommendations** with **per-item explanations** and optional **overall summary**.
- Keep behavior **testable** (template version, structured output where possible).
- Call **Groq** over HTTP with the official Groq Python SDK or OpenAI-compatible client pointed at Groq’s base URL, using credentials supplied via environment variables populated from `.env`.

### 3.2 Inputs to the LLM

- **System message:** Role (expert recommender), constraints (only recommend from provided list; respect min rating and **max budget in INR**; if list empty, say so).
- **User message:** Serialized shortlist (compact JSON or markdown table) + preference summary + `extras` text.

### 3.3 Output contract

Preferred: **JSON** from the model (with schema validation and repair retry):

```json
{
  "summary": "string",
  "recommendations": [
    {
      "restaurant_id": "string",
      "rank": 1,
      "explanation": "string"
    }
  ]
}
```

Fallback: parse markdown numbered list if JSON fails; log and degrade gracefully.

### 3.4 Prompt engineering checklist

- Include **only** restaurants from the shortlist (by id) to reduce hallucination.
- Ask for **top K** (e.g. 5) with **one paragraph max** per explanation.
- Instruct to **cite** concrete attributes (cuisine, rating, cost) from the data.

### 3.5 Orchestration service

| Step | Action |
|------|--------|
| 1 | Build shortlist (Phase 2) |
| 2 | If empty, return structured empty response (skip LLM or single small call explaining no matches) |
| 3 | Render prompt from template + data |
| 4 | Call **Groq** API with timeout and max tokens |
| 5 | Parse/validate response; on failure, retry once with “JSON only” reminder or fall back to heuristic order |

### 3.6 Configuration

- **API key (Groq):** Keep the Groq API key in a **`.env`** file in the project root (or the directory the app loads env from). Use `python-dotenv` or your framework’s equivalent so values are available as environment variables at runtime. Add `.env` to `.gitignore` and commit only a **`.env.example`** (or README snippet) listing required variable names with empty or placeholder values.
- **Typical variable name:** `GROQ_API_KEY` (confirm against [Groq API documentation](https://console.groq.com/docs) when implementing).
- **Non-secret settings:** Model id (e.g. Groq-hosted model name), temperature (low for consistency), `max_tokens`, and display `top_k` can live in `config.yaml` or additional env vars as needed.

### 3.7 Exit criteria

- Golden-file or manual eval sheet for ~10 preference profiles.
- Documented latency and token usage for typical shortlist sizes.

---

## Phase 4 — Application layer: API and presentation

### 4.1 Objectives

- Expose a **single recommendation endpoint** (or CLI) that returns everything the UI needs.
- Render **Restaurant Name, Cuisine, Rating, Estimated Cost, AI explanation** per row.

### 4.2 Backend API (recommended shape)

**`GET /api/v1/localities`** — `{ "localities": ["Banashankari", "Koramangala", ...] }` (distinct `locality`) for the UI dropdown. **`GET /api/v1/locations`** remains for distinct metros (`city`) if needed.

**`POST /api/v1/recommend`**

Request body: JSON matching `UserPreferences` (Phase 2): `location`, `budget_max_inr`, `min_rating`, optional `cuisine`, `extras`, `enable_rating_relax`.

Response body:

```json
{
  "summary": "string",
  "items": [
    {
      "id": "string",
      "name": "string",
      "cuisines": ["string"],
      "rating": 4.2,
      "estimated_cost": "medium",
      "cost_display": "₹800 for two",
      "explanation": "string",
      "rank": 1
    }
  ],
  "meta": {
    "shortlist_size": 35,
    "model": "string",
    "prompt_version": "v1"
  }
}
```

**Implementation note:** Merge LLM output with catalog rows by `restaurant_id` to fill cuisine, rating, and cost for display (do not trust the LLM for numeric facts).

**Backend (implemented):** `restaurant_rec.phase4.app` — FastAPI app with CORS enabled. Run from repo root after `pip install -e .`:

`uvicorn restaurant_rec.phase4.app:app --reload`

Open **http://127.0.0.1:8000/** for the **embedded** static UI (`web/`). Interactive API: **http://127.0.0.1:8000/docs**.

For the **Next.js** experience (recommended for demos), run the frontend separately (see §4.3.1) and keep the API on **:8000**.

Loads `config.yaml` and `paths.processed_catalog` at startup; `GROQ_API_KEY` from `.env` applies to recommend calls.

### 4.3 UI — web clients (end-to-end)

Two frontends share the same Phase 4 JSON API (`GET /api/v1/localities`, `POST /api/v1/recommend`). The request body still uses JSON field **`location`** for the chosen **locality** (or city), plus **`budget_max_inr`**, **`min_rating`**, optional **`cuisine`**, **`extras`**, **`enable_rating_relax`**.

#### 4.3.1 Static app — `web/`

Served by FastAPI at **`/`** and **`/static/*`** (same origin as the API). Vanilla **HTML / CSS / JS**; minimal footprint for CI and quick checks.

#### 4.3.2 Next.js app — `web-next/` (Zomato-style UI)

A **Next.js 14 (App Router) + Tailwind** client aligned with the product mock under **`design/`** (e.g. `design/Screenshot 2026-04-05 at 14.53.58.png`):

- **Header:** brand bar + nav placeholders (Home, Dining Out, Delivery, Profile).
- **Hero:** full-width food imagery (reference asset copied to `web-next/public/hero-reference.png`) with dark overlay and a centered **search card**.
- **Card contents:** headline (“Find Your Perfect Meal…”), **AI-style** text field (merged into **`extras`** for the LLM), **quick chips** (Italian / Spicy / Dessert / Near Me), **2×2 grid**: Locality (`<select>` from **`GET /api/v1/localities`**), Cuisine, max budget (**`budget_max_inr`**), specific cravings (**`extras`**), collapsible **min rating** + rating relax, primary **Get Recommendations** CTA.
- **Results:** “Personalized Picks for You” — responsive **2-column** grid of cards with rating, cuisines, cost, and a pink-tinted **“AI Reason”** block from each item’s **`explanation`**.

**Configuration:** copy **`web-next/.env.local.example`** → **`.env.local`** and set **`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`** (or your API host). The browser calls the API directly; FastAPI **CORS** is already permissive for local dev.

**Run (two terminals):** (1) `uvicorn restaurant_rec.phase4.app:app --host 127.0.0.1 --port 8000 --reload` from repo root after `pip install -e .`. (2) `cd web-next && npm install && npm run dev` → **http://localhost:3000**.

| Option | Status / use when |
|--------|-------------------|
| **`web-next/`** | **Primary demo UI** — richer UX, easy to extend (components, routing, assets) |
| **`web/`** | **Minimal** — same API, zero Node toolchain |
| **Backend API** | **Current** — JSON as in §4.2 |
| **CLI** | Optional; `curl` or **/docs** |
| **Notebook** | Teaching/demo only |

### 4.4 Cross-cutting concerns

- **CORS** when the Next.js app (e.g. **http://localhost:3000**) calls the API on another origin; widen `allow_origins` in production.
- **Rate limiting** if exposed publicly.
- **Input validation** return 422 with field errors.

### 4.5 Exit criteria

- **Backend:** `POST /api/v1/recommend` returns structured `summary`, `items`, and `meta`; validation errors return **422**; empty filter outcomes return **200** with empty `items` and a clear `summary`.
- **Browser:** user opens `/`, submits preferences → sees summary and ranked cards (or empty-state message).
- Empty and error states copy-reviewed for clarity.

---

## Phase 5 — Hardening, observability, and quality

### 5.1 Objectives

- Improve **reliability**, **debuggability**, and **iterative prompt/dataset** updates without breaking clients.

### 5.2 Caching

- Key: hash of `(preferences, shortlist content hash, prompt_version, model)`.
- TTL or LRU for repeated queries in demos.

### 5.3 Logging and metrics

- Structured logs: `shortlist_size`, `duration_filter_ms`, `duration_llm_ms`, `outcome` (success / empty / error).
- Avoid logging full prompts if they contain sensitive data; truncate or redact.

### 5.4 Testing strategy

| Layer | Tests |
|-------|--------|
| Filter | Unit tests, property tests optional |
| Prompt | Snapshot of rendered template with fixture data |
| API | Contract tests for `/recommend` |
| LLM | Marked optional integration tests with recorded responses |

### 5.5 Deployment (optional)

- **Primary layout:** Streamlit (backend) + Vercel (frontend) — see **Deployment** above.
- **Alternatives:** Containerize API + mount `data/processed` for self-hosted or other PaaS targets.
- Secrets via env; no keys in repo.

### 5.6 Exit criteria

- Runbook: how to refresh data, bump prompt version, rotate API keys.
- Basic load/latency note for expected concurrency.

---

## Dependency graph between phases

```
Phase 1 (Catalog)
    │
    ▼
Phase 2 (Filter + Preferences)
    │
    ▼
Phase 3 (LLM orchestration)
    │
    ▼
Phase 4 (API + UI)
    │
    ▼
Phase 5 (Hardening)
```

Phases 2–3 can be prototyped in a notebook before extraction into modules; Phase 4 should consume stable interfaces from 2 and 3.

---

## Technology stack (suggestion, not mandatory)

| Concern | Suggested default |
|---------|-------------------|
| Language | Python 3.11+ |
| Data | `pandas` or `polars` + Parquet |
| Validation | Pydantic v2 |
| API | FastAPI |
| LLM | **Groq** via Groq API; key in `.env` → env (e.g. `GROQ_API_KEY`) |
| UI | Simple React/Vite or Streamlit for speed |

Adjust to your course constraints; the phase boundaries stay the same.

---

## Deployment

The system is split across two managed hosts: the **Python application and recommendation pipeline** run on **Streamlit** (backend), and the **primary web client** (`web-next/`, Next.js) is deployed on **Vercel** (frontend).

### Backend — Streamlit

- **Platform:** [Streamlit Community Cloud](https://streamlit.io/cloud) or equivalent Streamlit hosting that runs your Python environment.
- **Repo entrypoint:** Root **`streamlit_app.py`** → **`restaurant_rec.phase4.streamlit_ui`**, which loads `config.yaml`, the Parquet catalog, and runs the same **`recommend()`** path as FastAPI.
- **Dependencies:** Root **`requirements.txt`** installs **`-e ".[streamlit]"`** (see **`pyproject.toml`** optional extra `streamlit`). Local dev: `pip install -e ".[streamlit]"` then `streamlit run streamlit_app.py`.
- **Secrets:** In Streamlit Cloud → **Secrets**, set **`GROQ_API_KEY`**. Locally, `.streamlit/secrets.toml` is gitignored; `.env` still works via `load_project_dotenv`.
- **Data:** `config.yaml` → **`paths.processed_catalog`**. If that file is missing and the repo tree is **read-only** (Streamlit Cloud), **`ensure_catalog_dataframe`** runs Phase 1 ingest once and writes Parquet under the container temp dir (needs **outbound network** to Hugging Face). Locally, if `data/processed/` is writable, ingest fills the configured path instead.
- **Stability:** Pin Python 3.11+ on Cloud; keep `requirements.txt` aligned with `pyproject.toml`.
- **Note:** Streamlit is a **hosted UI + Python backend**, not a substitute for **`POST /api/v1/recommend`**. The **Vercel** Next.js app still needs **`NEXT_PUBLIC_API_BASE`** pointing at a **FastAPI** (or other) JSON host unless you change the frontend to stop calling REST.

### Frontend — Vercel

- **Project:** Point Vercel at **`web-next/`** (or the monorepo with root directory set to `web-next`).
- **Build:** Default Next.js settings (`npm run build`); Node version per Vercel defaults or `engines` in `package.json` if you need a specific major.
- **Environment:** Set **`NEXT_PUBLIC_API_BASE`** to the **FastAPI base URL** (e.g. `https://api.example.com` without a trailing slash)—the JSON API from §4.2, not the Streamlit page URL.
- **CORS:** FastAPI (or whichever serves `/api/v1/*`) must allow the Vercel origin—see §4.4.

### End-to-end

1. Deploy Streamlit (`streamlit_app.py`), secrets, and catalog; smoke-test recommendations in the browser.
2. If using **web-next/**: deploy FastAPI (or equivalent) where CORS allows Vercel; set **`NEXT_PUBLIC_API_BASE`** to that API base URL; smoke-test localities + recommend from the live Vercel URL.

---

## Traceability to problem statement

| Problem statement item | Phase |
|------------------------|-------|
| Load HF Zomato dataset, extract fields | 1 |
| User preferences (location, `budget_max_inr`, cuisine, rating, extras) | 2, 4 |
| Filter + prepare data for LLM | 2, 3 |
| Prompt for reasoning and ranking | 3 |
| LLM rank + explanations + summary | 3 |
| Display name, cuisine, rating, cost, explanation | 4 |

---

*Document version: 1.11 — Catalog bootstrap: auto-ingest to temp when Parquet missing (Streamlit Cloud).*
