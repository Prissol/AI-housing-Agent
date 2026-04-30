import { FiArrowRight, FiCheckCircle } from "react-icons/fi";
import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <section className="section-shell grid gap-12 pb-20 pt-14 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
      <div className="animate-fade-up">
        <p className="mb-5 inline-flex items-center rounded-full border border-cyan-300/60 bg-cyan-50/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-cyan-700">
          Legal-tech for high-stakes map reviews
        </p>
        <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-slate-950 sm:text-5xl lg:text-6xl">
          Automate Multan map compliance with trusted AI reasoning.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
          Upload plans, validate by-laws with RAG, and produce decision-ready reports that explain every violation and every
          compliant outcome with confidence.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
          >
            Upload a Map
            <FiArrowRight size={16} aria-hidden="true" />
          </Link>
          <a
            href="#sample-report"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            See Sample Report
          </a>
        </div>

        <div className="mt-8 flex flex-wrap gap-6 text-sm text-slate-600">
          <p className="inline-flex items-center gap-2">
            <FiCheckCircle aria-hidden="true" className="text-emerald-500" />
            Rule-grounded outputs
          </p>
          <p className="inline-flex items-center gap-2">
            <FiCheckCircle aria-hidden="true" className="text-emerald-500" />
            Team-ready audit logs
          </p>
          <p className="inline-flex items-center gap-2">
            <FiCheckCircle aria-hidden="true" className="text-emerald-500" />
            Fast legal review cycles
          </p>
        </div>
      </div>

      <aside id="sample-report" className="animate-fade-up glass-panel rounded-3xl p-5 sm:p-7">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-4">
          <img src="/multan-logo.png" alt="DHA Multan Logo" className="mx-auto h-auto w-full max-w-[360px] object-contain" />
        </div>
      </aside>
    </section>
  );
}

export default HeroSection;
