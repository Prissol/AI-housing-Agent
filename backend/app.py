from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import get_settings
from core.logger import configure_logging, get_logger
from db.mongo import (
    analysis_history_collection,
    as_jsonable,
    bylaw_clauses_collection,
    bylaw_sets_collection,
    chat_logs_collection,
    ensure_indexes,
    report_metadata_collection,
    users_collection,
    utcnow,
)
from pipeline.orchestrator import persist_analysis, run_pipeline_for_file
from rules.bylaw_repository import ensure_bylaw_profiles_seeded
from schemas.report import AnalysisReport
from services.auth_service import authenticate_user, create_user, decode_token, issue_token
from services.groq_service import generate_bylaw_answer
from services.report_generator import build_report_json, render_report_html, write_report_files
from services.storage import ensure_output_dirs, save_upload_temp
from storage.clarifications_store import load_clarification_state, merge_answers, save_clarification_state

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000)
    context: str = Field(default="", max_length=6000)


class ChatResponse(BaseModel):
    response: str


class ClarificationAnswer(BaseModel):
    question_id: str = Field(..., min_length=2, max_length=120)
    answer: str = Field(..., min_length=1, max_length=1000)


class ClarifyRequest(BaseModel):
    answers: list[ClarificationAnswer] = Field(default_factory=list)


class SignUpRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    role: str = Field(default="user", max_length=32)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=200)
    password: str = Field(..., min_length=8, max_length=200)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ChatLogUpsertRequest(BaseModel):
    session_id: str = Field(..., min_length=2, max_length=200)
    analysis_id: str | None = None
    messages: list[dict] = Field(default_factory=list)
    ended: bool = False


class ReportMetaCreateRequest(BaseModel):
    analysis_id: str = Field(..., min_length=6, max_length=128)
    report_type: str = Field(..., min_length=2, max_length=80)
    report_name: str = Field(..., min_length=2, max_length=200)
    storage_path: str = Field(..., min_length=2, max_length=500)
    version: str = Field(default="1.0", max_length=40)
    status: str = Field(default="generated", max_length=40)


class ReportGenerateRequest(BaseModel):
    analysis_id: str = Field(..., min_length=6, max_length=128)
    plot_id: str | None = None
    property_id: str | None = None
    project_name: str | None = None
    client_name: str | None = None
    file_name: str | None = None
    location: str | None = None
    plot_type: str | None = None
    uploaded_by: str | None = None
    uploaded_at: str | None = None
    reviewer_name: str | None = None
    reviewer_role: str | None = None
    reviewer_decision: str | None = None
    decision_reason: str | None = None
    decision_at: str | None = None
    final_resolved_value: str | None = None
    required_corrections: str | None = None
    next_action: str | None = None
    resubmission_checklist: list[str] = Field(default_factory=list)
    clarifications: list[dict] = Field(default_factory=list)
    compliance_score: str | None = None
    version: str = "1.0"


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".xlsx", ".csv", ".dwg", ".dxf"}


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format.")
    return parts[1].strip()


def _get_current_user(authorization: str | None) -> dict:
    token = _extract_bearer_token(authorization)
    try:
        claims = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc
    user = users_collection().find_one({"email": claims.get("email", "").lower(), "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
    return as_jsonable(user) or {}


def _persist_analysis_history(
    *,
    analysis_id: str,
    file: UploadFile,
    ext: str,
    bylaw_profile_id: str | None,
    report: AnalysisReport,
    user_id: str | None,
) -> None:
    now = utcnow()
    rule_results = list(report.rule_results or [])
    violations_count = len([item for item in rule_results if item.status == "fail"])
    non_violations_count = len([item for item in rule_results if item.status == "pass"])
    payload = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "file_name": file.filename or "unknown",
        "file_type": ext.lstrip(".") or "unknown",
        "file_size": getattr(file, "size", 0) or 0,
        "preprocess_meta": report.extracted_data.get("meta", {}),
        "ocr_meta": {"ocr_blocks_count": len(report.extracted_data.get("ocr_blocks", []))},
        "extraction_confidence": report.extracted_data.get("confidence", {}),
        "status": str(report.status).lower(),
        "failure_reason_code": str(report.failure_reason_code or ""),
        "diagnostics": report.diagnostics or {},
        "violations_count": violations_count,
        "non_violations_count": non_violations_count,
        "bylaw_set_id": bylaw_profile_id or "default",
        "created_at": now,
        "updated_at": now,
    }
    analysis_history_collection().update_one({"analysis_id": analysis_id}, {"$set": payload}, upsert=True)


def _raise_pipeline_http_error(exc: Exception) -> None:
    detail = str(exc)
    if "BYLAW_SOURCE_MISSING" in detail:
        raise HTTPException(status_code=422, detail="BYLAW_SOURCE_MISSING: Active bylaw set/clauses not found.") from exc
    if "RULE_MAPPING_ERROR" in detail:
        raise HTTPException(status_code=422, detail=detail) from exc
    if "max size" in detail.lower():
        raise HTTPException(status_code=413, detail=detail) from exc
    if "converter not found" in detail.lower():
        raise HTTPException(
            status_code=500,
            detail="CAD conversion failed. DWG converter not found. Set DWG_CONVERTER_PATH.",
        ) from exc
    if "Unsupported DWG version" in detail:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported DWG version. {detail}",
        ) from exc
    if "conversion failed" in detail.lower():
        raise HTTPException(
            status_code=500,
            detail=f"CAD conversion failed. {detail}",
        ) from exc
    if "Parser confidence low" in detail:
        raise HTTPException(status_code=422, detail="Parser confidence low -> Needs Human Review.") from exc
    raise HTTPException(status_code=500, detail="Failed to analyze file. Check OCR/OpenAI/CAD configuration.") from exc


