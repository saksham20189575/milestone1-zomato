/**
 * Backend integration:
 * - **FastAPI** (local or hosted): set `NEXT_PUBLIC_API_BASE` → JSON `/api/v1/*`.
 * - **Streamlit only** (e.g. Vercel prod): leave `NEXT_PUBLIC_API_BASE` unset in production
 *   and set `NEXT_PUBLIC_STREAMLIT_APP_URL` → marketing shell links to the live app.
 */

export function streamlitAppUrl(): string | null {
  const raw = process.env.NEXT_PUBLIC_STREAMLIT_APP_URL;
  if (raw != null && String(raw).trim() !== "") {
    return String(raw).trim().replace(/\/$/, "");
  }
  return null;
}

/**
 * JSON API base, or `null` in production when unset (Streamlit-only deploy).
 * In development, defaults to `http://127.0.0.1:8000` when unset.
 */
export function resolvedApiBase(): string | null {
  const raw = process.env.NEXT_PUBLIC_API_BASE;
  if (raw != null && String(raw).trim() !== "") {
    return String(raw).trim().replace(/\/$/, "");
  }
  if (process.env.NODE_ENV !== "production") {
    return "http://127.0.0.1:8000";
  }
  return null;
}

/** Vercel + Streamlit backend: no JSON API configured, but Streamlit URL is set. */
export function preferStreamlitShell(): boolean {
  return streamlitAppUrl() !== null && resolvedApiBase() === null;
}

/** Base URL for `fetch`; throws if missing (should not run in Streamlit shell mode). */
export function apiBase(): string {
  const b = resolvedApiBase();
  if (!b) {
    throw new Error("NEXT_PUBLIC_API_BASE is not set; use Streamlit shell mode or configure the API URL.");
  }
  return b;
}

export async function fetchLocalities(): Promise<string[]> {
  const base = resolvedApiBase();
  if (!base) {
    return [];
  }
  const res = await fetch(`${base}/api/v1/localities`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  const data = (await res.json()) as { localities?: string[] };
  return data.localities ?? [];
}

export type RecommendBody = {
  location: string;
  budget_max_inr: number;
  min_rating: number;
  enable_rating_relax: boolean;
  cuisine?: string;
  extras?: string;
};

export type RecommendItem = {
  id: string;
  name: string | null;
  cuisines: string[];
  rating: number | null;
  cost_display: string;
  explanation: string;
  rank: number;
};

export type RecommendResponse = {
  summary: string;
  items: RecommendItem[];
  meta: {
    shortlist_size: number;
    model: string;
    prompt_version: string;
    filter_reason?: string;
    used_llm?: boolean;
    rating_relaxed?: boolean;
    llm_parse_failed?: boolean;
  };
};

export async function postRecommend(body: RecommendBody): Promise<RecommendResponse> {
  const base = resolvedApiBase();
  if (!base) {
    throw new Error("API base URL is not configured.");
  }
  const res = await fetch(`${base}/api/v1/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON (${res.status}): ${text.slice(0, 400)}`);
  }
  if (!res.ok) {
    const d = data as { detail?: unknown };
    throw new Error(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail ?? data));
  }
  return data as RecommendResponse;
}
