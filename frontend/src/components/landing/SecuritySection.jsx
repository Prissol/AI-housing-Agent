import { FiCheck, FiLock, FiShield } from "react-icons/fi";
import { securityPoints } from "./landingData";

function SecuritySection() {
  return (
    <section id="security" className="section-shell scroll-mt-28 pb-20">
      <div className="glass-panel grid gap-6 rounded-3xl p-7 lg:grid-cols-[0.9fr_1.1fr] lg:p-10">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.15em] text-indigo-700">Core product features</p>
          <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Built for real-world map compliance work</h2>
          <p className="mt-4 text-slate-600">
            From large architectural drawings to final rule-based verdicts, the platform is designed to make compliance reviews
            faster, traceable, and decision-ready.
          </p>
          <div className="mt-6 inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800">
            <FiShield aria-hidden="true" className="text-indigo-700" />
            Feature-first architecture
          </div>
        </div>

        <ul className="grid gap-3 text-sm">
          {securityPoints.map((point) => (
            <li key={point} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-slate-700">
              <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-emerald-50 text-emerald-700">
                <FiCheck size={14} aria-hidden="true" />
              </span>
              {point}
            </li>
          ))}
          <li className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-900 p-4 text-sm font-medium text-white">
            <FiLock size={16} aria-hidden="true" />
            Full evidence trail per decision for legal and authority review.
          </li>
        </ul>
      </div>
    </section>
  );
}

export default SecuritySection;
