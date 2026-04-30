import { testimonials } from "./landingData";

function TestimonialsSection() {
  return (
    <section className="section-shell pb-20">
      <div className="mb-10 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-indigo-700">Trusted by professionals</p>
        <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Teams rely on AI Legal Maps for defensible decisions</h2>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {testimonials.map((item) => (
          <article key={item.name} className="glass-panel rounded-2xl p-6">
            <p className="text-base leading-relaxed text-slate-700">"{item.quote}"</p>
            <div className="mt-6 border-t border-slate-200 pt-4">
              <p className="font-semibold text-slate-950">{item.name}</p>
              <p className="text-sm text-slate-500">{item.role}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default TestimonialsSection;
