import Link from "next/link";

const nav = [
  { href: "#", label: "Home", active: true },
  { href: "#", label: "Dining Out", active: false },
  { href: "#", label: "Delivery", active: false },
  { href: "#", label: "Profile", active: false },
];

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 md:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tracking-tight text-zomato">zomato</span>
          <span className="text-lg font-semibold text-neutral-800">AI</span>
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium md:flex">
          {nav.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className={
                item.active
                  ? "text-zomato"
                  : "text-neutral-600 transition hover:text-neutral-900"
              }
            >
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
