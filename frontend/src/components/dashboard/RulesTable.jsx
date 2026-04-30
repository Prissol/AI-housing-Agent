import { useMemo, useState } from "react";
import { FiDownload, FiFilter, FiSearch } from "react-icons/fi";
import {
  ACCEPTED_STATUS,
  REJECTED_STATUS,
  REVIEW_STATUS,
  flattenAnalysis,
  getSeverity,
  recommendationFromStatus,
  statusPillClass,
  stripYoloText,
  toReadableStatus,
} from "./dashboardUtils";

function createTableRows(data) {
  return flattenAnalysis(data).map((item, index) => {
    const details = stripYoloText(String(item.details || item.error || "No details returned."));
    const ruleTitle = item.clause_ref || details.split(/[.:]/)[0] || "By-law validation check";
    const bylawRuleId = item.rule_id || `R-${String(index + 1).padStart(3, "0")}`;
    const uniqueTraceId = item.unique_rule_trace_id || `${item.sourceRef || "SRC"}-${index + 1}`;
    let evidenceRefDisplay = "Not Provided";
    const rawEvidenceRef = item.evidence_ref ?? "Not Provided";
    if (typeof rawEvidenceRef === "string") {
      try {
        const parsed = JSON.parse(rawEvidenceRef);
        const source = parsed?.source || "unknown_source";
        const observed = parsed?.observed_value ?? "n/a";
        const required = parsed?.required_value ?? "n/a";
        evidenceRefDisplay = `${source} | observed: ${observed} | required: ${required}`;
      } catch {
        evidenceRefDisplay = rawEvidenceRef;
      }
    } else if (rawEvidenceRef && typeof rawEvidenceRef === "object") {
      const source = rawEvidenceRef?.source || "unknown_source";
      const observed = rawEvidenceRef?.observed_value ?? "n/a";
      const required = rawEvidenceRef?.required_value ?? "n/a";
      evidenceRefDisplay = `${source} | observed: ${observed} | required: ${required}`;
    }

    return {
      ruleId: bylawRuleId,
      uniqueTraceId,
      ruleTitle,
      status: item.status,
      severity: getSeverity(item.status),
      evidence: details,
      recommendation: recommendationFromStatus(item.status),
      filename: item.filename,
      expectedRequirement: item.expected_value ?? "Not Provided",
      observedValue: item.observed_value ?? "Not Provided",
      evidenceRef: evidenceRefDisplay,
    };
  });
}

