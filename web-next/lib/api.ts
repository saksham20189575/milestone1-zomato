/**
 * Calls the FastAPI Phase 4 backend (see repo config.yaml + restaurant_rec.phase4.app).
 */

export function apiBase(): string {
  const b = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
  return b;
}

export async function fetchLocalities(): Promise<string[]> {
  const res = await fetch(`${apiBase()}/api/v1/localities`, {
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
  const res = await fetch(`${apiBase()}/api/v1/recommend`, {
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
