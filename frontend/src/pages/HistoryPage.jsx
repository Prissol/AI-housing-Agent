import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchMyChatLogs,
  fetchMyHistory,
  fetchMyReportMetadata,
  fetchRecordByAnalysis,
  fetchRecordByReport,
  fetchRecordBySession,
  fetchRecordByUser,
} from "../lib/apiClient";

function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [chatLogs, setChatLogs] = useState([]);
  const [reportMeta, setReportMeta] = useState([]);
  const [lookupType, setLookupType] = useState("analysis");
  const [lookupValue, setLookupValue] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const run = async () => {
      try {
        const [h, c, r] = await Promise.all([fetchMyHistory(), fetchMyChatLogs(), fetchMyReportMetadata()]);
        setHistory(h.items || []);
        setChatLogs(c.items || []);
        setReportMeta(r.items || []);
      } catch (err) {
        setError(err.message || "Failed loading history records.");
      }
    };
    run();
  }, []);

  const runLookup = async () => {
    if (!lookupValue.trim()) return;
    setError("");
    try {
      let result;
      if (lookupType === "analysis") result = await fetchRecordByAnalysis(lookupValue.trim());
      else if (lookupType === "report") result = await fetchRecordByReport(lookupValue.trim());
      else if (lookupType === "session") result = await fetchRecordBySession(lookupValue.trim());
      else result = await fetchRecordByUser(lookupValue.trim());
      setLookupResult(result);
    } catch (err) {
      setError(err.message || "Lookup failed.");
      setLookupResult(null);
    }
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-slate-950">History & Records</h1>
          <Link to="/dashboard" className="text-sm font-semibold text-indigo-700">
            Back to Dashboard
          </Link>
        </div>

        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">ID-wise Search</h2>
          <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
            <select
              value={lookupType}
              onChange={(e) => setLookupType(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="analysis">analysis_id</option>
              <option value="report">report_id</option>
              <option value="session">session_id</option>
              <option value="user">user_id/email</option>
            </select>
            <input
              type="text"
              value={lookupValue}
              onChange={(e) => setLookupValue(e.target.value)}
              placeholder="Enter ID"
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <button onClick={runLookup} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
              Search
            </button>
          </div>
          {lookupResult ? (
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800">
              {JSON.stringify(lookupResult, null, 2)}
            </pre>
          ) : null}
        </section>

        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Analysis History</h2>
          <div className="space-y-2">
            {history.map((item) => (
              <div key={item.analysis_id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <p className="font-semibold">{item.file_name}</p>
                <p className="text-slate-600">
                  {item.analysis_id} · {item.status} · violations: {item.violations_count}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Chat Logs</h2>
          <div className="space-y-2">
            {chatLogs.map((item) => (
              <div key={item.session_id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <p className="font-semibold">{item.session_id}</p>
                <p className="text-slate-600">messages: {(item.messages || []).length}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Report Metadata</h2>
          <div className="space-y-2">
            {reportMeta.map((item) => (
              <div key={item.report_id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <p className="font-semibold">{item.report_name}</p>
                <p className="text-slate-600">
                  {item.report_id} · {item.report_type} · {item.status}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

export default HistoryPage;
