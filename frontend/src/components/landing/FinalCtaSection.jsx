import { FiArrowRight } from "react-icons/fi";
import { Link } from "react-router-dom";

function FinalCtaSection() {
  return (
    <section className="section-shell pb-20">
      <div className="rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-900 to-slate-800 p-8 text-white shadow-[0_20px_48px_rgba(15,23,42,0.35)] sm:p-10">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr] lg:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.15em] text-cyan-300">Ready for smarter compliance?</p>
            <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">
              Turn map reviews into a fast, transparent, and legally grounded workflow.
            </h2>
          </div>
          <div className="flex flex-wrap justify-start gap-3 lg:justify-end">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              Upload a Map
              <FiArrowRight aria-hidden="true" />
            </Link>
            <a
              href="#contact"
              className="rounded-xl border border-white/30 bg-white/10 px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              Book Demo
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

export default FinalCtaSection;
