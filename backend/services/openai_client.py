import base64
import json
import time
from typing import Any, Dict

from openai import OpenAI

from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.model = settings.openai_model
        self.enabled = bool(settings.openai_api_key.strip())
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None

    def extract_structured(self, image_bytes: bytes, ocr_hint_text: str) -> Dict[str, Any]:
        if not self.enabled or self.client is None:
            return {
                "floors": [],
                "rooms": [],
                "stairs": [],
                "lifts": [],
                "exits": [],
                "corridors": [],
                "dimensions": [],
                "confidence": {
                    "floors": 0.0,
                    "rooms": 0.0,
                    "circulation": 0.0,
                    "dimensions": 0.0,
                },
                "explanation": "OpenAI disabled; returned empty extraction.",
            }

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "You are extracting bylaw-compliance data from an architectural/map plan. Return strict JSON only. "
            "Never return markdown, prose, or code fences. "
            "Never fabricate facts. If uncertain, mark values as 'unknown' or null. "
            "If evidence is unclear, ask targeted clarification questions in explanation field and do not imply final legal verdict. "
            "Required top-level keys: floors, rooms, stairs, lifts, exits, corridors, dimensions, confidence, explanation. "
            "For each spatial item use this shape when possible: "
            "{name?: string, count?: number, area_sqft?: number, width_ft?: number, bbox?: [x1,y1,x2,y2], floor?: string}. "
            "For dimensions use: {label: string, value?: number, unit?: string, bbox?: [x1,y1,x2,y2], floor?: string}. "
            "If you can see a measurable value in image, extract it even if OCR hint is weak. "
            "Do not hallucinate: only include values visually present or strongly implied by map annotations. "
            "When floor is numeric, convert to string (example: '5'). "
            "Confidence must be numeric 0..1 for keys: floors, rooms, circulation, dimensions. "
            "If uncertain, keep item but leave numeric fields null and explain uncertainty. "
            f"OCR hints:\n{ocr_hint_text[:6000]}"
        )
        response_payload = None
        for attempt in range(1, self.settings.openai_max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "You are a strict JSON extractor for architectural compliance."},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                            ],
                        },
                    ],
                )
                content = response.choices[0].message.content or "{}"
                response_payload = json.loads(content)
                break
            except Exception as exc:
                if attempt == self.settings.openai_max_retries:
                    logger.warning("OpenAI extraction failed after retries: %s", exc)
                    response_payload = None
                    break
                wait = self.settings.openai_retry_backoff_sec * attempt
                logger.warning("OpenAI attempt %s failed: %s. Retrying in %.1fs", attempt, exc, wait)
                time.sleep(wait)

        if isinstance(response_payload, dict):
            return response_payload
        logger.warning("OpenAI response not valid JSON. Returning safe empty payload.")
        return {
            "floors": [],
            "rooms": [],
            "stairs": [],
            "lifts": [],
            "exits": [],
            "corridors": [],
            "dimensions": [],
            "confidence": {
                "floors": 0.0,
                "rooms": 0.0,
                "circulation": 0.0,
                "dimensions": 0.0,
            },
            "explanation": "Model response parse failure.",
        }

    def interpret_cad_labels(self, labels: list[str]) -> Dict[str, Any]:
        """
        Controlled GPT helper for ambiguous CAD abbreviations only.
        It never returns dimensions/values, only semantic class hints.
        """
        if not labels:
            return {"mappings": [], "unresolved": []}
        if not self.enabled or self.client is None:
            return {"mappings": [], "unresolved": labels}

        compact_labels = [str(label).strip() for label in labels if str(label).strip()][:80]
        if not compact_labels:
            return {"mappings": [], "unresolved": []}

        prompt = (
            "You are interpreting ambiguous AutoCAD labels.\n"
            "Allowed mapped_type values only: room, stair, lift, exit, corridor, floor, unknown.\n"
            "Do not invent measurements or dimensions.\n"
            "If uncertain, set mapped_type='unknown' and confidence <= 0.5.\n"
            "Return strict JSON with keys: mappings (array), unresolved (array).\n"
            "Each mapping object keys: label, mapped_type, confidence.\n"
            f"Labels:\n{json.dumps(compact_labels)}"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You classify CAD label abbreviations into safe semantic buckets."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                return {"mappings": [], "unresolved": compact_labels}
            mappings = parsed.get("mappings", [])
            unresolved = parsed.get("unresolved", [])
            if not isinstance(mappings, list):
                mappings = []
            if not isinstance(unresolved, list):
                unresolved = []
            return {"mappings": mappings, "unresolved": unresolved}
        except Exception as exc:
            logger.warning("CAD label interpretation failed: %s", exc)
            return {"mappings": [], "unresolved": compact_labels}