@app.on_event("startup")
async def startup_event() -> None:
    ensure_output_dirs()
    ensure_indexes()
    ensure_bylaw_profiles_seeded()
    if not settings.openai_api_key.strip():
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it in backend/.env before starting this service."
        )
    logger.info("Startup validation passed.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.query.strip()
    context = payload.context.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    # Ask-before-answer behavior for weak/ambiguous prompts.
    if len(question) < 8:
        return ChatResponse(
            response=(
                "I need one more detail before answering: are you asking about stair width, exit width, corridor width, "
                "room area, or height/setback? Please specify clause/topic and file type."
            )
        )
    if "No analyzed files available in current session." in context:
        return ChatResponse(
            response=(
                "I cannot infer bylaws without analysis context. Please upload and analyze a file first, then ask your question "
                "with clause/topic (e.g., stair width, corridor width, plot setback)."
            )
        )
    try:
        answer = generate_bylaw_answer(question=question, context=context)
        return ChatResponse(response=answer)
    except Exception as exc:  # pragma: no cover - endpoint safety
        logger.exception("Chat endpoint failed: %s", exc)
        raise HTTPException(status_code=502, detail="Unable to fetch chatbot response right now.") from exc


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(payload: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    _get_current_user(authorization)
    return chat(payload)


@app.post("/analyze", response_model=AnalysisReport)
async def analyze(
    file: UploadFile = File(...),
    manual_rotation_deg: float = Form(default=0),
    bylaw_profile_id: str | None = None,
) -> AnalysisReport:
    analysis_id = uuid4().hex
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or 'unknown'}")
    try:
        temp_path = await save_upload_temp(file, analysis_id)
        report = run_pipeline_for_file(
            temp_path,
            bylaw_profile_id=bylaw_profile_id,
            analysis_id=analysis_id,
            manual_rotation_deg=manual_rotation_deg,
        )
        save_clarification_state(
            analysis_id,
            {
                "analysis_id": analysis_id,
                "source_file_path": str(temp_path),
                "bylaw_profile_id": bylaw_profile_id,
                "answers": {},
            },
        )
        extracted_path = settings.extracted_dir / f"{analysis_id}.json"
        report_path = settings.reports_dir / f"{analysis_id}.json"
        persist_analysis(report, extracted_path, report_path)
        _persist_analysis_history(
            analysis_id=analysis_id,
            file=file,
            ext=ext,
            bylaw_profile_id=bylaw_profile_id,
            report=report,
            user_id=None,
        )
        return report
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive endpoint safety
        logger.exception("Analyze pipeline failed for %s: %s", file.filename, exc)
        _raise_pipeline_http_error(exc)


@app.post("/analysis/{analysis_id}/clarify", response_model=AnalysisReport)
def clarify_analysis(analysis_id: str, payload: ClarifyRequest) -> AnalysisReport:
    state = load_clarification_state(analysis_id)
    if not state:
        raise HTTPException(status_code=404, detail="Analysis clarification state not found.")
    source_file_path = Path(state.get("source_file_path", ""))
    if not source_file_path.exists():
        raise HTTPException(status_code=404, detail="Original source file missing for clarification rerun.")
    merged_answers = merge_answers(state.get("answers"), [item.model_dump() for item in payload.answers])
    report = run_pipeline_for_file(
        source_file_path,
        bylaw_profile_id=state.get("bylaw_profile_id"),
        analysis_id=analysis_id,
        clarification_answers=merged_answers,
    )
    save_clarification_state(
        analysis_id,
        {
            **state,
            "answers": merged_answers,
        },
    )
    extracted_path = settings.extracted_dir / f"{analysis_id}.json"
    report_path = settings.reports_dir / f"{analysis_id}.json"
    persist_analysis(report, extracted_path, report_path)
    analysis_history_collection().update_one({"analysis_id": analysis_id}, {"$set": {"status": str(report.status).lower(), "updated_at": utcnow()}})
    return report


@app.get("/analysis/{analysis_id}", response_model=AnalysisReport)
def get_analysis(analysis_id: str) -> AnalysisReport:
    report_path = settings.reports_dir / f"{analysis_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found.")
    import json

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return AnalysisReport.model_validate(payload)


