import base64
import json
import logging
from typing import Any, get_args

from openai import APIError, APITimeoutError, AuthenticationError, OpenAI

from app.ai.provider import AIAnalysisError, ImageRef, ProviderResult
from app.nutrition import FOOD_CATEGORIES
from app.schemas.food import SafetyFlag

logger = logging.getLogger(__name__)

SUPPORTED_OPENAI_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
OPENAI_UNSUPPORTED_FOOD_IMAGE_TYPES = {"image/heic", "image/heif"}
MODEL_PRICING_PER_MILLION_TOKENS = {
    "gpt-5.4-mini": {
        "input": 0.75,
        "output": 4.50,
    },
}


class OpenAIProvider:
    name = "openai"
    requires_image_bytes = True

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = (
            client
            if client is not None
            else OpenAI(api_key=api_key, timeout=timeout_seconds)
        )

    @property
    def model(self) -> str:
        return self._model

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        if image_ref.content_type in OPENAI_UNSUPPORTED_FOOD_IMAGE_TYPES:
            raise AIAnalysisError(
                "AI provider does not support this image type.",
                safety_flags=["unsupported_food_image"],
            )
        if image_ref.content_type not in SUPPORTED_OPENAI_IMAGE_TYPES:
            raise AIAnalysisError(
                "AI provider does not support this image type.",
                safety_flags=["unsupported_food_image"],
            )

        image_url = _image_data_url(image_ref)

        try:
            response = self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": image_url},
                        ],
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "food_analysis_model_output",
                        "strict": True,
                        "schema": _food_analysis_model_output_schema(),
                    }
                },
                timeout=self._timeout_seconds,
            )
        except APITimeoutError as exc:
            raise AIAnalysisError("AI provider timed out", safety_flags=[]) from exc
        except AuthenticationError:
            raise AIAnalysisError("AI provider unavailable", safety_flags=[]) from None
        except APIError:
            raise AIAnalysisError("AI provider error", safety_flags=[]) from None

        structured_output = _extract_structured_output(response)
        if structured_output is None:
            raise AIAnalysisError(
                "AI provider returned no structured food analysis output.",
                safety_flags=["schema_validation_failed"],
            )

        input_tokens, output_tokens = _usage_tokens(response)
        return ProviderResult(
            # Names, grams, category or density, confidence. The analyzer
            # computes calories, items_count and totals.
            raw_analysis=structured_output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_cost_usd(self._model, input_tokens, output_tokens),
        )


def _image_data_url(image_ref: ImageRef) -> str:
    encoded = base64.b64encode(image_ref.data).decode("ascii")
    return f"data:{image_ref.content_type};base64,{encoded}"


def _extract_structured_output(response: Any) -> dict[str, object] | None:
    output_parsed = getattr(response, "output_parsed", None)
    if isinstance(output_parsed, dict):
        return output_parsed

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

    for output_item in getattr(response, "output", []) or []:
        for content_item in getattr(output_item, "content", []) or []:
            parsed = getattr(content_item, "parsed", None)
            if isinstance(parsed, dict):
                return parsed
            text = getattr(content_item, "text", None)
            if isinstance(text, str):
                try:
                    parsed_text = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed_text, dict):
                    return parsed_text

    return None


def _usage_tokens(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    input_tokens = _get_usage_value(usage, "input_tokens")
    output_tokens = _get_usage_value(usage, "output_tokens")
    return input_tokens, output_tokens


def _get_usage_value(usage: Any, key: str) -> int:
    if usage is None:
        return 0

    value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, 0)
    return value if isinstance(value, int) else 0


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        logger.warning("No OpenAI pricing configured for model %s", model)
        return 0.0

    return (
        input_tokens * pricing["input"] / 1_000_000
        + output_tokens * pricing["output"] / 1_000_000
    )


def _food_analysis_model_output_schema() -> dict[str, object]:
    """Strict schema for what the model may decide. No calorie numbers."""
    item_schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "grams", "category", "density_kcal_per_gram", "confidence"],
        "properties": {
            "name": {"type": "string"},
            "grams": {"type": "integer"},
            "category": {
                "type": ["string", "null"],
                "enum": [*FOOD_CATEGORIES, None],
            },
            "density_kcal_per_gram": {"type": ["number", "null"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items", "uncertainty_notes", "safety_flags"],
        "properties": {
            "items": {
                "type": "array",
                "items": item_schema,
            },
            "uncertainty_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
            "safety_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(get_args(SafetyFlag)),
                },
            },
        },
    }
