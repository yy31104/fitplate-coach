import json
import base64
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.formparsers import MultiPartParser

import app.observability.log_writer as log_writer
from app.ai.analyzer import AIFoodAnalyzer
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import FakeAIProvider, ImageRef, ProviderResult
from app.config import get_settings
from app.main import app
from app.observability.model_run import ModelRun
from app.routers import food as food_router
from app.routers.food import MAX_FILE_SIZE_BYTES

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_valid_jpeg_upload_returns_food_analysis() -> None:
    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["schema_version"] == "food_analysis.v1"
    assert body["mode"] == "mock"


def test_upload_rejects_unsupported_content_type() -> None:
    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(content_type="text/plain"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_file_type"


def test_upload_rejects_empty_image() -> None:
    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(content=b""),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "empty_file"


def test_upload_rejects_oversized_image() -> None:
    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(content=b"x" * (MAX_FILE_SIZE_BYTES + 1)),
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_upload_requires_image_field() -> None:
    response = client.post("/api/v0/food/analyze", files={})

    assert response.status_code == 422


def test_upload_rejects_wrong_file_field_name() -> None:
    response = client.post(
        "/api/v0/food/analyze",
        files={"file": ("meal.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 422


def test_upload_model_run_records_multipart_input_summary(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(filename="meal.jpg", content=b"abc123"),
    )

    assert response.status_code == 200
    record = _read_records(log_path)[0]
    assert record.route == "POST /api/v0/food/analyze"
    assert record.input_summary == {
        "transport": "multipart",
        "filename": "meal.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 6,
    }


def test_upload_model_run_does_not_contain_uploaded_bytes(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    sentinel = b"UNIQUE_UPLOAD_SENTINEL_DO_NOT_LOG"

    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(content=sentinel),
    )

    assert response.status_code == 200
    raw_line = log_path.read_text(encoding="utf-8").strip()
    record = ModelRun.model_validate(json.loads(raw_line))
    assert all(
        not isinstance(value, (bytes, bytearray)) for value in record.input_summary.values()
    )
    assert sentinel.decode("utf-8") not in raw_line


def test_upload_ai_mode_uses_fake_provider_and_logs_prompt(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    get_settings.cache_clear()

    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(),
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "ai"
    record = _read_records(log_path)[0]
    assert record.mode == "ai"
    assert record.model == "fake-food-vision-v1"
    assert record.prompt_name == "food_analysis"
    assert record.prompt_version == "v1"


def test_upload_ai_mode_passes_bytes_to_provider_without_logging_them(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    sentinel = b"AI_UPLOAD_SENTINEL_BYTES"
    provider = RecordingProvider()
    analyzer = AIFoodAnalyzer(provider=provider)
    monkeypatch.setattr(food_router, "select_food_analyzer", lambda: analyzer)

    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(content=sentinel),
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "ai"
    assert provider.seen_data == sentinel
    raw_line = log_path.read_text(encoding="utf-8").strip()
    record = ModelRun.model_validate(json.loads(raw_line))
    assert record.mode == "ai"
    assert sentinel.decode("utf-8") not in raw_line


def test_upload_openai_provider_missing_key_returns_analysis_failed(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "openai")
    monkeypatch.delenv("FITPLATE_AI_PROVIDER_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post("/api/v0/food/analyze", files=_image_file())

    assert response.status_code == 500
    assert response.json()["code"] == "analysis_failed"


def test_upload_cost_cap_exceeded_returns_503_and_does_not_select_provider(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    log_path.write_text(
        json.dumps(
                {
                    "mode": "ai",
                    "started_at": datetime.now(UTC).isoformat(),
                    "cost_usd": 1.0,
                }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_MONTHLY_COST_CAP_USD", "1.0")
    monkeypatch.setattr(
        food_router,
        "select_food_analyzer",
        lambda: (_ for _ in ()).throw(AssertionError("provider should not be selected")),
    )
    get_settings.cache_clear()

    response = client.post("/api/v0/food/analyze", files=_image_file())

    assert response.status_code == 503
    assert response.json()["code"] == "cost_cap_exceeded"
    record = ModelRun.model_validate(
        json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    )
    assert record.error_code == "cost_cap_exceeded"
    assert record.model == "cost-cap"


def test_upload_openai_provider_logs_usage_without_secrets_or_image_bytes(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    api_key = "SECRET_OPENAI_KEY_SENTINEL"
    image_bytes = b"UNIQUE_OPENAI_IMAGE_BYTES"
    client = FakeOpenAIClient(_openai_response(input_tokens=1000, output_tokens=2000))
    provider = OpenAIProvider(
        api_key=api_key,
        model="gpt-5.4-mini",
        timeout_seconds=30,
        client=client,
    )
    monkeypatch.setattr(
        food_router,
        "select_food_analyzer",
        lambda: AIFoodAnalyzer(provider=provider),
    )

    response = client_post_upload(image_bytes)

    assert response.status_code == 200
    assert response.json()["mode"] == "ai"
    raw_line = log_path.read_text(encoding="utf-8").strip()
    record = ModelRun.model_validate(json.loads(raw_line))
    assert record.input_tokens == 1000
    assert record.output_tokens == 2000
    assert record.cost_usd > 0
    assert api_key not in raw_line
    assert image_bytes.decode("utf-8") not in raw_line
    assert base64.b64encode(image_bytes).decode("ascii") not in raw_line


def test_upload_long_filename_is_truncated_in_model_run(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    filename = f"{'a' * 300}.jpg"

    response = client.post(
        "/api/v0/food/analyze",
        files=_image_file(filename=filename),
    )

    assert response.status_code == 200
    record = _read_records(log_path)[0]
    assert len(record.input_summary["filename"]) == 255


def test_upload_same_filename_produces_same_mock_item_names() -> None:
    first = client.post(
        "/api/v0/food/analyze",
        files=_image_file(filename="same-meal.jpg"),
    )
    second = client.post(
        "/api/v0/food/analyze",
        files=_image_file(filename="same-meal.jpg"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert _item_names(first.json()) == _item_names(second.json())


def test_multipart_spool_threshold_exceeds_upload_cap() -> None:
    assert MultiPartParser.spool_max_size > MAX_FILE_SIZE_BYTES


def _image_file(
    *,
    filename: str = "meal.jpg",
    content: bytes = b"image-bytes",
    content_type: str = "image/jpeg",
) -> dict[str, tuple[str, bytes, str]]:
    return {"image": (filename, content, content_type)}


def _item_names(body: dict[str, object]) -> list[str]:
    items = body["items"]
    assert isinstance(items, list)
    return [item["name"] for item in items]


class RecordingProvider(FakeAIProvider):
    seen_data: bytes | None = None

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        self.seen_data = image_ref.data
        return super().call(prompt, image_ref)


class FakeResponses:
    def __init__(self, response) -> None:
        self._response = response

    def create(self, **kwargs):
        return self._response


class FakeOpenAIClient:
    def __init__(self, response) -> None:
        self.responses = FakeResponses(response)


def client_post_upload(content: bytes):
    return client.post(
        "/api/v0/food/analyze",
        files=_image_file(content=content),
    )


def _openai_response(input_tokens: int, output_tokens: int):
    return SimpleNamespace(
        output_text=json.dumps(
            {
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
                        "calories": {
                            "min": 198,
                            "max": 298,
                            "point_estimate": 248,
                        },
                        "calorie_density_kcal_per_gram": 1.65,
                        "confidence": "medium",
                    }
                ],
                "total_calories": {
                    "min": 198,
                    "max": 298,
                    "point_estimate": 248,
                },
                "uncertainty_notes": ["Estimated with uncertainty."],
                "safety_flags": [],
            }
        ),
        usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
    )


def _use_log_path(tmp_path: Path, monkeypatch) -> Path:
    log_path = tmp_path / "model_runs.jsonl"
    monkeypatch.setattr(log_writer, "LOG_PATH", log_path)
    return log_path


def _read_records(log_path: Path) -> list[ModelRun]:
    return [
        ModelRun.model_validate(json.loads(line))
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
