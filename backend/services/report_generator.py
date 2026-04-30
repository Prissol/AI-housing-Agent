from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe(value: Any) -> str:
    if value is None:
        return "Not Provided"
    text = str(value).strip()
    return text if text else "Not Provided"


def _status_badge(status: str) -> tuple[str, str]:
    normalized = (status or "").upper()
    if "ACCEPT" in normalized or normalized == "READY_FOR_DECISION":
        return "Accepted", "badge-green"
    if "REJECT" in normalized:
        return "Rejected", "badge-red"
    return "Needs Review", "badge-amber"


def build_report_json(
    *,
    report_id: str,
    analysis_id: str,
    analysis_payload: dict[str, Any],
    report_input: dict[str, Any],
    generated_by: str,
    app_env: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    rule_results = analysis_payload.get("rule_results", []) or []
    summary = analysis_payload.get("summary", {}) or {}
    status_text, _ = _status_badge(str(report_input.get("reviewer_decision") or analysis_payload.get("status") or ""))

    clarification_questions = list(analysis_payload.get("questions_for_user", []) or [])
    clarifications = list(report_input.get("clarifications", []) or [])
    return {
        "report_id": report_id,
        "analysis_id": analysis_id,
        "version": str(report_input.get("version") or "1.0"),
        "generated_at": now.isoformat(),
        "timezone": "UTC",
        "generated_by": _safe(generated_by),
        "environment": _safe(app_env),
        "header": {
            "product_name": "AI Legal Maps",
            "title": "Compliance Analysis Report",
            "confidential": True,
        },
        "property_info": {
            "plot_id": _safe(report_input.get("plot_id")),
            "property_id": _safe(report_input.get("property_id")),
            "project_name": _safe(report_input.get("project_name")),
            "client_name": _safe(report_input.get("client_name")),
            "file_name": _safe(report_input.get("file_name")),
            "location": _safe(report_input.get("location")),
            "plot_type": _safe(report_input.get("plot_type")),
            "uploaded_by": _safe(report_input.get("uploaded_by")),
            "uploaded_at": _safe(report_input.get("uploaded_at")),
        },
        "analysis_summary": {
            "overall_status": status_text,
            "compliance_score": _safe(report_input.get("compliance_score")),
            "total_checks_run": int(summary.get("total_rules", 0) or 0),
            "passed_checks_count": int(summary.get("passed", 0) or 0),
            "failed_checks_count": int(summary.get("failed", 0) or 0),
            "needs_clarification_count": len(clarification_questions),
        },
        "decision_reviewer": {
            "final_decision": _safe(report_input.get("reviewer_decision")),
            "reviewer_name": _safe(report_input.get("reviewer_name")),
            "reviewer_role": _safe(report_input.get("reviewer_role")),
            "decision_datetime": _safe(report_input.get("decision_at")),
            "approval_rejection_note": _safe(report_input.get("decision_reason")),
            "digital_signature_placeholder": f"{_safe(report_input.get('reviewer_name'))} @ {_safe(report_input.get('decision_at'))}",
        },
        "findings": [
            {
                "rule_clause_id": _safe(item.get("rule_id")),
                "rule_title": _safe(item.get("clause_ref")),
                "expected_requirement": _safe(item.get("evidence", {}).get("required_value")),
                "observed_value": _safe(item.get("evidence", {}).get("observed_value")),
                "status": _safe(item.get("status")),
                "severity": _safe(report_input.get("severity_map", {}).get(item.get("rule_id")) or "Medium"),
                "reason": _safe(item.get("reason")),
                "evidence_reference": _safe(item.get("evidence")),
            }
            for item in rule_results
        ],
        "clarifications": {
            "what_was_unclear": list(analysis_payload.get("what_is_unclear", []) or []),
            "questions_asked": clarification_questions,
            "user_responses": clarifications,
            "final_resolved_value": _safe(report_input.get("final_resolved_value")),
        },
        "recommendation": {
            "required_corrections": _safe(report_input.get("required_corrections")),
            "next_action": _safe(report_input.get("next_action")),
            "resubmission_checklist": list(report_input.get("resubmission_checklist", []) or ["Not Provided"]),
        },
        "footer": {
            "report_id": report_id,
            "generated_by_system": "AI Legal Maps",
            "environment": _safe(app_env),
            "legal_disclaimer": "This report is generated for compliance assistance. Final approvals remain subject to competent authority review.",
        },
    }


def render_report_html(report: dict[str, Any], logo_path: str = "/multan-logo.png") -> str:
    status_text = _safe(report["analysis_summary"].get("overall_status"))
    _, badge_class = _status_badge(status_text)
    findings_rows = "\n".join(
        f"""
        <tr>
          <td>{_safe(item.get('rule_clause_id'))}</td>
          <td>{_safe(item.get('rule_title'))}</td>
          <td>{_safe(item.get('expected_requirement'))}</td>
          <td>{_safe(item.get('observed_value'))}</td>
          <td>{_safe(item.get('status'))}</td>
          <td>{_safe(item.get('severity'))}</td>
          <td>{_safe(item.get('reason'))}</td>
          <td>{_safe(item.get('evidence_reference'))}</td>
        </tr>
        """
        for item in report.get("findings", [])
    ) or "<tr><td colspan='8'>Not Provided</td></tr>"

    q_items = report.get("clarifications", {}).get("questions_asked", [])
    q_html = "".join(f"<li>{_safe(q.get('question'))}</li>" for q in q_items) or "<li>Not Provided</li>"
    r_items = report.get("clarifications", {}).get("user_responses", [])
    r_html = "".join(
        f"<li>{_safe(r.get('question_id'))}: {_safe(r.get('answer'))}</li>" if isinstance(r, dict) else f"<li>{_safe(r)}</li>"
        for r in r_items
    ) or "<li>Not Provided</li>"
    checklist = report.get("recommendation", {}).get("resubmission_checklist", []) or ["Not Provided"]
    checklist_html = "".join(f"<li>{_safe(item)}</li>" for item in checklist)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>{_safe(report.get("report_id"))} - Compliance Analysis Report</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  body {{ font-family: Inter, Arial, sans-serif; color: #0f172a; margin: 0; background: #f8fafc; }}
  .page {{ max-width: 980px; margin: 0 auto; background: #fff; padding: 18px; }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #e2e8f0; padding-bottom:12px; }}
  .head-left {{ display:flex; gap:12px; align-items:center; }}
  .logo {{ width:56px; height:56px; object-fit:contain; border-radius:8px; border:1px solid #e2e8f0; padding:4px; }}
  .title {{ font-size:22px; font-weight:700; margin:0; }}
  .subtitle {{ font-size:12px; color:#475569; margin-top:4px; }}
  .tag {{ font-size:11px; font-weight:700; color:#b91c1c; border:1px solid #fecaca; background:#fef2f2; padding:4px 8px; border-radius:999px; }}
  .meta {{ font-size:12px; line-height:1.6; text-align:right; color:#334155; }}
  .section {{ border:1px solid #e2e8f0; border-radius:12px; margin-top:14px; overflow:hidden; }}
  .section h3 {{ margin:0; padding:10px 12px; font-size:14px; letter-spacing:.02em; text-transform:uppercase; background:#f8fafc; border-bottom:1px solid #e2e8f0; }}
  .section .content {{ padding:12px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:10px 20px; font-size:13px; }}
  .summary {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
  .card {{ border:1px solid #e2e8f0; border-radius:10px; padding:10px; background:#fff; }}
  .k {{ font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; }}
  .v {{ font-size:18px; font-weight:700; margin-top:4px; }}
  .badge-green {{ background:#dcfce7; color:#166534; border:1px solid #86efac; }}
  .badge-red {{ background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; }}
  .badge-amber {{ background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }}
  .badge {{ display:inline-flex; padding:5px 10px; border-radius:999px; font-size:12px; font-weight:700; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ border:1px solid #e2e8f0; padding:7px; vertical-align:top; text-align:left; }}
  th {{ background:#f8fafc; font-size:11px; text-transform:uppercase; color:#475569; }}
  ul {{ margin:0; padding-left:18px; }}
  .footer {{ border-top:1px solid #e2e8f0; margin-top:16px; padding-top:8px; font-size:11px; color:#64748b; display:flex; justify-content:space-between; }}
</style>
</head>
<body>
<div class="page">
  <header class="head">
    <div class="head-left">
      <img class="logo" src="{logo_path}" alt="logo" />
      <div>
        <p class="title">{_safe(report["header"].get("product_name"))} - Compliance Analysis Report</p>
        <p class="subtitle">Enterprise Compliance Output</p>
      </div>
    </div>
    <div>
      <div class="tag">Confidential</div>
      <div class="meta">
        <div><b>Report ID:</b> {_safe(report.get("report_id"))}</div>
        <div><b>Analysis ID:</b> {_safe(report.get("analysis_id"))}</div>
        <div><b>Version:</b> {_safe(report.get("version"))}</div>
        <div><b>Generated:</b> {_safe(report.get("generated_at"))}</div>
        <div><b>Timezone:</b> {_safe(report.get("timezone"))}</div>
      </div>
    </div>
  </header>

  <section class="section"><h3>Property / Plot Information</h3><div class="content grid2">
    <div><b>Plot ID:</b> {_safe(report["property_info"].get("plot_id"))}</div>
    <div><b>Property ID:</b> {_safe(report["property_info"].get("property_id"))}</div>
    <div><b>Project / Client:</b> {_safe(report["property_info"].get("project_name"))} / {_safe(report["property_info"].get("client_name"))}</div>
    <div><b>File Name:</b> {_safe(report["property_info"].get("file_name"))}</div>
    <div><b>Location:</b> {_safe(report["property_info"].get("location"))}</div>
    <div><b>Plot Type:</b> {_safe(report["property_info"].get("plot_type"))}</div>
    <div><b>Uploaded By:</b> {_safe(report["property_info"].get("uploaded_by"))}</div>
    <div><b>Uploaded At:</b> {_safe(report["property_info"].get("uploaded_at"))}</div>
  </div></section>

  <section class="section"><h3>Analysis Summary</h3><div class="content">
    <div class="summary">
      <div class="card"><div class="k">Overall status</div><div class="v"><span class="badge {badge_class}">{status_text}</span></div></div>
      <div class="card"><div class="k">Compliance score</div><div class="v">{_safe(report["analysis_summary"].get("compliance_score"))}</div></div>
      <div class="card"><div class="k">Checks run</div><div class="v">{_safe(report["analysis_summary"].get("total_checks_run"))}</div></div>
      <div class="card"><div class="k">Passed</div><div class="v">{_safe(report["analysis_summary"].get("passed_checks_count"))}</div></div>
      <div class="card"><div class="k">Failed</div><div class="v">{_safe(report["analysis_summary"].get("failed_checks_count"))}</div></div>
      <div class="card"><div class="k">Needs clarification</div><div class="v">{_safe(report["analysis_summary"].get("needs_clarification_count"))}</div></div>
    </div>
  </div></section>

  <section class="section"><h3>Decision & Reviewer Details</h3><div class="content grid2">
    <div><b>Final Decision:</b> {_safe(report["decision_reviewer"].get("final_decision"))}</div>
    <div><b>Reviewer:</b> {_safe(report["decision_reviewer"].get("reviewer_name"))}</div>
    <div><b>Reviewer Role:</b> {_safe(report["decision_reviewer"].get("reviewer_role"))}</div>
    <div><b>Decision Time:</b> {_safe(report["decision_reviewer"].get("decision_datetime"))}</div>
    <div style="grid-column:1/-1;"><b>Note:</b> {_safe(report["decision_reviewer"].get("approval_rejection_note"))}</div>
    <div style="grid-column:1/-1;"><b>Digital Signature Placeholder:</b> {_safe(report["decision_reviewer"].get("digital_signature_placeholder"))}</div>
  </div></section>

  <section class="section"><h3>Findings Table (Detailed)</h3><div class="content">
    <table>
      <thead><tr><th>Rule/Clause ID</th><th>Rule Title</th><th>Expected</th><th>Observed</th><th>Status</th><th>Severity</th><th>Reason</th><th>Evidence Ref</th></tr></thead>
      <tbody>{findings_rows}</tbody>
    </table>
  </div></section>

  <section class="section"><h3>Clarifications</h3><div class="content grid2">
    <div><b>What was unclear</b><ul>{"".join(f"<li>{_safe(item)}</li>" for item in report.get("clarifications", {}).get("what_was_unclear", []) or ["Not Provided"])}</ul></div>
    <div><b>Questions asked</b><ul>{q_html}</ul></div>
    <div><b>User responses</b><ul>{r_html}</ul></div>
    <div><b>Final resolved value</b><div>{_safe(report.get("clarifications", {}).get("final_resolved_value"))}</div></div>
  </div></section>

  <section class="section"><h3>Recommendation Block</h3><div class="content">
    <p><b>Required corrections:</b> {_safe(report.get("recommendation", {}).get("required_corrections"))}</p>
    <p><b>Suggested next action:</b> {_safe(report.get("recommendation", {}).get("next_action"))}</p>
    <p><b>Resubmission checklist:</b></p><ul>{checklist_html}</ul>
  </div></section>

  <footer class="footer">
    <div>Report ID: {_safe(report.get("report_id"))} | Generated by: {_safe(report.get("generated_by"))} ({_safe(report.get("environment"))})</div>
    <div>Page 1</div>
  </footer>
  <p style="margin-top:8px;font-size:10px;color:#94a3b8;">{_safe(report.get("footer", {}).get("legal_disclaimer"))}</p>
</div>
</body>
</html>
"""


def write_report_files(report_json: dict[str, Any], html: str, reports_dir: Path) -> tuple[str, str]:
    report_id = str(report_json["report_id"])
    json_path = reports_dir / f"{report_id}.document.json"
    html_path = reports_dir / f"{report_id}.html"
    json_path.write_text(__import__("json").dumps(report_json, indent=2), encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return str(json_path), str(html_path)
