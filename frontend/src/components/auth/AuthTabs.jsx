function AuthTabs({ mode, onModeChange }) {
  return (
    <div className="mb-6 grid grid-cols-2 rounded-xl border border-slate-200 bg-slate-50 p-1" role="tablist" aria-label="Auth mode">
      <button
        type="button"
        role="tab"
        aria-selected={mode === "login"}
        onClick={() => onModeChange("login")}
        className={`rounded-lg px-3 py-2 text-sm font-semibold transition duration-200 ${
          mode === "login" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
        }`}
      >
        Login
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === "signup"}
        onClick={() => onModeChange("signup")}
        className={`rounded-lg px-3 py-2 text-sm font-semibold transition duration-200 ${
          mode === "signup" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
        }`}
      >
        Sign Up
      </button>
    </div>
  );
}

export default AuthTabs;
