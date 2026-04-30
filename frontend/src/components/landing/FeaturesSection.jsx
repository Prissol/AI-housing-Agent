import { features } from "./landingData";

function FeaturesSection() {
  return (
    <section id="features" className="section-shell scroll-mt-28 pb-20">
      <div className="mb-10 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-indigo-700">Core capabilities</p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Everything your compliance team needs</h2>
        <p className="mx-auto mt-4 max-w-2xl text-slate-600">
          AI Legal Maps brings map analysis, legal reasoning, and collaboration together in one premium workflow.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {features.map((feature) => (
          <article
            key={feature.title}
            className="group glass-panel rounded-2xl p-6 transition duration-300 hover:-translate-y-1 hover:shadow-xl"
          >
            <div className="mb-5 grid size-11 place-items-center rounded-xl bg-slate-900 text-cyan-300 shadow-sm transition group-hover:bg-indigo-700">
              <feature.icon size={18} aria-hidden="true" />
            </div>
            <h3 className="text-xl font-semibold text-slate-950">{feature.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">{feature.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FeaturesSection;
