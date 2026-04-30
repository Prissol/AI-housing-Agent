from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.groq_service import generate_bylaw_answer
from utils.logger import get_logger

router = APIRouter(tags=["Bylaw Chat"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000)
    context: str = Field(default="", max_length=6000)


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.query.strip()
    context = payload.context.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )

    logger.info("Received bylaw chat question (%s chars).", len(question))

    try:
        answer = generate_bylaw_answer(question=question, context=context)
    except Exception as exc:  # pragma: no cover - API safety net
        logger.exception("Chat endpoint failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch chatbot response right now.",
        ) from exc

    return ChatResponse(response=answer)
