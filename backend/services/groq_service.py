from groq import Groq
import re

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a housing bylaw assistant.
Only answer questions related to housing/building bylaws, approvals, map compliance,
setbacks, floor-area guidance, parking requirements, and related legal construction rules.

If the user asks about unrelated topics, politely refuse and ask them to ask a bylaw question.
Keep answers concise, practical, and beginner-friendly.
""".strip()


def _extract_context_value(pattern: str, context: str) -> str | None:
    match = re.search(pattern, context, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _build_context_grounded_answer(question: str, context: str) -> str | None:
    lowered = question.lower()
    if not context:
        return None

    status = _extract_context_value(r"status:\s*([^|\n]+)", context)
    file_name = _extract_context_value(r"file:\s*([^|]+)", context)
    height = _extract_context_value(r"building height detected:\s*([0-9.]+\s*ft)", context)
    floors = _extract_context_value(r"storey count detected:\s*([0-9]+)", context)
    setbacks = _extract_context_value(r"readings\s*->\s*front:\s*([^,]+),\s*rear:\s*([^,]+),\s*side:\s*([^\.;\n]+)", context)

    if any(token in lowered for token in ["status", "accepted", "rejected", "compliant", "non-compliant", "approve"]):
        if status:
            return f"Latest analyzed file `{file_name or 'current file'}` has status: {status}. This is based on current bylaw and OCR context."
        return "I do not have analyzed status in current context yet. Please run Analyze first."

    if any(token in lowered for token in ["height", "building height"]):
        if height:
            return f"From latest analyzed context, detected building height is {height}."
        return "Current analyzed context does not provide a reliable building-height measurement."

    if any(token in lowered for token in ["floor", "floors", "storey", "stories"]):
        if floors:
            return f"From latest analyzed context, detected storey count is {floors}."
        return "Current analyzed context does not provide a reliable floor/storey count."

    if "setback" in lowered:
        if setbacks:
            return "Setback readings were found in the latest context. Please refer to the listed front/rear/side values in the compliance findings."
        return "Current analyzed context does not provide complete setback values."

    if any(token in lowered for token in ["why", "reason", "issue", "problem"]):
        if status and ("violation" in status.lower() or "non-compliant" in status.lower()):
            return "Latest file is non-compliant mainly because measurable bylaw evidence is incomplete or unclear in OCR context."
        if status:
            return "Latest file appears compliant in current context; no major bylaw violation was flagged."

    return None


def _fallback_bylaw_answer(question: str, context: str = "") -> str:
    lowered = question.lower()
    context_lower = context.lower()
    context_answer = _build_context_grounded_answer(question, context)
    if context_answer:
        return context_answer

    if context and any(token in lowered for token in ["why", "reject", "rejected", "non-compliant", "status", "approved", "accept"]):
        if "no violation" in context_lower:
            return "Latest analysis context indicates Compliant/No Violation. It appears accepted based on currently extracted bylaw signals."
        if "violation" in context_lower or "non-compliant" in context_lower:
            return "Latest analysis context indicates Non-Compliant/Violation. The main reason is missing or unclear measurable bylaw evidence (for example plot type, setbacks, height, or floor count) in the current plan."

    bylaw_terms = [
        "bylaw",
        "setback",
        "setbacks",
        "height",
        "floors",
        "floor",
        "plot",
        "parking",
        "building",
        "dha",
        "map",
        "approval",
        "commercial",
        "residential",
    ]
    if not any(term in lowered for term in bylaw_terms):
        return (
            "I can help with housing bylaws only. Please ask about setbacks, plot size, building "
            "height, floors, parking, or map approval rules."
        )
    if context and any(token in lowered for token in ["this", "current", "image", "plan", "result", "analysis"]):
        if "no violation" in context_lower and any(term in lowered for term in ["approve", "accepted", "status", "result"]):
            return "Current analyzed plan appears compliant in the latest result context. You can proceed, but final approval should still be validated against official DHA documents."
        if "violation" in context_lower and any(term in lowered for term in ["why", "reason", "issue", "reject", "non-compliant"]):
            return "Based on the current analyzed context, non-compliance is coming from missing measurable bylaw evidence (such as clear plot/setback/height/floor details). Improve plan clarity or provide explicit measurements for accurate validation."
    if "setback" in lowered:
        return (
            "Setbacks depend on plot type and zoning. For compliance, confirm front/side/rear "
            "setback values from your DHA checklist and ensure all building edges respect those limits."
        )
    if "height" in lowered or "floor" in lowered:
        return (
            "Height and floor limits vary by residential/commercial category. Verify allowed stories "
            "(for example, categories like B+G+1) and maximum building height before approval."
        )
    if "parking" in lowered:
        return (
            "Parking compliance is checked against use type and covered area. Confirm minimum required "
            "parking bays and that access/driveway width is available on the submitted plan."
        )
    if "commercial" in lowered:
        return (
            "For commercial plans, review use category, frontage requirements, parking demand, height "
            "cap, and fire/egress constraints from the approved DHA commercial checklist."
        )
    if "residential" in lowered:
        return (
            "For residential plans, verify plot dimensions, front/side/rear setbacks, story limit, "
            "height cap, and any mandatory open space and parking rules."
        )
    return (
        "Please share plot type and key measurements (road width, setbacks, height, floors, parking). "
        "I can then give a more precise bylaw compliance answer."
    )


def generate_bylaw_answer(question: str, context: str = "") -> str:
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY is missing. Returning fallback bylaw response.")
        return _fallback_bylaw_answer(question, context)

    client = Groq(api_key=settings.groq_api_key)
    try:
        user_prompt = question
        if context:
            user_prompt = (
                "Use this latest analyzed-plan context for answer grounding.\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{question}"
            )

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=600,
        )
    except Exception as exc:  # pragma: no cover - external API/network safety
        logger.exception("Groq request failed, using fallback response: %s", exc)
        return _fallback_bylaw_answer(question, context)

    content = response.choices[0].message.content
    if not content:
        logger.warning("Groq returned empty response content.")
        return _fallback_bylaw_answer(question, context)

    return content.strip()
