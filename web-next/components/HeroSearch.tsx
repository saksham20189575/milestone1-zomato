"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchLocalities, postRecommend, type RecommendItem, type RecommendResponse } from "@/lib/api";
import { RestaurantCard } from "@/components/RestaurantCard";

const CHIPS = ["Italian", "Spicy", "Dessert", "Near Me"] as const;

function buildExtras(cravings: string, aiQuery: string, chips: Set<string>): string | undefined {
  const parts: string[] = [];
  if (cravings.trim()) parts.push(`Cravings: ${cravings.trim()}`);
  if (aiQuery.trim()) parts.push(`What I said: ${aiQuery.trim()}`);
  if (chips.has("Near Me")) parts.push("Prefer options close / convenient in this locality.");
  if (chips.has("Spicy")) parts.push("Prefer spicy food.");
  if (chips.has("Dessert")) parts.push("Interested in desserts.");
  if (chips.has("Italian")) parts.push("Interest: Italian cuisine.");
  const s = parts.join(" ");
  return s || undefined;
}

export function HeroSearch() {
  const [localities, setLocalities] = useState<string[]>([]);
  const [locality, setLocality] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [budgetMax, setBudgetMax] = useState(1000);
  const [cravings, setCravings] = useState("");
  const [aiQuery, setAiQuery] = useState("");
  const [minRating, setMinRating] = useState(3.5);
  const [ratingRelax, setRatingRelax] = useState(true);
  const [chips, setChips] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchLocalities();
        if (!cancelled) {
          setLocalities(list);
          setLoadError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "Failed to load localities");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleChip = useCallback((label: string) => {
    setChips((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
    if (label === "Italian" && !cuisine.toLowerCase().includes("italian")) {
      setCuisine((c) => (c.trim() ? `${c}, Italian` : "Italian"));
    }
  }, [cuisine]);

  const extras = useMemo(
    () => buildExtras(cravings, aiQuery, chips),
    [cravings, aiQuery, chips],
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!locality) {
      setStatus("Choose a locality.");
      return;
    }
    setSubmitting(true);
    setStatus(null);
    setResult(null);
    try {
      const data = await postRecommend({
        location: locality,
        budget_max_inr: budgetMax,
        min_rating: minRating,
        enable_rating_relax: ratingRelax,
        cuisine: cuisine.trim() || undefined,
        extras,
      });
      setResult(data);
      if (!data.items?.length) {
        setStatus(data.summary || "No matches — try relaxing filters.");
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="relative min-h-[520px] overflow-hidden">
        <div className="absolute inset-0">
          <Image
            src="/hero-reference.png"
            alt=""
            fill
            className="object-cover object-center"
            priority
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/65 via-black/55 to-neutral-900/90" />
        </div>

        <div className="relative mx-auto max-w-6xl px-4 py-12 md:px-6 md:py-16">
          <div className="mx-auto max-w-2xl rounded-3xl bg-white p-6 shadow-2xl md:p-8">
            <h1 className="text-center text-2xl font-bold text-neutral-900 md:text-3xl">
              Find Your Perfect Meal with Zomato AI
            </h1>

            <form onSubmit={onSubmit} className="mt-6 space-y-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
                <div className="relative flex flex-1 items-center rounded-xl border border-neutral-200 bg-neutral-50 focus-within:border-zomato focus-within:ring-2 focus-within:ring-zomato/20">
                  <span className="pl-3 text-neutral-400" aria-hidden>
                    🎤
                  </span>
                  <input
                    type="text"
                    value={aiQuery}
                    onChange={(e) => setAiQuery(e.target.value)}
                    placeholder="Hi! What are you craving today?"
                    className="min-w-0 flex-1 bg-transparent px-2 py-3 text-sm outline-none placeholder:text-neutral-400"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-xl bg-zomato px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-zomato-dark sm:shrink-0"
                >
                  Send
                </button>
              </div>

              <div className="flex flex-wrap gap-2">
                {CHIPS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => toggleChip(c)}
                    className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${
                      chips.has(c)
                        ? "border-zomato bg-zomato-muted text-zomato-dark"
                        : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>

              {loadError && (
                <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Localities: {loadError} — is the API running at {process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"}?
                </p>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Locality
                  </span>
                  <select
                    required
                    value={locality}
                    onChange={(e) => setLocality(e.target.value)}
                    disabled={localities.length === 0}
                    className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-zomato focus:ring-2 focus:ring-zomato/20"
                  >
                    <option value="">(e.g. Banashankari)</option>
                    {localities.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Cuisine
                  </span>
                  <input
                    value={cuisine}
                    onChange={(e) => setCuisine(e.target.value)}
                    placeholder="(e.g. North Indian)"
                    className="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-zomato focus:ring-2 focus:ring-zomato/20"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Budget (max ₹ for two)
                  </span>
                  <input
                    type="number"
                    min={100}
                    max={100000}
                    step={50}
                    value={budgetMax}
                    onChange={(e) => setBudgetMax(Number(e.target.value))}
                    placeholder="e.g. 1000"
                    className="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-zomato focus:ring-2 focus:ring-zomato/20"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Specific cravings
                  </span>
                  <input
                    value={cravings}
                    onChange={(e) => setCravings(e.target.value)}
                    placeholder="(e.g. Biryani, Butter Chicken)"
                    className="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-zomato focus:ring-2 focus:ring-zomato/20"
                  />
                </label>
              </div>

              <details className="rounded-xl border border-neutral-100 bg-neutral-50/80 px-3 py-2 text-sm">
                <summary className="cursor-pointer font-medium text-neutral-700">More options</summary>
                <div className="mt-3 flex flex-wrap items-center gap-4">
                  <label className="flex items-center gap-2">
                    <span className="text-neutral-600">Min rating</span>
                    <input
                      type="number"
                      min={0}
                      max={5}
                      step={0.1}
                      value={minRating}
                      onChange={(e) => setMinRating(Number(e.target.value))}
                      className="w-20 rounded-lg border border-neutral-200 px-2 py-1"
                    />
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={ratingRelax}
                      onChange={(e) => setRatingRelax(e.target.checked)}
                    />
                    <span className="text-neutral-600">Relax rating if few matches</span>
                  </label>
                </div>
              </details>

              <button
                type="submit"
                disabled={submitting || localities.length === 0}
                className="w-full rounded-xl bg-zomato py-3.5 text-center text-base font-semibold text-white shadow-lg transition hover:bg-zomato-dark disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Finding picks…" : "Get Recommendations"}
              </button>
            </form>
          </div>
        </div>
      </section>

      <section className="border-t border-neutral-200 bg-neutral-50 py-12">
        <div className="mx-auto max-w-6xl px-4 md:px-6">
          <h2 className="text-xl font-bold text-neutral-900 md:text-2xl">Personalized Picks for You</h2>
          {status && (
            <p className="mt-4 rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-800">
              {status}
            </p>
          )}
          {result?.summary && result.items.length > 0 && (
            <p className="mt-4 max-w-3xl text-neutral-700">{result.summary}</p>
          )}
          {result?.meta && (
            <p className="mt-2 text-xs text-neutral-500">
              Shortlist {result.meta.shortlist_size} · {result.meta.used_llm ? "LLM ranked" : "Filtered only"}
              {result.meta.llm_parse_failed ? " (parse fallback)" : ""}
            </p>
          )}
          {!result && !status && (
            <p className="mt-8 text-center text-sm text-neutral-500">
              Your ranked restaurants will appear here after you submit the form.
            </p>
          )}
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            {(result?.items ?? []).map((item: RecommendItem, i: number) => (
              <RestaurantCard key={item.id || i} item={item} index={i} />
            ))}
          </div>
          {result && result.items.length === 0 && (
            <p className="mt-6 text-neutral-600">
              No cards to show — adjust locality, budget, or cuisine and try again.
            </p>
          )}
        </div>
      </section>
    </>
  );
}
