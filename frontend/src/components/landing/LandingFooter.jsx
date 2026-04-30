function LandingFooter() {
  return (
    <footer id="contact" className="border-t border-slate-200 bg-white/80 py-12">
      <div className="section-shell grid gap-8 md:grid-cols-4">
        <section>
          <h2 className="text-lg font-semibold text-slate-950">AI Legal Maps</h2>
          <p className="mt-3 text-sm text-slate-600">
            Compliance intelligence for architecture and housing planning teams.
          </p>
        </section>

        <section>
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">Product</h3>
          <ul className="mt-3 grid gap-2 text-sm text-slate-700">
            <li><a href="#features" className="hover:text-slate-950">Features</a></li>
            <li><a href="#how-it-works" className="hover:text-slate-950">How it works</a></li>
            <li><a href="#security" className="hover:text-slate-950">Security</a></li>
          </ul>
        </section>

        <section>
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">Legal</h3>
          <ul className="mt-3 grid gap-2 text-sm text-slate-700">
            <li><a href="#security" className="hover:text-slate-950">Security</a></li>
            <li><a href="#security" className="hover:text-slate-950">Privacy policy</a></li>
            <li><a href="#security" className="hover:text-slate-950">Terms of service</a></li>
          </ul>
        </section>

        <section>
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">Contact</h3>
          <ul className="mt-3 grid gap-2 text-sm text-slate-700">
            <li>contact@ailegalmaps.com</li>
            <li>+92 300 0000000</li>
            <li>Lahore, Pakistan</li>
          </ul>
        </section>
      </div>

      <p className="section-shell mt-10 border-t border-slate-200 pt-5 text-xs text-slate-500">
        © {new Date().getFullYear()} AI Legal Maps. All rights reserved.
      </p>
    </footer>
  );
}

export default LandingFooter;
