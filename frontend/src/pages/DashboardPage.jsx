import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import BylawChatCard from "../components/dashboard/BylawChatCard";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import HeaderToolbar from "../components/dashboard/HeaderToolbar";
import HistorySidebar from "../components/dashboard/HistorySidebar";
import ResultsTabs from "../components/dashboard/ResultsTabs";
import RightUtilityPanel from "../components/dashboard/RightUtilityPanel";
import RulesTable from "../components/dashboard/RulesTable";
import UploadCard from "../components/dashboard/UploadCard";
import {
  ACCEPTED_STATUS,
  REJECTED_STATUS,
  REVIEW_STATUS,
  flattenAnalysis,
  stripYoloText,
} from "../components/dashboard/dashboardUtils";
import { fetchMyHistory, getToken } from "../lib/apiClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const HISTORY_STORAGE_KEY = "dha_ai_maps_history_v2";

function DashboardPage() {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [fileAreaTypes, setFileAreaTypes] = useState({});
  const [fileRotations, setFileRotations] = useState({});
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState({ images: [], pdfs: [], excels: [] });
  const [analyzeError, setAnalyzeError] = useState("");
  const [progressLabel, setProgressLabel] = useState("");
  const [history, setHistory] = useState([]);
  const [historyQuery, setHistoryQuery] = useState("");
  const [activeHistoryId, setActiveHistoryId] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState("READY_FOR_DECISION");
  const [clarificationQuestions, setClarificationQuestions] = useState([]);
  const [clarificationAnswers, setClarificationAnswers] = useState({});
  const [activeAnalysisId, setActiveAnalysisId] = useState("");

  const [question, setQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Welcome to AI Legal Maps. Ask any DHA Multan bylaw question." },
  ]);
  const [reviewerDecision, setReviewerDecision] = useState(null);
  const [analysisInsights, setAnalysisInsights] = useState({
    confidenceOverall: null,
    confidenceScores: {},
    unresolvedFields: [],
    sourceMode: "",
    unitsDetected: [],
    failureReasonCode: "",
  });

  const mapRuleResultsToRows = (ruleResults, fallbackFileName, analysisId, confidenceValue) => {
    if (Array.isArray(ruleResults) && ruleResults.length) {
      return ruleResults.map((rule, idx) => {
        const evidence = rule?.evidence || {};
        const entityIds = Array.isArray(evidence.entity_ids)
          ? evidence.entity_ids
          : Array.isArray(evidence.evidence_points)
            ? evidence.evidence_points.map((point) => point?.entity_id).filter(Boolean)
            : [];
        const layers = Array.isArray(evidence.layers)
          ? evidence.layers
          : Array.isArray(evidence.evidence_points)
            ? evidence.evidence_points.map((point) => point?.layer).filter(Boolean)
            : [];
        return {
          filename: fallbackFileName || "Uploaded file",
          status: rule.status === "fail" ? REJECTED_STATUS : rule.status === "pass" ? ACCEPTED_STATUS : REVIEW_STATUS,
          details: stripYoloText(`${rule.rule_id}: ${rule.reason}`),
          confidence: confidenceValue ?? null,
          rule_id: rule.rule_id || "Not Provided",
          clause_ref: rule.clause_ref || "Not Provided",
          expected_value: rule?.expected ?? rule?.evidence?.required_value ?? "Not Provided",
          observed_value: rule?.observed ?? rule?.evidence?.observed_value ?? "Not Provided",
          evidence_ref: JSON.stringify(rule?.evidence || {}),
          evidence_entity_ids: entityIds.join(", "),
          evidence_layers: layers.join(", "),
          unique_rule_trace_id: `${analysisId || "NA"}-${rule.rule_id || "RULE"}-${idx + 1}`,
        };
      });
    }
    return [
      {
        filename: fallbackFileName || "Uploaded file",
        status: REVIEW_STATUS,
        details: "No deterministic rule evidence returned by analyzer.",
        confidence: confidenceValue ?? null,
        rule_id: "Not Provided",
        clause_ref: "Not Provided",
        expected_value: "Not Provided",
        observed_value: "Not Provided",
        evidence_ref: "Not Provided",
        unique_rule_trace_id: `${analysisId || "NA"}-NO-RULE-1`,
      },
    ];
  };

  const mapHistoryApiItem = (item) => {
    const rejected = Number(item?.violations_count || 0);
    const accepted = Number(item?.non_violations_count || 0);
    const review = Math.max(0, 1 - rejected - accepted);
    const synthesizedRows = [
      ...Array.from({ length: rejected }).map((_, idx) => ({
        filename: item?.file_name || "Uploaded file",
        status: REJECTED_STATUS,
        details: "Loaded from history summary. Open this item to view full rule findings.",
        unique_rule_trace_id: `${item?.analysis_id || "NA"}-HIST-REJ-${idx + 1}`,
      })),
      ...Array.from({ length: accepted }).map((_, idx) => ({
        filename: item?.file_name || "Uploaded file",
        status: ACCEPTED_STATUS,
        details: "Loaded from history summary. Open this item to view full rule findings.",
        unique_rule_trace_id: `${item?.analysis_id || "NA"}-HIST-ACC-${idx + 1}`,
      })),
      ...Array.from({ length: review }).map((_, idx) => ({
        filename: item?.file_name || "Uploaded file",
        status: REVIEW_STATUS,
        details: "Loaded from history summary. Open this item to view full rule findings.",
        unique_rule_trace_id: `${item?.analysis_id || "NA"}-HIST-REV-${idx + 1}`,
      })),
    ];
    return {
      id: item?.analysis_id || `${Date.now()}`,
      analysisId: item?.analysis_id || "",
      createdAt: item?.created_at || new Date().toISOString(),
      files: [item?.file_name || "Uploaded file"],
      analysis: { images: synthesizedRows, pdfs: [], excels: [] },
      hydrated: false,
    };
  };

  const updateInsightsFromResponse = (data) => {
    const extracted = data?.extracted_data || {};
    const confidenceScores = extracted?.confidence_scores || {};
    const fallbackConfidence = extracted?.confidence || {};
    const derivedOverall =
      confidenceScores?.overall ??
      (Object.values(fallbackConfidence).length
        ? Object.values(fallbackConfidence).reduce((acc, value) => acc + Number(value || 0), 0) / Object.values(fallbackConfidence).length
        : null);
    const unresolved = Array.isArray(extracted?.unresolved_fields)
      ? extracted.unresolved_fields
      : Array.isArray(data?.what_is_unclear)
        ? data.what_is_unclear
        : [];
    setAnalysisInsights({
      confidenceOverall: Number.isFinite(Number(derivedOverall)) ? Number(derivedOverall) : null,
      confidenceScores: confidenceScores || {},
      unresolvedFields: unresolved,
      sourceMode: extracted?.meta?.source_mode || "",
      unitsDetected: Array.isArray(extracted?.units_detected) ? extracted.units_detected : [],
      failureReasonCode: data?.failure_reason_code || "",
    });
  };

  useEffect(() => {
    const saved = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) setHistory(parsed);
    } catch (error) {
      console.error("History parse error:", error);
    }
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    let cancelled = false;
    fetchMyHistory("?skip=0&limit=50")
      .then((payload) => {
        if (cancelled) return;
        const items = Array.isArray(payload?.items) ? payload.items : [];
        if (!items.length) return;
        const mapped = items.map(mapHistoryApiItem);
        setHistory(mapped);
        setActiveHistoryId(mapped[0]?.id || null);
      })
      .catch(() => {
        // Keep local history fallback if API history cannot be loaded.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  const allAnalyzedItems = useMemo(() => flattenAnalysis(analysisData), [analysisData]);
  const buildFileKey = (file) => `${file.name}-${file.size}-${file.lastModified}`;

  const handleFilesChange = (nextFiles) => {
    setSelectedFiles(nextFiles);
    setFileAreaTypes((previous) => {
      const nextMap = {};
      nextFiles.forEach((file) => {
        const key = buildFileKey(file);
        nextMap[key] = previous[key] || "residential";
      });
      return nextMap;
    });
    setFileRotations((previous) => {
      const nextMap = {};
      nextFiles.forEach((file) => {
        const key = buildFileKey(file);
        nextMap[key] = Number(previous[key] || 0);
      });
      return nextMap;
    });
  };

  const handleFileAreaTypeChange = (file, areaType) => {
    const key = buildFileKey(file);
    setFileAreaTypes((previous) => ({ ...previous, [key]: areaType }));
  };

  const handleFileRotationChange = (file, rotationDeg) => {
    const key = buildFileKey(file);
    setFileRotations((previous) => ({ ...previous, [key]: Number(rotationDeg || 0) }));
  };

  const filteredHistory = useMemo(() => {
    const query = historyQuery.trim().toLowerCase();
    if (!query) return history;
    return history.filter((item) => {
      const fileNames = (item.files || []).join(" ").toLowerCase();
      const statuses = flattenAnalysis(item.analysis)
        .map((resultItem) => resultItem.status || "")
        .join(" ")
        .toLowerCase();
      return fileNames.includes(query) || statuses.includes(query);
    });
  }, [history, historyQuery]);

  const historyStats = useMemo(() => {
    const allItems = history.flatMap((entry) => flattenAnalysis(entry.analysis));
    return {
      total: allItems.length,
      accepted: allItems.filter((item) => item.status === ACCEPTED_STATUS).length,
      rejected: allItems.filter((item) => item.status === REJECTED_STATUS).length,
    };
  }, [history]);

  const buildChatContext = () => {
    const entries = allAnalyzedItems.slice(0, 5).map((item, index) => {
      const cleanedDetails = String(item.details || "").replace(/\s+/g, " ").trim();
      return `${index + 1}) File: ${item.filename} | Status: ${item.status} | Details: ${cleanedDetails}`;
    });
    return [
      "Latest analyzed files context:",
      ...(entries.length ? entries : ["No analyzed files available in current session."]),
      "Object-detection layer disabled in this workspace.",
    ].join("\n");
  };

  const handleAnalyze = async () => {
    setAnalyzeError("");
    setAnalysisData({ images: [], pdfs: [], excels: [] });
    setAnalysisInsights({
      confidenceOverall: null,
      confidenceScores: {},
      unresolvedFields: [],
      sourceMode: "",
      unitsDetected: [],
      failureReasonCode: "",
    });
    setAnalysisStatus("READY_FOR_DECISION");
    setClarificationQuestions([]);
    setClarificationAnswers({});
    setActiveAnalysisId("");
    if (!selectedFiles.length) {
      setAnalyzeError("Please upload at least one file.");
      return;
    }

    try {
      const token = getToken();
      const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
      setAnalyzeLoading(true);
      setProgressLabel(`Processing ${selectedFiles.length} files...`);
      const rows = [];
      let latestAnalysisId = "";
      let shouldUseLegacyAnalyzeFiles = false;
      for (const file of selectedFiles) {
        const fileType = file.name.toLowerCase().endsWith(".dwg") || file.name.toLowerCase().endsWith(".dxf") ? "cad" : "default";
        if (fileType === "cad") {
          setProgressLabel(`CAD Processing: ${file.name}`);
        } else {
          setProgressLabel(`Extraction: ${file.name}`);
        }
        const formData = new FormData();
        formData.append("file", file);
        const manualRotation = Number(fileRotations[buildFileKey(file)] || 0);
        formData.append("manual_rotation_deg", String(manualRotation));
        const areaType = fileAreaTypes[buildFileKey(file)] || "residential";
        const profileId = areaType === "commercial" ? "dha_commercial" : "dha_residential";
        const analyzeEndpoint = token ? "/api/analyze" : "/analyze";
        const response = await fetch(`${API_BASE_URL}${analyzeEndpoint}?bylaw_profile_id=${encodeURIComponent(profileId)}`, {
          method: "POST",
          headers: authHeaders,
          body: formData,
        });

        if (response.status === 404) {
          shouldUseLegacyAnalyzeFiles = true;
          break;
        }

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Analysis failed for ${file.name}`);
        updateInsightsFromResponse(data);
        latestAnalysisId = data.analysis_id || latestAnalysisId;
        setActiveAnalysisId(data.analysis_id || "");
        if (data.status === "NEEDS_CLARIFICATION") {
          setAnalysisStatus("NEEDS_CLARIFICATION");
          const questions = Array.isArray(data.questions_for_user) ? data.questions_for_user : [];
          setClarificationQuestions(questions);
          const placeholderRows = [
            {
              filename: file.name,
              status: REVIEW_STATUS,
              details: "Awaiting your input. More details required before compliance decision.",
              confidence: 0,
            },
          ];
          setAnalysisData({ images: placeholderRows, pdfs: [], excels: [] });
          return;
        }
        setAnalysisStatus("READY_FOR_DECISION");
        setProgressLabel(`Compliance Check: ${file.name}`);
        const ruleResults = Array.isArray(data.rule_results) ? data.rule_results : [];
        rows.push(
          ...mapRuleResultsToRows(
            ruleResults,
            file.name,
            data.analysis_id,
            data.extracted_data?.confidence?.dimensions ?? null
          )
        );
      }

      if (shouldUseLegacyAnalyzeFiles) {
        const batchFormData = new FormData();
        selectedFiles.forEach((file) => batchFormData.append("files", file));
        const legacyResponse = await fetch(`${API_BASE_URL}/analyze-files`, { method: "POST", body: batchFormData });
        const legacyData = await legacyResponse.json();
        if (!legacyResponse.ok) throw new Error(legacyData.detail || "File analysis failed.");
        const legacyRows = [
          ...(Array.isArray(legacyData.images) ? legacyData.images : []),
          ...(Array.isArray(legacyData.pdfs) ? legacyData.pdfs : []),
          ...(Array.isArray(legacyData.excels) ? legacyData.excels : []),
        ].map((item) => ({ ...item, details: stripYoloText(item.details), error: stripYoloText(item.error) }));
        rows.length = 0;
        rows.push(...legacyRows);
      }

      const unified = { images: rows, pdfs: [], excels: [] };
      setAnalysisData(unified);
      setActiveAnalysisId(latestAnalysisId);

      const historyEntry = {
        id: latestAnalysisId || `${Date.now()}`,
        analysisId: latestAnalysisId || "",
        createdAt: new Date().toISOString(),
        files: selectedFiles.map((file) => file.name),
        analysis: unified,
        hydrated: true,
      };
      setHistory((previous) => [historyEntry, ...previous].slice(0, 40));
      setActiveHistoryId(historyEntry.id);
      setProgressLabel(`Completed ${selectedFiles.length} files`);

      // Object-detection layer intentionally disabled.
    } catch (error) {
      const raw = error.message || "Something went wrong during analysis.";
      const message = raw.includes("Unsupported DWG version")
        ? "Unsupported DWG version. Please convert and re-upload."
        : raw.includes("CAD conversion failed")
          ? "CAD conversion failed. Verify converter path and try again."
          : raw.includes("Needs Human Review")
            ? "CAD parser confidence low -> Needs Human Review."
            : raw;
      setAnalyzeError(message);
      setProgressLabel("");
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const handleClarificationSubmit = async () => {
    if (!activeAnalysisId || !clarificationQuestions.length) return;
    try {
      const token = getToken();
      setAnalyzeLoading(true);
      const answers = clarificationQuestions
        .map((q) => ({ question_id: q.question_id, answer: (clarificationAnswers[q.question_id] || "").trim() }))
        .filter((item) => item.answer);
      if (!answers.length) {
        setAnalyzeError("Please answer at least one clarification question.");
        return;
      }
      const clarifyEndpoint = token ? "/api/analysis" : "/analysis";
      const response = await fetch(`${API_BASE_URL}${clarifyEndpoint}/${activeAnalysisId}/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ answers }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to submit clarifications.");
      updateInsightsFromResponse(data);
      if (data.status === "NEEDS_CLARIFICATION") {
        setAnalysisStatus("NEEDS_CLARIFICATION");
        setClarificationQuestions(Array.isArray(data.questions_for_user) ? data.questions_for_user : []);
        setAnalyzeError("");
        return;
      }
      const ruleResults = Array.isArray(data.rule_results) ? data.rule_results : [];
      const clarifiedRows = mapRuleResultsToRows(
        ruleResults,
        selectedFiles[0]?.name || "Clarified file",
        data.analysis_id || activeAnalysisId,
        data.extracted_data?.confidence?.dimensions ?? null
      );
      setAnalysisData({ images: clarifiedRows, pdfs: [], excels: [] });
      setAnalysisStatus("READY_FOR_DECISION");
      setClarificationQuestions([]);
      setClarificationAnswers({});
      setAnalyzeError("");
    } catch (error) {
      setAnalyzeError(error.message || "Failed to submit clarifications.");
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const sendQuestion = async () => {
    const cleaned = question.trim();
    if (!cleaned) return;
    setMessages((previous) => [...previous, { role: "user", text: cleaned }]);
    setQuestion("");
    setChatError("");
    try {
      const token = getToken();
      const chatEndpoint = token ? "/api/chat" : "/chat";
      setChatLoading(true);
      const response = await fetch(`${API_BASE_URL}${chatEndpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ query: cleaned, context: buildChatContext() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Chat request failed.");
      setMessages((previous) => [...previous, { role: "assistant", text: data.response }]);
    } catch (error) {
      setChatError(error.message || "Unable to get chatbot response.");
    } finally {
      setChatLoading(false);
    }
  };

  const openHistoryItem = async (item) => {
    setActiveHistoryId(item.id);
    setAnalyzeError("");
    setMobileSidebarOpen(false);
    setActiveAnalysisId(item.analysisId || item.id || "");
    if (item.hydrated) {
      setAnalysisData(item.analysis || { images: [], pdfs: [], excels: [] });
      return;
    }
    const token = getToken();
    const analysisId = item.analysisId || item.id;
    if (!token || !analysisId) {
      setAnalysisData(item.analysis || { images: [], pdfs: [], excels: [] });
      return;
    }
    try {
      setAnalyzeLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/analysis/${encodeURIComponent(analysisId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Unable to open history analysis.");
      updateInsightsFromResponse(payload);
      const hydratedRows = mapRuleResultsToRows(
        payload.rule_results || [],
        item.files?.[0] || "Uploaded file",
        payload.analysis_id || analysisId,
        payload.extracted_data?.confidence?.dimensions ?? null
      );
      const hydratedItem = { ...item, analysis: { images: hydratedRows, pdfs: [], excels: [] }, hydrated: true };
      setAnalysisData(hydratedItem.analysis);
      setHistory((previous) => previous.map((entry) => (entry.id === item.id ? hydratedItem : entry)));
    } catch (error) {
      setAnalyzeError(error.message || "Failed to open selected history item.");
      setAnalysisData(item.analysis || { images: [], pdfs: [], excels: [] });
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const clearHistory = () => {
    setHistory([]);
    setActiveHistoryId(null);
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  };

  const handleDownloadReport = () => {
    if (!allAnalyzedItems.length || !activeAnalysisId) {
      setAnalyzeError("Analyze at least one file before downloading report.");
      return;
    }
    const token = getToken();
    if (!token) {
      setAnalyzeError("Please login first to generate professional report.");
      return;
    }
    const primary = allAnalyzedItems[0] || {};
    fetch(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        analysis_id: activeAnalysisId,
        file_name: primary.filename || "Not Provided",
        plot_type: (fileAreaTypes[buildFileKey(selectedFiles[0] || {})] || "residential").toLowerCase(),
        uploaded_by: "Not Provided",
        uploaded_at: new Date().toISOString(),
        project_name: "Not Provided",
        client_name: "Not Provided",
        ...reviewerDecision,
      }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to generate report.");
        navigate(`/reports/${data.report_id}`);
      })
      .catch((err) => setAnalyzeError(err.message || "Failed to generate report."));
  };

  return (
    <div className={darkMode ? "dashboard-dark min-h-screen bg-slate-950 pb-24" : "min-h-screen bg-slate-100 pb-24"}>
      <HeaderToolbar
        canAnalyze={selectedFiles.length > 0}
        onAnalyze={handleAnalyze}
        onDownload={handleDownloadReport}
        analyzeLoading={analyzeLoading}
        darkMode={darkMode}
        onToggleTheme={() => setDarkMode((previous) => !previous)}
        onToggleSidebar={() => setMobileSidebarOpen((previous) => !previous)}
      />

      <DashboardLayout
        sidebar={
          <HistorySidebar
            open={mobileSidebarOpen}
            history={history}
            filteredHistory={filteredHistory}
            historyQuery={historyQuery}
            onHistoryQueryChange={setHistoryQuery}
            historyStats={historyStats}
            activeHistoryId={activeHistoryId}
            onOpenHistoryItem={openHistoryItem}
            onClearHistory={clearHistory}
            onClose={() => setMobileSidebarOpen(false)}
          />
        }
        main={
          <>
            <UploadCard
              files={selectedFiles}
              fileAreaTypes={fileAreaTypes}
              fileRotations={fileRotations}
              onFileAreaTypeChange={handleFileAreaTypeChange}
              onFileRotationChange={handleFileRotationChange}
              onFilesChange={handleFilesChange}
              onAnalyze={handleAnalyze}
              loading={analyzeLoading}
              progressLabel={progressLabel}
              analysisStatus={analysisStatus}
              confidenceOverall={analysisInsights.confidenceOverall}
            />

            {analyzeError ? (
              <section className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <p>{analyzeError}</p>
                <button
                  type="button"
                  onClick={handleAnalyze}
                  className="mt-2 rounded-md border border-rose-300 px-3 py-1.5 text-xs font-semibold"
                >
                  Retry analysis
                </button>
              </section>
            ) : null}

            {analysisStatus === "NEEDS_CLARIFICATION" ? (
              <section className="glass-panel space-y-4 rounded-2xl border border-indigo-200 bg-gradient-to-b from-indigo-50/70 to-white px-5 py-4 text-sm text-slate-800">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-semibold text-slate-900">Clarification Required</p>
                    <p className="mt-1 text-xs text-slate-600">
                      Please answer only the unclear points so final compliance decision can be completed.
                    </p>
                  </div>
                  <span className="rounded-full border border-indigo-200 bg-indigo-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-700">
                    Needs Clarification
                  </span>
                </div>
                <div className="space-y-2">
                  {clarificationQuestions.map((question) => (
                    <label key={question.question_id} className="block">
                      <span className="mb-1 block text-xs font-semibold text-slate-800">{question.question}</span>
                      <input
                        type="text"
                        value={clarificationAnswers[question.question_id] || ""}
                        onChange={(event) =>
                          setClarificationAnswers((prev) => ({ ...prev, [question.question_id]: event.target.value }))
                        }
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-200/70"
                      />
                    </label>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={handleClarificationSubmit}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800"
                >
                  Submit Clarifications
                </button>
              </section>
            ) : null}

            {analysisInsights.unresolvedFields.length ? (
              <section className="rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Unresolved fields</p>
                <p className="mt-1 text-sm">
                  {analysisInsights.unresolvedFields.join(", ")}
                  {analysisInsights.failureReasonCode ? ` | reason code: ${analysisInsights.failureReasonCode}` : ""}
                </p>
              </section>
            ) : null}

            <BylawChatCard
              messages={messages}
              question={question}
              onQuestionChange={setQuestion}
              onSend={sendQuestion}
              chatLoading={chatLoading}
              chatError={chatError}
            />
            <ResultsTabs data={analysisData} loading={analyzeLoading} />
            <RulesTable data={analysisData} loading={analyzeLoading} onDecisionSaved={setReviewerDecision} />
          </>
        }
        utility={<RightUtilityPanel analysisData={analysisData} history={history} analysisInsights={analysisInsights} />}
      />

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-300 bg-white/90 p-3 backdrop-blur md:hidden">
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={analyzeLoading || !selectedFiles.length}
          className="w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {analyzeLoading ? "Running analysis..." : "Run Compliance Analysis"}
        </button>
      </div>
    </div>
  );
}

export default DashboardPage;
