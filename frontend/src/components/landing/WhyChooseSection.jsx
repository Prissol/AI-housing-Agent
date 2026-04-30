import { metrics } from "./landingData";

function WhyChooseSection() {
  return (
    <section className="section-shell pb-20">
      <div className="grid gap-8 rounded-3xl border border-slate-200 bg-white p-7 shadow-[0_20px_50px_rgba(15,23,42,0.08)] lg:grid-cols-[1.05fr_0.95fr] lg:p-10">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.15em] text-indigo-700">Why choose AI Legal Maps</p>
          <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Confident decisions without manual bottlenecks</h2>
          <p className="mt-5 text-base leading-relaxed text-slate-600">
            Manual compliance checks are slow, inconsistent, and hard to defend at scale. Our platform combines AI assistance
            with legal reasoning so teams can move faster while preserving accountability.
          </p>
          <ul className="mt-6 grid gap-2 text-sm text-slate-700">
            <li>- Consistent review quality across projects and reviewers</li>
            <li>- Clause-level explanations that improve stakeholder trust</li>
            <li>- Transparent records for internal and regulatory audits</li>
          </ul>
        </div>

        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          {metrics.map((metric) => (
            <article key={metric.label} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5">
              <div className="mb-3 grid size-10 place-items-center rounded-xl bg-slate-900 text-cyan-300">
                <metric.icon size={18} aria-hidden="true" />
              </div>
              <p className="text-3xl font-semibold text-slate-950">{metric.value}</p>
              <p className="mt-2 text-sm text-slate-600">{metric.label}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export default WhyChooseSection;
