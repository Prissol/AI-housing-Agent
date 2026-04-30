import { FiArrowLeft, FiShield } from "react-icons/fi";
import { Link } from "react-router-dom";

function AuthLayout({ children }) {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-100 via-white to-cyan-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl gap-6 overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_22px_60px_rgba(15,23,42,0.16)] backdrop-blur-md lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative flex flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 p-8 text-white sm:p-10">
          <div className="absolute -left-16 -top-16 size-48 rounded-full bg-cyan-400/20 blur-3xl" aria-hidden="true" />
          <div className="absolute bottom-0 right-0 size-56 rounded-full bg-indigo-400/20 blur-3xl" aria-hidden="true" />
          <div className="relative">
            <Link
              to="/"
              className="mb-8 inline-flex items-center gap-2 rounded-xl border border-white/25 bg-white/10 px-3 py-2 text-sm font-medium text-white transition duration-200 hover:-translate-y-0.5 hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <FiArrowLeft size={14} aria-hidden="true" />
              Back to Home
            </Link>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/40 bg-cyan-300/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-200">
              <FiShield aria-hidden="true" size={13} />
              Secure • Compliant • Fast
            </div>
            <h1 className="mt-8 max-w-md text-3xl font-semibold leading-tight sm:text-4xl">
              Welcome to DHA Multan Compliance Intelligence.
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-200">
              Upload plans, validate bylaws, and generate decision-ready reports with transparent evidence.
            </p>
          </div>
          <div className="relative mt-10 rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.12em] text-cyan-300">Trusted by teams</p>
            <p className="mt-2 text-sm text-slate-100">For legal, planning, and architecture workflows requiring audit-ready outputs.</p>
          </div>
        </section>
        <section className="flex items-center justify-center p-6 sm:p-10">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-8">{children}</div>
        </section>
      </div>
    </main>
  );
}

export default AuthLayout;