@app.post("/api/auth/signup", response_model=AuthResponse)
def api_signup(payload: SignUpRequest) -> AuthResponse:
    user = create_user(payload.full_name, payload.email, payload.password, payload.role)
    token = issue_token(user)
    return AuthResponse(access_token=token, user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(payload: LoginRequest) -> AuthResponse:
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = issue_token(user)
    return AuthResponse(access_token=token, user=user)


@app.get("/api/auth/me")
def api_me(authorization: str | None = Header(default=None)) -> dict:
    return _get_current_user(authorization)


@app.post("/api/analyze", response_model=AnalysisReport)
async def api_analyze(
    file: UploadFile = File(...),
    manual_rotation_deg: float = Form(default=0),
    bylaw_profile_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> AnalysisReport:
    current_user = _get_current_user(authorization)
    analysis_id = uuid4().hex
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or 'unknown'}")
    if not bylaw_profile_id:
        raise HTTPException(status_code=400, detail="bylaw_profile_id is required.")
    try:
        temp_path = await save_upload_temp(file, analysis_id)
        report = run_pipeline_for_file(
            temp_path,
            bylaw_profile_id=bylaw_profile_id,
            analysis_id=analysis_id,
            manual_rotation_deg=manual_rotation_deg,
        )
        save_clarification_state(
            analysis_id,
            {
                "analysis_id": analysis_id,
                "source_file_path": str(temp_path),
                "bylaw_profile_id": bylaw_profile_id,
                "answers": {},
                "user_id": current_user.get("_id"),
            },
        )
        extracted_path = settings.extracted_dir / f"{analysis_id}.json"
        report_path = settings.reports_dir / f"{analysis_id}.json"
        persist_analysis(report, extracted_path, report_path)
        _persist_analysis_history(
            analysis_id=analysis_id,
            file=file,
            ext=ext,
            bylaw_profile_id=bylaw_profile_id,
            report=report,
            user_id=current_user.get("_id"),
        )
        return report
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("API analyze pipeline failed for %s: %s", file.filename, exc)
        _raise_pipeline_http_error(exc)


@app.get("/api/analysis/{analysis_id}", response_model=AnalysisReport)
def api_get_analysis(analysis_id: str, authorization: str | None = Header(default=None)) -> AnalysisReport:
    _get_current_user(authorization)
    return get_analysis(analysis_id)


@app.post("/api/analysis/{analysis_id}/clarify", response_model=AnalysisReport)
def api_clarify_analysis(
    analysis_id: str, payload: ClarifyRequest, authorization: str | None = Header(default=None)
) -> AnalysisReport:
    _get_current_user(authorization)
    report = clarify_analysis(analysis_id, payload)
    return report


@app.get("/api/history/my")
def api_history_my(authorization: str | None = Header(default=None), skip: int = 0, limit: int = 50) -> dict:
    user = _get_current_user(authorization)
    cursor = analysis_history_collection().find({"user_id": user.get("_id")}).sort("created_at", -1).skip(skip).limit(limit)
    return {"items": [as_jsonable(item) for item in cursor], "skip": skip, "limit": limit}


@app.get("/api/history/{analysis_id}")
def api_history_by_analysis_id(analysis_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    item = as_jsonable(analysis_history_collection().find_one({"analysis_id": analysis_id}))
    if not item:
        raise HTTPException(status_code=404, detail="History not found.")
    return item


@app.get("/api/history/user/{user_id}")
def api_history_by_user_id(user_id: str, authorization: str | None = Header(default=None), skip: int = 0, limit: int = 50) -> dict:
    _get_current_user(authorization)
    cursor = analysis_history_collection().find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    return {"items": [as_jsonable(item) for item in cursor], "skip": skip, "limit": limit}


@app.post("/api/chat/logs")
def api_chat_logs_upsert(payload: ChatLogUpsertRequest, authorization: str | None = Header(default=None)) -> dict:
    user = _get_current_user(authorization)
    now = utcnow()
    existing = chat_logs_collection().find_one({"session_id": payload.session_id, "user_id": user.get("_id")})
    if existing:
        merged = list(existing.get("messages", [])) + payload.messages
        update = {"messages": merged, "ended_at": now if payload.ended else existing.get("ended_at")}
        chat_logs_collection().update_one({"_id": existing["_id"]}, {"$set": update})
        doc = chat_logs_collection().find_one({"_id": existing["_id"]})
        return as_jsonable(doc) or {}

    doc = {
        "session_id": payload.session_id,
        "analysis_id": payload.analysis_id,
        "user_id": user.get("_id"),
        "messages": payload.messages,
        "started_at": now,
        "ended_at": now if payload.ended else None,
    }
    inserted = chat_logs_collection().insert_one(doc)
    return as_jsonable(chat_logs_collection().find_one({"_id": inserted.inserted_id})) or {}


@app.get("/api/chat/logs/my")
def api_chat_logs_my(authorization: str | None = Header(default=None), skip: int = 0, limit: int = 50) -> dict:
    user = _get_current_user(authorization)
    cursor = chat_logs_collection().find({"user_id": user.get("_id")}).sort("started_at", -1).skip(skip).limit(limit)
    return {"items": [as_jsonable(item) for item in cursor], "skip": skip, "limit": limit}


@app.get("/api/chat/logs/session/{session_id}")
def api_chat_logs_by_session(session_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    item = as_jsonable(chat_logs_collection().find_one({"session_id": session_id}))
    if not item:
        raise HTTPException(status_code=404, detail="Session logs not found.")
    return item


@app.post("/api/reports/meta")
def api_reports_meta_create(payload: ReportMetaCreateRequest, authorization: str | None = Header(default=None)) -> dict:
    user = _get_current_user(authorization)
    now = utcnow()
    report_id = uuid4().hex
    doc = {
        "report_id": report_id,
        "analysis_id": payload.analysis_id,
        "user_id": user.get("_id"),
        "report_type": payload.report_type,
        "report_name": payload.report_name,
        "storage_path": payload.storage_path,
        "generated_at": now,
        "version": payload.version,
        "status": payload.status,
    }
    report_metadata_collection().insert_one(doc)
    return as_jsonable(doc) or {}


@app.get("/api/reports/meta/my")
def api_reports_meta_my(authorization: str | None = Header(default=None), skip: int = 0, limit: int = 50) -> dict:
    user = _get_current_user(authorization)
    cursor = report_metadata_collection().find({"user_id": user.get("_id")}).sort("generated_at", -1).skip(skip).limit(limit)
    return {"items": [as_jsonable(item) for item in cursor], "skip": skip, "limit": limit}


@app.get("/api/reports/meta/{report_id}")
def api_reports_meta_by_id(report_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    item = as_jsonable(report_metadata_collection().find_one({"report_id": report_id}))
    if not item:
        raise HTTPException(status_code=404, detail="Report metadata not found.")
    return item


def _next_report_id() -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"RPT-{year}-"
    count = report_metadata_collection().count_documents({"report_id": {"$regex": f"^{prefix}"}})
    return f"{prefix}{count + 1:06d}"


@app.post("/api/reports/generate")
def api_reports_generate(payload: ReportGenerateRequest, authorization: str | None = Header(default=None)) -> dict:
    user = _get_current_user(authorization)
    report_path = settings.reports_dir / f"{payload.analysis_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Analysis report not found.")
    import json

    analysis_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_id = _next_report_id()
    now = utcnow()
    report_json = build_report_json(
        report_id=report_id,
        analysis_id=payload.analysis_id,
        analysis_payload=analysis_payload,
        report_input=payload.model_dump(),
        generated_by=user.get("email") or user.get("full_name") or "system",
        app_env=settings.app_env,
    )
    html = render_report_html(report_json)
    json_storage_path, html_storage_path = write_report_files(report_json, html, settings.reports_dir)
    meta_doc = {
        "report_id": report_id,
        "analysis_id": payload.analysis_id,
        "user_id": user.get("_id"),
        "report_type": "compliance_analysis",
        "report_name": f"Compliance Report {report_id}",
        "storage_path": html_storage_path,
        "generated_at": now,
        "version": payload.version,
        "status": "generated",
        "json_storage_path": json_storage_path,
    }
    report_metadata_collection().insert_one(meta_doc)
    return {
        "report_id": report_id,
        "analysis_id": payload.analysis_id,
        "html": html,
        "json": report_json,
        "storage_path": html_storage_path,
        "json_storage_path": json_storage_path,
    }


@app.get("/api/reports/view/{report_id}")
def api_reports_view(report_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    meta = report_metadata_collection().find_one({"report_id": report_id})
    if not meta:
        raise HTTPException(status_code=404, detail="Report not found.")
    html_path = Path(str(meta.get("storage_path", "")))
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Report HTML not found.")
    return {
        "report_id": report_id,
        "analysis_id": str(meta.get("analysis_id", "")),
        "html": html_path.read_text(encoding="utf-8"),
        "generated_at": str(meta.get("generated_at", "")),
    }


@app.get("/api/records/by-user/{user_id}")
def api_records_by_user(user_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    user = as_jsonable(users_collection().find_one({"_id": user_id})) or as_jsonable(users_collection().find_one({"email": user_id.lower()}))
    history = [as_jsonable(item) for item in analysis_history_collection().find({"user_id": user_id}).sort("created_at", -1)]
    chats = [as_jsonable(item) for item in chat_logs_collection().find({"user_id": user_id}).sort("started_at", -1)]
    reports = [as_jsonable(item) for item in report_metadata_collection().find({"user_id": user_id}).sort("generated_at", -1)]
    return {"user": user, "history": history, "chat_logs": chats, "reports": reports}


@app.get("/api/records/by-analysis/{analysis_id}")
def api_records_by_analysis(analysis_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    history = as_jsonable(analysis_history_collection().find_one({"analysis_id": analysis_id}))
    chats = [as_jsonable(item) for item in chat_logs_collection().find({"analysis_id": analysis_id})]
    reports = [as_jsonable(item) for item in report_metadata_collection().find({"analysis_id": analysis_id})]
    return {"analysis_history": history, "chat_logs": chats, "reports": reports}


@app.get("/api/records/by-report/{report_id}")
def api_records_by_report(report_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    report = as_jsonable(report_metadata_collection().find_one({"report_id": report_id}))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    analysis = as_jsonable(analysis_history_collection().find_one({"analysis_id": report.get("analysis_id")}))
    return {"report_metadata": report, "analysis_history": analysis}


@app.get("/api/records/by-session/{session_id}")
def api_records_by_session(session_id: str, authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    chat = as_jsonable(chat_logs_collection().find_one({"session_id": session_id}))
    if not chat:
        raise HTTPException(status_code=404, detail="Session not found.")
    analysis = None
    reports = []
    if chat.get("analysis_id"):
        analysis = as_jsonable(analysis_history_collection().find_one({"analysis_id": chat["analysis_id"]}))
        reports = [as_jsonable(item) for item in report_metadata_collection().find({"analysis_id": chat["analysis_id"]})]
    return {"chat_log": chat, "analysis_history": analysis, "reports": reports}


@app.get("/api/bylaws/sets")
def api_bylaw_sets(authorization: str | None = Header(default=None)) -> dict:
    _get_current_user(authorization)
    sets = [as_jsonable(item) for item in bylaw_sets_collection().find({}).sort("created_at", -1)]
    clauses = [as_jsonable(item) for item in bylaw_clauses_collection().find({})]
    return {"bylaw_sets": sets, "bylaw_clauses": clauses}


@app.get("/api/debug/users")
def api_debug_users(authorization: str | None = Header(default=None), limit: int = 10) -> dict:
    _get_current_user(authorization)
    safe_limit = max(1, min(limit, 100))
    cursor = users_collection().find({}, {"password_hash": 0}).sort("created_at", -1).limit(safe_limit)
    return {"items": [as_jsonable(item) for item in cursor], "count": safe_limit}