function RulesTable({ data, loading, onDecisionSaved }) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("severity");
  const [decision, setDecision] = useState("");
  const [reviewerName, setReviewerName] = useState("");
  const [reviewerEmail, setReviewerEmail] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [savedDecision, setSavedDecision] = useState(null);
  const rows = useMemo(() => createTableRows(data), [data]);

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    let next = rows.filter((row) => {
      const byStatus = statusFilter === "all" ? true : row.status === statusFilter;
      if (!byStatus) return false;
      if (!normalized) return true;
      return [row.ruleId, row.ruleTitle, row.filename, row.evidence].join(" ").toLowerCase().includes(normalized);
    });

    next = [...next].sort((a, b) => {
      if (sortBy === "status") return a.status.localeCompare(b.status);
      if (sortBy === "rule") return a.ruleId.localeCompare(b.ruleId);
      const severityRank = { High: 3, Medium: 2, Low: 1 };
      return severityRank[b.severity] - severityRank[a.severity];
    });
    return next;
  }, [query, rows, sortBy, statusFilter]);

  const exportCsv = () => {
    if (!filteredRows.length) return;
    const header = ["Rule ID", "Unique Trace ID", "Rule Title", "Status", "Severity", "Expected", "Observed", "Reason", "Evidence Ref", "Recommendation"];
    const lines = filteredRows.map((row) =>
      [
        row.ruleId,
        row.uniqueTraceId,
        row.ruleTitle,
        toReadableStatus(row.status),
        row.severity,
        row.expectedRequirement,
        row.observedValue,
        row.evidence,
        row.evidenceRef,
        row.recommendation,
      ]
        .map((value) => `"${String(value).replaceAll('"', '""')}"`)
        .join(",")
    );
    const csv = [header.join(","), ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `rules-table-${Date.now()}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleDecisionToggle = (next) => {
    setDecision((prev) => (prev === next ? "" : next));
  };

  const handleSaveDecision = () => {
    if (!decision) {
      setDecisionError("Please select Accepted or Rejected.");
      return;
    }
    if (!reviewerName.trim()) {
      setDecisionError("Please enter user name.");
      return;
    }
    if (!decisionReason.trim()) {
      setDecisionError("Please enter reason for this decision.");
      return;
    }
    setDecisionError("");
    setSavedDecision({
      decision,
      reviewerName: reviewerName.trim(),
      reviewerEmail: reviewerEmail.trim(),
      decisionReason: decisionReason.trim(),
      savedAt: new Date().toLocaleString(),
    });
    onDecisionSaved?.({
      reviewer_decision: decision,
      reviewer_name: reviewerName.trim(),
      reviewer_email: reviewerEmail.trim(),
      decision_reason: decisionReason.trim(),
      decision_at: new Date().toISOString(),
    });
  };

  return (
    <section className="space-y-4 border-t border-slate-200 pt-6" aria-label="Detailed rules table">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-2xl font-semibold text-slate-950">Detailed Rule Findings</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={exportCsv}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <FiDownload size={14} aria-hidden="true" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
        <label className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2">
          <FiSearch size={14} className="text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by rule, evidence, or file"
            className="w-full border-none bg-transparent text-sm text-slate-800 outline-none"
            aria-label="Search rule rows"
          />
        </label>

        <label className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
          <FiFilter size={14} aria-hidden="true" />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="border-none bg-transparent outline-none"
            aria-label="Filter by status"
          >
            <option value="all">All statuses</option>
            <option value={ACCEPTED_STATUS}>Accepted</option>
            <option value={REJECTED_STATUS}>Rejected</option>
            <option value={REVIEW_STATUS}>Needs Review</option>
          </select>
        </label>

        <label className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
          Sort
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
            className="border-none bg-transparent outline-none"
            aria-label="Sort table rows"
          >
            <option value="severity">Severity</option>
            <option value="status">Status</option>
            <option value="rule">Rule ID</option>
          </select>
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">Rule ID</th>
              <th className="px-3 py-2">Unique ID</th>
              <th className="px-3 py-2">Rule Title</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Expected</th>
              <th className="px-3 py-2">Observed</th>
              <th className="px-3 py-2">Evidence</th>
              <th className="px-3 py-2">Evidence Ref</th>
              <th className="px-3 py-2">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <tr key={`skeleton-${index}`} className="border-t border-slate-200">
                  <td colSpan={10} className="px-3 py-3">
                    <div className="h-4 animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))
            ) : filteredRows.length ? (
              filteredRows.map((row) => (
                <tr key={row.uniqueTraceId} className="border-t border-slate-200 align-top">
                  <td className="px-3 py-2 font-semibold text-slate-900">{row.ruleId}</td>
                  <td className="px-3 py-2 text-[11px] font-medium text-slate-500">{row.uniqueTraceId}</td>
                  <td className="px-3 py-2 text-slate-800">{row.ruleTitle}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusPillClass(row.status)}`}>
                      {toReadableStatus(row.status)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-700">{row.severity}</td>
                  <td className="px-3 py-2 text-slate-700">{String(row.expectedRequirement)}</td>
                  <td className="px-3 py-2 text-slate-700">{String(row.observedValue)}</td>
                  <td className="max-w-[280px] px-3 py-2 text-slate-600">{row.evidence}</td>
                  <td
                    className="max-w-[280px] truncate whitespace-nowrap px-3 py-2 font-mono text-[11px] text-slate-500"
                    title={String(row.evidenceRef)}
                  >
                    {String(row.evidenceRef)}
                  </td>
                  <td className="max-w-[260px] px-3 py-2 text-slate-600">{row.recommendation}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={10} className="px-3 py-6 text-center text-sm text-slate-500">
                  No rows match your current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 pt-2">
        <h3 className="text-base font-semibold text-slate-900">Reviewer Decision</h3>

        <div className="flex flex-wrap items-center gap-4">
          <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={decision === ACCEPTED_STATUS}
              onChange={() => handleDecisionToggle(ACCEPTED_STATUS)}
              className="size-4 rounded border-slate-300"
            />
            Accepted
          </label>
          <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={decision === REJECTED_STATUS}
              onChange={() => handleDecisionToggle(REJECTED_STATUS)}
              className="size-4 rounded border-slate-300"
            />
            Rejected
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">User Name</span>
            <input
              type="text"
              value={reviewerName}
              onChange={(event) => setReviewerName(event.target.value)}
              placeholder="Enter reviewer name"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-400"
            />
          </label>
          <label className="space-y-1 text-sm text-slate-700">
            <span className="font-medium">User Email (optional)</span>
            <input
              type="email"
              value={reviewerEmail}
              onChange={(event) => setReviewerEmail(event.target.value)}
              placeholder="name@company.com"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-400"
            />
          </label>
        </div>

        <label className="space-y-1 text-sm text-slate-700">
          <span className="font-medium">Reason</span>
          <textarea
            value={decisionReason}
            onChange={(event) => setDecisionReason(event.target.value)}
            placeholder="Write why you accepted or rejected this result..."
            rows={3}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-400"
          />
        </label>

        {decisionError ? <p className="text-xs font-medium text-rose-600">{decisionError}</p> : null}

        <button
          type="button"
          onClick={handleSaveDecision}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          Save Decision
        </button>

        {savedDecision ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
            <p className="font-semibold">
              Decision saved: {savedDecision.decision === ACCEPTED_STATUS ? "Accepted" : "Rejected"}
            </p>
            <p className="mt-1">User: {savedDecision.reviewerName}</p>
            {savedDecision.reviewerEmail ? <p>Email: {savedDecision.reviewerEmail}</p> : null}
            <p className="mt-1">Reason: {savedDecision.decisionReason}</p>
            <p className="mt-1 text-xs text-emerald-700">Saved at: {savedDecision.savedAt}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export default RulesTable;
