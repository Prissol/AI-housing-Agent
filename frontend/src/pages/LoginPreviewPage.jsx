import { useMemo, useState } from "react";
import { FiArrowLeft, FiEye, FiEyeOff, FiLayers, FiLoader, FiLock } from "react-icons/fi";
import { Link } from "react-router-dom";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const initialState = {
  email: "",
  password: "",
  rememberMe: false,
};

function LoginPreviewPage() {
  const [formData, setFormData] = useState(initialState);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");

  const errors = useMemo(() => {
    const next = { email: "", password: "" };
    if (!formData.email.trim()) {
      next.email = "Email is required.";
    } else if (!EMAIL_REGEX.test(formData.email.trim())) {
      next.email = "Please enter a valid email address.";
    }

    if (!formData.password) {
      next.password = "Password is required.";
    } else if (formData.password.length < 8) {
      next.password = "Password must be at least 8 characters.";
    }
    return next;
  }, [formData.email, formData.password]);

  const isFormValid = !errors.email && !errors.password;

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    setSubmitError("");
    setSubmitSuccess("");
  };

  const handleBlur = (event) => {
    const { name } = event.target;
    if (name === "email" || name === "password") {
      setTouched((prev) => ({ ...prev, [name]: true }));
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setTouched({ email: true, password: true });
    setSubmitError("");
    setSubmitSuccess("");

    if (!isFormValid) {
      return;
    }

    setIsSubmitting(true);
    try {
      await new Promise((resolve) => {
        setTimeout(resolve, 1100);
      });
      setSubmitSuccess("Signed in successfully. Redirecting to your compliance workspace...");
    } catch {
      setSubmitError("Unable to sign in right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-100 via-white to-cyan-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl gap-6 overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_22px_60px_rgba(15,23,42,0.16)] backdrop-blur-md lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative flex flex-col justify-between overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 p-8 text-white sm:p-10">
          <div className="absolute -left-16 -top-16 size-48 rounded-full bg-cyan-400/20 blur-3xl" aria-hidden="true" />
          <div className="absolute bottom-0 right-0 size-56 rounded-full bg-indigo-400/20 blur-3xl" aria-hidden="true" />

          <div className="relative">
            <Link
              to="/"
              className="mb-8 inline-flex items-center gap-2 rounded-xl border border-white/25 bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:-translate-y-0.5 hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <FiArrowLeft size={14} aria-hidden="true" />
              Back to Home
            </Link>

            <div className="inline-flex items-center gap-3 rounded-2xl border border-white/20 bg-white/10 px-4 py-3 backdrop-blur">
              <span className="grid size-9 place-items-center rounded-xl bg-white/90 text-slate-900">
                <FiLayers size={16} aria-hidden="true" />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.15em] text-cyan-300">AI Legal Maps</p>
                <p className="text-sm font-medium text-slate-100">Compliance Intelligence</p>
              </div>
            </div>

            <h1 className="mt-8 max-w-md text-3xl font-semibold leading-tight sm:text-4xl">
              Compliance decisions for maps, powered by AI.
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-200">
              Bring legal clarity to map reviews with rule-grounded analysis, transparent findings, and audit-ready workflows.
            </p>
          </div>

          <div className="relative mt-10 rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.12em] text-cyan-300">Trusted workflow</p>
            <p className="mt-2 text-sm text-slate-100">Used by architecture and planning teams for consistent by-law validation.</p>
          </div>
        </section>

        <section className="flex items-center justify-center p-6 sm:p-10">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-8">
            <h2 className="text-3xl font-semibold text-slate-950">Welcome Back</h2>
            <p className="mt-2 text-sm text-slate-600">Sign in to continue your compliance workflow</p>

            <form className="mt-7 space-y-4" onSubmit={handleSubmit} noValidate aria-label="Login form">
              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-700">
                  Email address
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  autoComplete="email"
                  aria-label="Email address"
                  aria-invalid={touched.email && Boolean(errors.email)}
                  aria-describedby={touched.email && errors.email ? "email-error" : undefined}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20"
                  placeholder="you@company.com"
                />
                {touched.email && errors.email ? (
                  <p id="email-error" className="mt-1.5 text-xs font-medium text-rose-600">
                    {errors.email}
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-slate-700">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    autoComplete="current-password"
                    aria-label="Password"
                    aria-invalid={touched.password && Boolean(errors.password)}
                    aria-describedby={touched.password && errors.password ? "password-error" : undefined}
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20"
                    placeholder="Minimum 8 characters"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute inset-y-0 right-0 grid w-12 place-items-center text-slate-500 transition hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                  >
                    {showPassword ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                  </button>
                </div>
                {touched.password && errors.password ? (
                  <p id="password-error" className="mt-1.5 text-xs font-medium text-rose-600">
                    {errors.password}
                  </p>
                ) : null}
              </div>

              <div className="flex items-center justify-between gap-3">
                <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                  <input
                    name="rememberMe"
                    type="checkbox"
                    checked={formData.rememberMe}
                    onChange={handleChange}
                    aria-label="Remember me"
                    className="size-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Remember me
                </label>
                <a
                  href="#"
                  className="text-sm font-medium text-indigo-700 transition hover:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                >
                  Forgot password?
                </a>
              </div>

              {submitError ? (
                <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{submitError}</p>
              ) : null}

              {submitSuccess ? (
                <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700">
                  {submitSuccess}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={!isFormValid || isSubmitting}
                aria-label="Log in"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
              >
                {isSubmitting ? <FiLoader className="animate-spin" size={16} aria-hidden="true" /> : <FiLock size={16} aria-hidden="true" />}
                {isSubmitting ? "Signing in..." : "Log In"}
              </button>

              <div className="relative py-1">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <span className="w-full border-t border-slate-200" />
                </div>
                <span className="relative mx-auto block w-fit bg-white px-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-400">
                  or
                </span>
              </div>

              <button
                type="button"
                aria-label="Continue with Google"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
              >
                <span className="text-base" aria-hidden="true">G</span>
                Continue with Google
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-600">
              Don&apos;t have an account?{" "}
              <a
                href="#"
                className="font-semibold text-indigo-700 transition hover:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
              >
                Sign up
              </a>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

export default LoginPreviewPage;
