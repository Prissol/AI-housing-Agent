import { useEffect, useMemo, useState } from "react";
import { FiFileText, FiImage, FiPaperclip, FiUploadCloud, FiX } from "react-icons/fi";
import { fileTypeFromName, formatBytes } from "./dashboardUtils";

const supportedTypes = ["DWG", "DXF", "PDF", "PNG", "JPG", "XLSX", "CSV"];

function UploadCard({
  files,
  fileAreaTypes,
  fileRotations,
  onFileAreaTypeChange,
  onFileRotationChange,
  onFilesChange,
  onAnalyze,
  loading,
  progressLabel,
  analysisStatus,
  confidenceOverall,
}) {
  const [dragActive, setDragActive] = useState(false);
  const [expandedImage, setExpandedImage] = useState(null);
  const [previewRotation, setPreviewRotation] = useState(0);
  const getFileKey = (file) => `${file.name}-${file.size}-${file.lastModified}`;
  const fileItems = useMemo(
    () =>
      files.map((file) => {
        const type = fileTypeFromName(file.name);
        return {
          file,
          type,
          previewUrl: type === "image" ? URL.createObjectURL(file) : "",
        };
      }),
    [files]
  );

  useEffect(
    () => () => {
      fileItems.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
    },
    [fileItems]
  );

  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);
    const droppedFiles = Array.from(event.dataTransfer.files || []);
    if (droppedFiles.length) onFilesChange(droppedFiles);
  };

  const removeFile = (target) => {
    onFilesChange(files.filter((file) => !(file.name === target.name && file.size === target.size)));
  };

  const replaceFiles = (event) => {
    const picked = Array.from(event.target.files || []);
    onFilesChange(picked);
  };

  const totalSize = files.reduce((acc, file) => acc + file.size, 0);
  const stages = ["CAD Parse", "Normalize", "Rule Check", "Report"];
  const normalizedProgress = String(progressLabel || "").toLowerCase();
  const activeStage = (() => {
    if (analysisStatus === "NEEDS_CLARIFICATION") return 2;
    if (!loading && normalizedProgress.includes("completed")) return 3;
    if (normalizedProgress.includes("compliance")) return 2;
    if (normalizedProgress.includes("extract")) return 1;
    if (normalizedProgress.includes("cad")) return 0;
    return -1;
  })();

  return (
    <section className="space-y-4" aria-label="Compliance file upload">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-700">Upload</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Compliance Analysis Workspace</h2>
          <p className="mt-1 text-sm text-slate-600">Drop project files to run by-law checks and generate structured findings.</p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Confidence</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {confidenceOverall == null ? "N/A" : `${Math.round(Number(confidenceOverall) * 100)}%`}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {supportedTypes.map((type) => (
            <span key={type} className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600">
              {type}
            </span>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Processing stages</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-4">
          {stages.map((stage, index) => (
            <div
              key={stage}
              className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold ${
                activeStage >= index
                  ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-slate-50 text-slate-500"
              }`}
            >
              {stage}
            </div>
          ))}
        </div>
      </div>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        aria-label="Drag and drop files area"
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
          dragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50"
        }`}
      >
        <div className="mx-auto grid size-12 place-items-center rounded-full bg-white text-slate-700 shadow-sm">
          <FiUploadCloud size={20} aria-hidden="true" />
        </div>
        <p className="mt-3 text-base font-semibold text-slate-900">Drag & drop map files here</p>
        <p className="mt-1 text-sm text-slate-500">Supports DWG, DXF, PDF, PNG, JPG, XLSX, CSV (max recommended batch: 25 files)</p>
        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:shadow-sm">
          <FiPaperclip size={14} aria-hidden="true" />
          Select Files
          <input
            type="file"
            multiple
            accept=".dwg,.dxf,.jpg,.jpeg,.png,.pdf,.xlsx,.csv"
            onChange={replaceFiles}
            className="hidden"
            aria-label="Select files"
          />
        </label>
      </div>

      <div className="border-t border-slate-200 pt-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-semibold text-slate-800">Selected Files ({files.length})</p>
          <p className="text-xs text-slate-500">Total size: {formatBytes(totalSize)}</p>
        </div>

        {!files.length ? (
          <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">
            No files selected yet. Add site plans, compliance sheets, and supporting documents to begin.
          </p>
        ) : (
          <ul className="grid gap-0 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
            {fileItems.map(({ file, type, previewUrl }) => {
              return (
                <li key={`${file.name}-${file.size}`} className="flex items-start justify-between gap-3 px-3 py-3">
                  <div className="flex min-w-0 items-start gap-3">
                    {type === "image" && previewUrl ? (
                      <button
                        type="button"
                        onClick={() => {
                          setExpandedImage({ name: file.name, previewUrl, file });
                          const key = `${file.name}-${file.size}-${file.lastModified}`;
                          setPreviewRotation(Number(fileRotations?.[key] || 0));
                        }}
                        className="shrink-0 rounded-lg border border-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                        aria-label={`Expand preview for ${file.name}`}
                        title="Click to expand image"
                      >
                        <img
                          src={previewUrl}
                          alt={file.name}
                            className="size-10 rounded-lg object-cover transition hover:opacity-90"
                            style={{
                              transform: `rotate(${Number(fileRotations?.[getFileKey(file)] || 0)}deg)`,
                            }}
                        />
                      </button>
                    ) : (
                      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white text-slate-600">
                        {type === "image" ? <FiImage size={15} /> : <FiFileText size={15} />}
                      </span>
                    )}
                    <div className="min-w-0 space-y-2">
                      <p className="truncate text-sm font-semibold text-slate-900">{file.name}</p>
                      <p className="text-xs font-medium text-slate-500">{formatBytes(file.size)}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-lg border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-xs font-bold text-cyan-900">
                          Saved Rotation: {Number(fileRotations?.[getFileKey(file)] || 0)}°
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <button
                      type="button"
                      onClick={() => removeFile(file)}
                      aria-label={`Remove ${file.name}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                    >
                      <FiX size={12} aria-hidden="true" />
                      Remove
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {!!files.length && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-700">Bylaw Category</p>
          <p className="mb-2 text-xs text-slate-500">Set category for each uploaded file (image, PDF, or spreadsheet).</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {fileItems.map(({ file, type }) => (
              <div
                key={`area-${file.name}-${file.size}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                <p className="max-w-[70%] truncate text-xs font-semibold text-slate-800">
                  {type === "image" ? "Image" : type === "cad" ? "CAD" : "File"}: {file.name}
                </p>
                <select
                  value={fileAreaTypes?.[getFileKey(file)] || "residential"}
                  onChange={(event) => onFileAreaTypeChange(file, event.target.value)}
                  className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-900"
                  aria-label={`Select bylaw category for ${file.name}`}
                >
                  <option value="residential">Residential</option>
                  <option value="commercial">Commercial</option>
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={loading || !files.length}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2"
        >
          {loading ? "Running analysis..." : "Run Compliance Analysis"}
        </button>
        {loading ? <p className="text-sm font-medium text-indigo-700">{progressLabel || "Preparing analysis..."}</p> : null}
      </div>
      {loading && progressLabel?.includes("CAD") ? (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs text-indigo-700">
          CAD Processing to Extraction to Compliance Check
        </div>
      ) : null}

      {expandedImage ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Expanded uploaded image preview"
          className="fixed inset-0 z-[100] grid place-items-center bg-slate-950/85 p-4"
          onClick={() => {
            setExpandedImage(null);
            setPreviewRotation(0);
          }}
        >
          <div
            className="w-full max-w-6xl rounded-xl border border-slate-700 bg-slate-900 p-3"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="truncate text-sm font-semibold text-slate-100">{expandedImage.name}</p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPreviewRotation((value) => value - 90)}
                  className="rounded-lg border border-slate-600 px-2.5 py-1 text-xs font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Rotate Left
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewRotation((value) => value + 90)}
                  className="rounded-lg border border-slate-600 px-2.5 py-1 text-xs font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Rotate Right
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewRotation(0)}
                  className="rounded-lg border border-slate-600 px-2.5 py-1 text-xs font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!expandedImage?.file) return;
                    const normalizedRotation = ((previewRotation % 360) + 360) % 360;
                    const snapped = Math.round(normalizedRotation / 90) * 90;
                    onFileRotationChange(expandedImage.file, snapped);
                    setExpandedImage(null);
                    setPreviewRotation(0);
                  }}
                  className="rounded-lg border border-emerald-600 px-2.5 py-1 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-900/30"
                >
                  Save Rotation
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setExpandedImage(null);
                    setPreviewRotation(0);
                  }}
                  className="rounded-lg border border-slate-600 px-2.5 py-1 text-xs font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="max-h-[80vh] overflow-auto rounded-lg bg-slate-950 p-1">
              <img
                src={expandedImage.previewUrl}
                alt={expandedImage.name}
                className="mx-auto h-auto max-h-[78vh] w-auto max-w-full rounded-md object-contain transition-transform duration-200"
                style={{ transform: `rotate(${previewRotation}deg)` }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default UploadCard;
