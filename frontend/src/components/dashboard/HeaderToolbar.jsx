import { FiArrowLeft, FiDownload, FiMoon, FiPlay, FiSun, FiUser } from "react-icons/fi";
import { Link } from "react-router-dom";

function HeaderToolbar({
  canAnalyze,
  onAnalyze,
  onDownload,
  analyzeLoading,
  darkMode,
  onToggleTheme,
  onToggleSidebar,
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div className="dashboard-shell flex flex-wrap items-center justify-between gap-3 py-4">
        <div className="min-w-[220px]">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">AI Legal Maps Dashboard</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 sm:text-3xl">Compliance Analysis Workspace</h1>
          <p className="mt-1 text-sm text-slate-600">Workspace: DHA Housing Compliance Team</p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={onAnalyze}
            disabled={!canAnalyze || analyzeLoading}
            aria-label="Run compliance analysis"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
          >
            <FiPlay size={14} aria-hidden="true" />
            {analyzeLoading ? "Analyzing..." : "Analyze"}
          </button>

          <button
            type="button"
            onClick={onDownload}
            aria-label="Download report"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            <FiDownload size={14} aria-hidden="true" />
            Download Report
          </button>

          <button
            type="button"
            onClick={onToggleTheme}
            aria-label="Toggle theme"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            {darkMode ? <FiSun size={14} aria-hidden="true" /> : <FiMoon size={14} aria-hidden="true" />}
            {darkMode ? "Light" : "Dark"}
          </button>

          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle history sidebar"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 transition md:hidden"
          >
            History
          </button>

          <div
            className="grid size-10 place-items-center rounded-full border border-slate-300 bg-white text-slate-700"
            aria-label="Profile menu placeholder"
            role="button"
            tabIndex={0}
          >
            <FiUser size={16} aria-hidden="true" />
          </div>

          <Link
            to="/history"
            className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 transition hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            History
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 transition hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            <FiArrowLeft size={13} aria-hidden="true" />
            Back to Landing
          </Link>
        </div>
      </div>
    </header>
  );
}

export default HeaderToolbar;
