import json
import traceback
from types import SimpleNamespace

import httpx
import pytest
from openai import APIError, APITimeoutError, AuthenticationError

from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIAnalysisError, ImageRef, ProviderResult
from app.schemas.food import FoodAnalysis


def test_openai_provider_calls_responses_api_with_image_and_strict_schema() -> None:
    client = FakeOpenAIClient(_response())
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=17,
        client=client,
    )

    provider.call(
        "Return JSON.",
        ImageRef(content_type="image/jpeg", size_bytes=10, data=b"image-bytes"),
    )

    kwargs = client.responses.last_kwargs
    assert kwargs["model"] == "gpt-5.4-mini"
    assert kwargs["timeout"] == 17
    assert kwargs["input"][0]["content"][0] == {
        "type": "input_text",
        "text": "Return JSON.",
    }
    assert kwargs["input"][0]["content"][1]["type"] == "input_image"
    assert kwargs["input"][0]["content"][1]["image_url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert kwargs["text"]["format"]["schema"]["additionalProperties"] is False


def test_openai_provider_success_returns_provider_result() -> None:
    result = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response()),
    ).call("prompt", _image_ref())

    assert isinstance(result, ProviderResult)
    assert FoodAnalysis.model_validate(result.raw_analysis).schema_version == "food_analysis.v1"


def test_openai_provider_usage_tokens_flow_to_provider_result() -> None:
    result = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response(input_tokens=123, output_tokens=456)),
    ).call("prompt", _image_ref())

    assert result.input_tokens == 123
    assert result.output_tokens == 456


def test_openai_provider_cost_computed_for_gpt_5_4_mini() -> None:
    result = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response(input_tokens=1_000_000, output_tokens=1_000_000)),
    ).call("prompt", _image_ref())

    assert result.cost_usd == 5.25


def test_openai_provider_unknown_model_returns_zero_cost(caplog) -> None:
    result = OpenAIProvider(
        api_key="test-key",
        model="unknown-model",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response(input_tokens=1_000_000, output_tokens=1_000_000)),
    ).call("prompt", _image_ref())

    assert result.cost_usd == 0.0
    assert "No OpenAI pricing configured" in caplog.text


@pytest.mark.parametrize("content_type", ["image/heic", "image/heif"])
def test_openai_provider_rejects_heic_and_heif(content_type: str) -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response()),
    )

    with pytest.raises(AIAnalysisError) as exc:
        provider.call("prompt", ImageRef(content_type=content_type, size_bytes=10, data=b"x"))

    assert exc.value.safety_flags == ["unsupported_food_image"]


def test_openai_provider_rejects_gif_as_unsupported_food_image() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(_response()),
    )

    with pytest.raises(AIAnalysisError) as exc:
        provider.call("prompt", ImageRef(content_type="image/gif", size_bytes=10, data=b"x"))

    assert exc.value.safety_flags == ["unsupported_food_image"]


def test_openai_timeout_maps_to_ai_analysis_error() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(APITimeoutError(request=_request())),
    )

    with pytest.raises(AIAnalysisError, match="timed out"):
        provider.call("prompt", _image_ref())


def test_openai_auth_error_maps_without_key_material() -> None:
    api_key = "SECRET_TEST_KEY"
    provider = OpenAIProvider(
        api_key=api_key,
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(
            AuthenticationError(
                f"bad key {api_key}",
                response=httpx.Response(401, request=_request()),
                body=None,
            )
        ),
    )

    with pytest.raises(AIAnalysisError) as exc:
        provider.call("prompt", _image_ref())

    formatted = "".join(
        traceback.format_exception(type(exc.value), exc.value, exc.value.__traceback__)
    )
    assert api_key not in str(exc.value)
    assert api_key not in repr(exc.value.__cause__)
    assert api_key not in formatted


def test_openai_api_error_maps_to_ai_analysis_error() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(APIError("provider broke", request=_request(), body=None)),
    )

    with pytest.raises(AIAnalysisError, match="AI provider error"):
        provider.call("prompt", _image_ref())


def test_openai_missing_structured_output_maps_to_schema_validation_error() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=FakeOpenAIClient(SimpleNamespace(usage={})),
    )

    with pytest.raises(AIAnalysisError) as exc:
        provider.call("prompt", _image_ref())

    assert exc.value.safety_flags == ["schema_validation_failed"]


class FakeResponses:
    def __init__(self, response_or_error) -> None:
        self._response_or_error = response_or_error
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if isinstance(self._response_or_error, Exception):
            raise self._response_or_error
        return self._response_or_error


class FakeOpenAIClient:
    def __init__(self, response_or_error) -> None:
        self.responses = FakeResponses(response_or_error)


def _response(input_tokens: int = 10, output_tokens: int = 20):
    return SimpleNamespace(
        output_text=json.dumps(_model_output()),
        usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


def _model_output() -> dict[str, object]:
    return {
        "items_count": 1,
        "items": [
            {
                "item_id": "openai-item-1",
                "name": "Chicken breast",
                "portion": {
                    "description": "~150g",
                    "grams_estimate": 150,
                    "assumptions": ["Estimated from image."],
                },
                "calories": {"min": 198, "max": 298, "point_estimate": 248},
                "calorie_density_kcal_per_gram": 1.65,
                "confidence": "medium",
            }
        ],
        "total_calories": {"min": 198, "max": 298, "point_estimate": 248},
        "uncertainty_notes": ["Portions are estimated."],
        "safety_flags": [],
    }


def _image_ref() -> ImageRef:
    return ImageRef(content_type="image/jpeg", size_bytes=10, data=b"image-bytes")


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/responses")
