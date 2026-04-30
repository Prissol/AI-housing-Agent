import { trustLogos } from "./landingData";

function TrustBar() {
  return (
    <section className="section-shell pb-14">
      <div className="glass-panel rounded-2xl px-6 py-5">
        <p className="text-center text-sm font-semibold tracking-wide text-slate-700">
          Built for architects, planners, and compliance teams
        </p>
        <div className="mt-4 grid gap-2 text-center sm:grid-cols-2 lg:grid-cols-5">
          {trustLogos.map((logo) => (
            <p
              key={logo}
              className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
            >
              {logo}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}

export default TrustBar;
