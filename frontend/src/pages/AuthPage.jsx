import { useState } from "react";
import { FiEye, FiEyeOff, FiLock, FiMail, FiUser } from "react-icons/fi";
import { useLocation, useNavigate } from "react-router-dom";
import AuthButton from "../components/auth/AuthButton";
import AuthInput from "../components/auth/AuthInput";
import AuthLayout from "../components/auth/AuthLayout";
import AuthTabs from "../components/auth/AuthTabs";
import { login, setAuthSession, signup } from "../lib/apiClient";

const initial = { full_name: "", email: "", password: "" };

function AuthPage() {
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const navigate = useNavigate();
  const showLoginRequiredNote = location.state?.reason === "login_required_for_analysis";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const payload =
        mode === "signup"
          ? await signup({ full_name: form.full_name, email: form.email, password: form.password })
          : await login({ email: form.email, password: form.password });
      setAuthSession(payload.access_token, payload.user);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <h2 className="text-3xl font-semibold text-slate-950">{mode === "login" ? "Welcome Back" : "Create Your Account"}</h2>
      <p className="mt-2 text-sm text-slate-600">Access your compliance workspace with secure, role-based authentication.</p>
      {showLoginRequiredNote ? (
        <p className="mt-3 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700">
          Please log in first. Only authenticated users can access the Analyze workspace.
        </p>
      ) : null}
      <AuthTabs mode={mode} onModeChange={setMode} />

      <form className="space-y-4" onSubmit={handleSubmit} aria-label="Authentication form">
        {mode === "signup" ? (
          <AuthInput
            id="full_name"
            label="Full Name"
            type="text"
            value={form.full_name}
            onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
            placeholder="Enter your full name"
            required
            autoComplete="name"
            icon={<FiUser size={16} aria-hidden="true" />}
          />
        ) : null}
        <AuthInput
          id="email"
          label="Email Address"
          type="email"
          value={form.email}
          onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
          placeholder="you@company.com"
          required
          autoComplete="email"
          icon={<FiMail size={16} aria-hidden="true" />}
        />
        <AuthInput
          id="password"
          label="Password"
          type={showPassword ? "text" : "password"}
          value={form.password}
          onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
          placeholder="Minimum 8 characters"
          required
          minLength={8}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          icon={<FiLock size={16} aria-hidden="true" />}
          rightAction={
            <button
              type="button"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((prev) => !prev)}
              className="text-slate-500 transition hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
            </button>
          }
        />

        <div className="flex items-center justify-between gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="size-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              aria-label="Remember me"
            />
            Remember me
          </label>
          <a
            href="#"
            className="text-sm font-medium text-indigo-700 transition duration-200 hover:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            Forgot password?
          </a>
        </div>

        {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</p> : null}

        <AuthButton loading={loading} mode={mode} />
      </form>
    </AuthLayout>
  );
}

export default AuthPage;
