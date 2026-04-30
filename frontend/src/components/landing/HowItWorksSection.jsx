import { workflowSteps } from "./landingData";

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="section-shell scroll-mt-28 pb-20">
      <div className="mb-10 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-indigo-700">How it works</p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">From map upload to audit-ready decision</h2>
      </div>

      <ol className="grid gap-4 lg:grid-cols-4">
        {workflowSteps.map((step, index) => (
          <li key={step.title} className="glass-panel rounded-2xl p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="grid size-10 place-items-center rounded-xl bg-indigo-700/10 text-indigo-700">
                <step.icon size={18} aria-hidden="true" />
              </div>
              <span className="text-sm font-semibold text-slate-500">0{index + 1}</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-950">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default HowItWorksSection;
