import { FiAlertTriangle, FiCheckCircle, FiShield, FiTarget } from "react-icons/fi";
import { flattenAnalysis, summaryFromItems } from "./dashboardUtils";

function SkeletonCard() {
  return <div className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-slate-100" />;
}

function ComplianceSummaryCards({ analysisData, loading, error }) {
  const allItems = flattenAnalysis(analysisData);
  const summary = summaryFromItems(allItems);
  const confidence = allItems.length ? Math.max(60, Math.min(98, summary.score + (summary.rejected ? -5 : 4))) : 0;

  return (
    <section className="space-y-4 border-t border-slate-200 pt-6" aria-label="Compliance summary cards">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">Assessment overview</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Compliance Snapshot</h2>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : !allItems.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No compliance results yet. Upload files and run analysis to generate scorecards.
        </div>
      ) : (
        <>
          {confidence < 75 ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800">
              Needs Human Review: extraction confidence is below policy threshold.
            </div>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <article className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <FiShield size={13} aria-hidden="true" />
                Compliance Score
              </p>
              <p className="mt-2 text-3xl font-semibold text-slate-950">{summary.score}%</p>
            </article>

            <article className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-rose-700">
                <FiAlertTriangle size={13} aria-hidden="true" />
                Violations
              </p>
              <p className="mt-2 text-3xl font-semibold text-rose-800">{summary.rejected}</p>
            </article>

            <article className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
                <FiCheckCircle size={13} aria-hidden="true" />
                Needs review
              </p>
              <p className="mt-2 text-3xl font-semibold text-amber-800">{summary.review}</p>
            </article>

            <article className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4">
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                <FiTarget size={13} aria-hidden="true" />
                Confidence
              </p>
              <p className="mt-2 text-3xl font-semibold text-indigo-800">{confidence}%</p>
            </article>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
              <span>Overall compliance progress</span>
              <span>{summary.score}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-200">
              <div
                className={`h-2 rounded-full transition-all ${
                  summary.score >= 75 ? "bg-emerald-500" : summary.score >= 50 ? "bg-amber-500" : "bg-rose-500"
                }`}
                style={{ width: `${summary.score}%` }}
              />
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default ComplianceSummaryCards;
