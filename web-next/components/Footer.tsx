export function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-neutral-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 md:flex-row md:items-center md:justify-between md:px-6">
        <div>
          <p className="text-xl font-bold text-zomato">zomato</p>
          <p className="mt-2 max-w-md text-xs text-neutral-500">
            © {new Date().getFullYear()} Demo UI inspired by Zomato-style layouts. Connects to the
            milestone FastAPI backend for real recommendations.
          </p>
        </div>
        <div>
          <p className="mb-2 text-sm font-medium text-neutral-700">Follow Us</p>
          <div className="flex gap-2">
            {["f", "𝕏", "◎", "♪", "▶"].map((icon, i) => (
              <span
                key={i}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-neutral-200 bg-white text-sm text-neutral-600"
                aria-hidden
              >
                {icon}
              </span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
