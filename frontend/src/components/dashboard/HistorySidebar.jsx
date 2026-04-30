import { FiClock, FiSearch, FiTrash2, FiX } from "react-icons/fi";

function HistorySidebar({
  open,
  history,
  filteredHistory,
  historyQuery,
  onHistoryQueryChange,
  historyStats,
  activeHistoryId,
  onOpenHistoryItem,
  onClearHistory,
  onClose,
}) {
  const getEntrySummary = (entry) => {
    const allItems = [
      ...(entry.analysis?.images || []),
      ...(entry.analysis?.pdfs || []),
      ...(entry.analysis?.excels || []),
    ];
    const accepted = allItems.filter((item) => item.status === "No Violation").length;
    const rejected = allItems.filter((item) => item.status === "Violation").length;
    return { total: allItems.length, accepted, rejected };
  };

  return (
    <aside
      className={`transition md:sticky md:top-24 md:max-h-[calc(100vh-7rem)] md:overflow-y-auto md:pr-4 md:border-r md:border-slate-200 ${
        open ? "block" : "hidden md:block"
      }`}
      aria-label="Analysis history"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-950">History</h2>
        <div className="flex items-center gap-2">
          {history.length ? (
            <button
              type="button"
              onClick={onClearHistory}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <FiTrash2 size={12} aria-hidden="true" />
              Clear
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 p-1.5 text-slate-700 md:hidden"
            aria-label="Close history sidebar"
          >
            <FiX size={14} />
          </button>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-2">
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Total</p>
          <p className="mt-1 text-xl font-semibold text-slate-950">{historyStats.total}</p>
        </div>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700">Accepted</p>
          <p className="mt-1 text-xl font-semibold text-emerald-800">{historyStats.accepted}</p>
        </div>
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700">Rejected</p>
          <p className="mt-1 text-xl font-semibold text-rose-800">{historyStats.rejected}</p>
        </div>
      </div>

      <label className="mb-4 flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2">
        <FiSearch size={14} className="text-slate-400" aria-hidden="true" />
        <input
          value={historyQuery}
          onChange={(event) => onHistoryQueryChange(event.target.value)}
          placeholder="Search by file or status"
          className="w-full border-none bg-transparent text-sm text-slate-800 outline-none"
          aria-label="Search history"
        />
      </label>

      <div className="grid gap-0 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {!filteredHistory.length ? (
          <div className="p-4 text-sm text-slate-500">
            No analyses yet. Run your first compliance check to populate history.
          </div>
        ) : (
          filteredHistory.map((item) => {
            const summary = getEntrySummary(item);
            const hasRejection = summary.rejected > 0;
            return (
              <button
                type="button"
                key={item.id}
                onClick={() => onOpenHistoryItem(item)}
                className={`p-3 text-left transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                  activeHistoryId === item.id
                    ? "bg-indigo-50"
                    : "bg-white"
                }`}
              >
                <p className="inline-flex items-center gap-1 text-xs text-slate-500">
                  <FiClock size={12} aria-hidden="true" />
                  {new Date(item.createdAt).toLocaleString()}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{summary.total} file(s) analyzed</p>
                <span
                  className={`mt-2 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                    hasRejection
                      ? "border-rose-200 bg-rose-50 text-rose-700"
                      : "border-emerald-200 bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {hasRejection ? "Needs Attention" : "Compliant"}
                </span>
                <p className="mt-1 truncate text-xs text-slate-500" title={(item.files || []).join(", ")}>
                  {(item.files || []).join(", ")}
                </p>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}

export default HistorySidebar;
