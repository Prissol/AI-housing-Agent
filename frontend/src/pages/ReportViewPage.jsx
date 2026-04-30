import { useEffect, useState } from "react";
import { FiDownload, FiPrinter } from "react-icons/fi";
import { Link, useParams } from "react-router-dom";
import { getToken } from "../lib/apiClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function ReportViewPage() {
  const { reportId } = useParams();
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setError("Login required to view report.");
      return;
    }
    fetch(`${API_BASE_URL}/api/reports/view/${encodeURIComponent(reportId || "")}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to load report.");
        setHtml(data.html || "");
      })
      .catch((err) => setError(err.message || "Failed to load report."));
  }, [reportId]);

  const downloadPdf = () => {
    window.print();
  };

  const printReport = () => {
    window.print();
  };

  return (
    <main className="min-h-screen bg-slate-100 p-4 sm:p-6">
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Compliance Report Preview</h1>
            <p className="text-sm text-slate-600">{reportId}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={downloadPdf}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
            >
              <FiDownload size={14} />
              Download PDF
            </button>
            <button
              type="button"
              onClick={printReport}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
            >
              <FiPrinter size={14} />
              Print Report
            </button>
            <Link to="/dashboard" className="text-sm font-semibold text-indigo-700">
              Back
            </Link>
          </div>
        </div>
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          {html ? (
            <iframe title="Report Preview" srcDoc={html} className="h-[80vh] w-full" />
          ) : (
            <div className="p-6 text-sm text-slate-500">Loading report...</div>
          )}
        </section>
      </div>
    </main>
  );
}

export default ReportViewPage;
