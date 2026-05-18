import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.formparsers import MultiPartParser

import app.observability.log_writer as log_writer
from app.config import get_settings
from app.main import app
from app.observability.model_run import ModelRun
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


def _use_log_path(tmp_path: Path, monkeypatch) -> Path:
    log_path = tmp_path / "model_runs.jsonl"
    monkeypatch.setattr(log_writer, "LOG_PATH", log_path)
    return log_path


def _read_records(log_path: Path) -> list[ModelRun]:
    return [
        ModelRun.model_validate(json.loads(line))
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
