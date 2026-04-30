function AuthButton({ loading, mode }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
      aria-label={mode === "login" ? "Log in" : "Create account"}
    >
      {loading ? "Please wait..." : mode === "login" ? "Log In" : "Create Account"}
    </button>
  );
}

export default AuthButton;
