# Improvements (tracked)

The following were implemented in code, API, UI, and [phase-wise-architecture.md](./phase-wise-architecture.md):

0. **Next.js frontend (`web-next/`)** — App Router + Tailwind UI modeled on `design/Screenshot 2026-04-05 at 14.53.58.png`; calls the FastAPI backend via `NEXT_PUBLIC_API_BASE` (see `web-next/README.md` and architecture §4.3.2).

1. **Locality dropdown** — `GET /api/v1/localities` returns distinct catalog localities; the web UI `<select>` uses that endpoint. `GET /api/v1/locations` (distinct cities) remains for other clients. The recommend API still accepts JSON field `location` (matches catalog `locality` or `city`).
2. **Numeric budget** — User preference is `budget_max_inr` (max approximate cost for two in INR). Phase 2 keeps rows with known `cost_for_two ≤ budget_max_inr`. Groq prompts describe this value instead of low/medium/high tiers.
3. **Fixed shortlist size** — `max_results_shortlist` was removed from user input. `filter.max_shortlist_candidates` in `config.yaml` caps rows passed to the LLM (default 40).
