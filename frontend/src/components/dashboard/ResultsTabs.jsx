import { useMemo, useState } from "react";
import {
  ACCEPTED_STATUS,
  REJECTED_STATUS,
  REVIEW_STATUS,
  extractReasonLines,
  flattenAnalysis,
  recommendationFromStatus,
  statusPillClass,
  stripYoloText,
  toReadableStatus,
} from "./dashboardUtils";

const tabs = [
  { id: "summary", label: "Summary" },
  { id: "violations", label: "Violations" },
  { id: "recommendations", label: "Recommendations" },
  { id: "logs", label: "Logs / reasoning" },
];

function EntryCard({ item }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{item.filename}</p>
          <p className="text-xs text-slate-500">
            {item.sourceType} · {item.sourceRef}
          </p>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusPillClass(item.status)}`}>
          {toReadableStatus(item.status)}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-600">{stripYoloText(item.details || item.error || "No details returned.")}</p>
      {item.evidence_entity_ids || item.evidence_layers ? (
        <p className="mt-2 text-xs text-slate-500">
          Evidence refs
          {item.evidence_entity_ids ? ` | entities: ${item.evidence_entity_ids}` : ""}
          {item.evidence_layers ? ` | layers: ${item.evidence_layers}` : ""}
        </p>
      ) : null}
    </article>
  );
}

function ResultsTabs({ data, loading }) {
  const [activeTab, setActiveTab] = useState("summary");
  const allItems = useMemo(() => flattenAnalysis(data), [data]);
  const violations = allItems.filter((item) => item.status === REJECTED_STATUS);
  const review = allItems.filter((item) => item.status === REVIEW_STATUS || item.status === "Failed");

  const renderTabContent = () => {
    if (loading) {
      return (
        <div className="grid gap-2">
          <div className="h-20 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
          <div className="h-20 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
          <div className="h-20 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
        </div>
      );
    }

    if (!allItems.length) {
      return (
        <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          Analyze files to view structured findings and reasoning logs.
        </p>
      );
    }

    if (activeTab === "summary") {
      return (
        <div className="grid gap-2">
          {allItems.map((item) => (
            <EntryCard key={`${item.filename}-${item.sourceRef}`} item={item} />
          ))}
        </div>
      );
    }

    if (activeTab === "violations") {
      return (
        <div className="grid gap-2">
          {violations.length ? (
            violations.map((item) => <EntryCard key={`${item.filename}-${item.sourceRef}`} item={item} />)
          ) : (
            <p className="rounded-xl border border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-700">
              No deterministic rule failures detected in the latest run.
            </p>
          )}
        </div>
      );
    }

    if (activeTab === "recommendations") {
      return (
        <ul className="grid gap-2">
          {(review.length ? review : allItems).map((item) => (
            <li key={`${item.filename}-${item.sourceRef}`} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">{item.filename}</p>
              <p className="mt-1 text-sm text-slate-600">{recommendationFromStatus(item.status)}</p>
            </li>
          ))}
        </ul>
      );
    }

    return (
      <ul className="grid gap-2">
        {allItems.map((item) => {
          const lines = extractReasonLines({ ...item, details: stripYoloText(item.details), error: stripYoloText(item.error) });
          return (
            <li key={`${item.filename}-${item.sourceRef}`} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">{item.filename}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                {(lines.length ? lines : ["No reasoning text returned."]).map((line, index) => (
                  <li key={`${item.filename}-${index}`}>{line}</li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <section className="space-y-4 border-t border-slate-200 pt-6" aria-label="Detailed tabbed results">
      <h2 className="text-2xl font-semibold text-slate-950">Assessment Breakdown</h2>
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
              activeTab === tab.id
                ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>{renderTabContent()}</div>
    </section>
  );
}

export default ResultsTabs;
