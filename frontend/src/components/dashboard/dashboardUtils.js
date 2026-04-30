export const ACCEPTED_STATUS = "No Violation";
export const REJECTED_STATUS = "Violation";
export const REVIEW_STATUS = "Needs Review";

export function flattenAnalysis(data) {
  const images = (data?.images || []).map((item, index) => ({
    ...item,
    sourceType: "Image",
    sourceRef: `IMG-${index + 1}`,
  }));
  const pdfs = (data?.pdfs || []).map((item, index) => ({
    ...item,
    sourceType: "PDF",
    sourceRef: `PDF-${item.page || index + 1}`,
  }));
  const excels = (data?.excels || []).map((item, index) => ({
    ...item,
    sourceType: "Spreadsheet",
    sourceRef: `ROW-${item.row || index + 1}`,
  }));
  return [...images, ...pdfs, ...excels];
}

export function toReadableStatus(status) {
  if (status === "Failed") return "Needs Review";
  if (status === REJECTED_STATUS) return "Rejected";
  if (status === ACCEPTED_STATUS) return "Accepted";
  if (status === REVIEW_STATUS) return "Needs Review";
  return "Needs Review";
}

export function statusPillClass(status) {
  if (status === "Failed") return "bg-amber-50 text-amber-700 border-amber-200";
  if (status === REJECTED_STATUS) return "bg-rose-50 text-rose-700 border-rose-200";
  if (status === ACCEPTED_STATUS) return "bg-emerald-50 text-emerald-700 border-emerald-200";
  return "bg-amber-50 text-amber-700 border-amber-200";
}

export function getSeverity(status) {
  if (status === REJECTED_STATUS) return "High";
  if (status === REVIEW_STATUS || status === "Failed") return "Medium";
  return "Low";
}

export function scoreFromItems(items) {
  if (!items.length) return 0;
  const accepted = items.filter((item) => item.status === ACCEPTED_STATUS).length;
  return Math.round((accepted / items.length) * 100);
}

export function summaryFromItems(items) {
  const accepted = items.filter((item) => item.status === ACCEPTED_STATUS).length;
  const rejected = items.filter((item) => item.status === REJECTED_STATUS).length;
  const review = items.filter((item) => item.status === REVIEW_STATUS || item.status === "Failed").length;
  return {
    total: items.length,
    accepted,
    rejected,
    review,
    score: scoreFromItems(items),
  };
}

export function extractReasonLines(entry) {
  const rawText = String(entry?.error || entry?.details || "");
  if (!rawText.trim()) return [];
  if (rawText.includes("\n")) {
    return rawText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }
  return rawText
    .split(/[.;]+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function recommendationFromStatus(status) {
  if (status === REJECTED_STATUS) return "Review cited clause and revise map dimensions before resubmission.";
  if (status === REVIEW_STATUS) return "Provide clearer evidence or rerun with higher quality source.";
  return "Proceed to approval and keep this result in the audit record.";
}

export function fileTypeFromName(fileName) {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".png")) return "image";
  if (lower.endsWith(".pdf")) return "pdf";
  if (lower.endsWith(".dwg") || lower.endsWith(".dxf")) return "cad";
  if (lower.endsWith(".xlsx") || lower.endsWith(".csv")) return "sheet";
  return "other";
}

export function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

export function stripYoloText(input) {
  const text = String(input || "");
  if (!text) return "";
  let cleaned = text;
  cleaned = cleaned.replace(/architecture signals[^.]*\./gi, "");
  cleaned = cleaned.replace(/model source[^.]*\./gi, "");
  cleaned = cleaned.replace(/fallback generic model/gi, "");
  cleaned = cleaned.replace(/\s{2,}/g, " ").trim();
  return cleaned;
}
