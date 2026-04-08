import type { RecommendItem } from "@/lib/api";

const plateGradients = [
  "from-amber-100 via-orange-50 to-rose-100",
  "from-emerald-100 via-lime-50 to-amber-50",
  "from-violet-100 via-fuchsia-50 to-rose-50",
  "from-sky-100 via-cyan-50 to-emerald-50",
];

function plateClass(index: number) {
  return plateGradients[index % plateGradients.length];
}

export function RestaurantCard({ item, index }: { item: RecommendItem; index: number }) {
  const cuisines = item.cuisines?.length ? item.cuisines.join(" • ") : "Restaurant";
  const rating = item.rating != null ? item.rating.toFixed(1) : "—";

  return (
    <article className="flex overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm transition hover:shadow-md">
      <div
        className={`relative hidden w-36 shrink-0 bg-gradient-to-br sm:block ${plateClass(index)}`}
        aria-hidden
      >
        <div className="absolute inset-2 rounded-xl border border-white/60 bg-white/30 backdrop-blur-sm" />
        <span className="absolute bottom-2 left-2 text-2xl opacity-80">🍽️</span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="text-lg font-bold text-neutral-900">{item.name ?? "Unknown"}</h3>
          <span className="flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-sm font-semibold text-amber-800">
            ★ {rating}
          </span>
        </div>
        <p className="mt-1 text-sm text-neutral-600">
          {cuisines}
          {item.cost_display ? ` • ${item.cost_display}` : ""}
        </p>
        <div className="mt-3 rounded-xl border border-rose-100 bg-zomato-muted/80 px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-zomato-dark">AI Reason</p>
          <p className="mt-1 text-sm leading-relaxed text-neutral-800">{item.explanation || "—"}</p>
        </div>
      </div>
    </article>
  );
}
