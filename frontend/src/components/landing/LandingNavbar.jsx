import { Link } from "react-router-dom";
import { navItems } from "./landingData";

function LandingNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <nav className="section-shell flex items-center justify-between gap-4 py-4" aria-label="Main navigation">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center overflow-hidden rounded-full border border-slate-200 bg-white shadow-sm">
            <img src="/multan-logo.png" alt="Multan Logo" className="size-full object-cover" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">AI Legal Maps</p>
            <p className="text-sm font-semibold text-slate-900">Compliance Intelligence Platform</p>
          </div>
        </div>

        <div className="hidden items-center gap-7 lg:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-slate-700 transition hover:text-slate-950 focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/dashboard"
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            Analyze
          </Link>
          <Link
            to="/auth"
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
          >
            Login
          </Link>
        </div>
      </nav>
    </header>
  );
}

export default LandingNavbar;
