import { FiActivity, FiFileText, FiTarget } from "react-icons/fi";
import { flattenAnalysis, summaryFromItems } from "./dashboardUtils";

function RiskRing({ score }) {
  const normalized = Math.max(0, Math.min(100, score));
  const gradient = `conic-gradient(#4f46e5 ${normalized}%, #e2e8f0 ${normalized}% 100%)`;
  return (
    <div className="relative mx-auto grid size-28 place-items-center rounded-full" style={{ background: gradient }}>
      <div className="grid size-20 place-items-center rounded-full bg-white text-center">
        <p className="text-sm font-semibold text-slate-900">{normalized}%</p>
        <p className="text-[10px] uppercase tracking-wide text-slate-500">Compliant</p>
      </div>
    </div>
  );
}

function RightUtilityPanel({ analysisData, history, analysisInsights }) {
  const allItems = flattenAnalysis(analysisData);
  const summary = summaryFromItems(allItems);
  const latest = history[0];

  return (
    <aside className="hidden space-y-4 md:block" aria-label="Utility insights panel">
      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">Quick insights</p>
        <h3 className="mt-1 text-lg font-semibold text-slate-950">Risk Overview</h3>
        <div className="mt-3">
          <RiskRing score={summary.score} />
        </div>
        <div className="mt-3 grid gap-1 text-sm text-slate-600">
          <p className="inline-flex items-center gap-2">
            <FiActivity size={14} aria-hidden="true" />
            {summary.rejected} potential violations detected
          </p>
          <p className="inline-flex items-center gap-2">
            <FiTarget size={14} aria-hidden="true" />
            {summary.accepted} compliant findings
          </p>
        </div>
        {analysisInsights?.unresolvedFields?.length ? (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
            <p className="font-semibold">Unresolved</p>
            <p className="mt-1">{analysisInsights.unresolvedFields.join(", ")}</p>
          </div>
        ) : null}
      </section>

      <section className="border-t border-slate-200 pt-4">
        <h3 className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-600">
          <FiFileText size={14} />
          Latest report snapshot
        </h3>
        {latest ? (
          <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-semibold text-slate-900">{(latest.files || []).length} file(s)</p>
            <p className="mt-1 text-xs text-slate-500">{new Date(latest.createdAt).toLocaleString()}</p>
            <p className="mt-2 truncate text-xs text-slate-600" title={(latest.files || []).join(", ")}>
              {(latest.files || []).join(", ")}
            </p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">No report snapshot available yet.</p>
        )}
      </section>
    </aside>
  );
}

export default RightUtilityPanel;
