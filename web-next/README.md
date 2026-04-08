# Zomato-style Next.js frontend

Next.js 14 (App Router) + Tailwind UI inspired by `../design/Screenshot 2026-04-05 at 14.53.58.png`.

- **Local:** calls the **FastAPI** backend (`restaurant_rec.phase4.app`) via `NEXT_PUBLIC_API_BASE`.
- **Vercel (Streamlit backend):** leave `NEXT_PUBLIC_API_BASE` **unset** in production and set **`NEXT_PUBLIC_STREAMLIT_APP_URL`** to your Streamlit URL. The site becomes a marketing shell with a button that opens the live Streamlit app (Streamlit does not expose `/api/v1/*`).

## Setup

If `npm install` hangs or times out, this folder includes **`.npmrc`** pointing at the public npm registry (`registry.npmjs.org`). Remove or override it if your org needs a different registry.

```bash
cp .env.local.example .env.local
# edit NEXT_PUBLIC_API_BASE if the API is not http://127.0.0.1:8000

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Start the API from the repo root (Python venv):

```bash
uvicorn restaurant_rec.phase4.app:app --host 127.0.0.1 --port 8000 --reload
```

## Deploy on Vercel

1. New project → import the Git repo → set **Root Directory** to **`web-next`**.
2. **Environment variables (production):**
   - **`NEXT_PUBLIC_STREAMLIT_APP_URL`** = `https://milestone1-zomato-o.streamlit.app` (no trailing slash).
   - **Do not** set `NEXT_PUBLIC_API_BASE` unless you also host FastAPI somewhere; leaving it unset enables Streamlit shell mode.
3. Deploy. Preview builds use the same env; for local `npm run dev`, keep `.env.local` with `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` for the full form.

## Hero image

`public/hero-reference.png` is copied from the design screenshot for the hero background. Replace it with your own asset if you prefer a smaller repo or different art direction.

## API mapping

| UI | Backend |
|----|---------|
| Locality `<select>` | `GET /api/v1/localities` → JSON `location` |
| Cuisine, budget, cravings, AI bar, chips | `POST /api/v1/recommend` (`cuisine`, `budget_max_inr`, `extras`, …) |
| “More options” | `min_rating`, `enable_rating_relax` |

See `../docs/phase-wise-architecture.md` §4.3.2.
