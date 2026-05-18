import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.config import get_settings
from app.main import app
from app.mock.density import CONFIDENCE_MARGIN
from app.mock.food_analyzer import scenario_bucket
from app.observability.model_run import ModelRun
from app.routers import food as food_router
from app.schemas.food import KNOWN_SAFETY_FLAGS

client = TestClient(app)


def test_analyze_valid_jpeg_metadata_returns_200() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 200


def test_analyze_response_schema_fields_present() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    body = response.json()

    assert response.status_code == 200
    assert {
        "analysis_id",
        "schema_version",
        "mode",
        "analyzed_at",
        "items_count",
        "items",
        "total_calories",
        "uncertainty_notes",
        "safety_flags",
        "user_corrections",
    }.issubset(body.keys())


def test_analyze_mode_is_mock() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.json()["mode"] == "mock"


def test_analyze_schema_version() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.json()["schema_version"] == "food_analysis.v1"


def test_analyze_rejects_text_file() -> None:
    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload(content_type="text/plain"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_file_type"


def test_analyze_rejects_oversized_file() -> None:
    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload(size_bytes=10 * 1024 * 1024 + 1),
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_analyze_rejects_empty_file() -> None:
    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload(size_bytes=0),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "empty_file"


def test_analyze_rejects_negative_file_size_as_invalid_body() -> None:
    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload(size_bytes=-1),
    )

    assert response.status_code == 422


def test_analyze_calorie_totals_consistent() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    body = response.json()
    items = body["items"]

    assert body["total_calories"]["min"] == sum(item["calories"]["min"] for item in items)
    assert body["total_calories"]["max"] == sum(item["calories"]["max"] for item in items)
    assert body["total_calories"]["point_estimate"] == sum(
        item["calories"]["point_estimate"] for item in items
    )


def test_analyze_confidence_range_proportional() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    for item in response.json()["items"]:
        calories = item["calories"]
        point = calories["point_estimate"]
        margin = CONFIDENCE_MARGIN[item["confidence"]]

        assert calories["min"] == round(point * (1 - margin))
        assert calories["max"] == round(point * (1 + margin))


def test_analyze_safety_flags_are_known_values() -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_payload(filename=_filename_for_bucket(7)))

    assert set(response.json()["safety_flags"]).issubset(KNOWN_SAFETY_FLAGS)


def test_analyze_analysis_id_unique_across_calls() -> None:
    payload = _payload()

    first = client.post("/api/v0/food/analyze/mock", json=payload).json()
    second = client.post("/api/v0/food/analyze/mock", json=payload).json()

    assert first["analysis_id"] != second["analysis_id"]


def test_analyze_non_food_scenario_returns_empty_items() -> None:
    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload(filename=_filename_for_bucket(8)),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["items"] == []
    assert body["items_count"] == 0
    assert "non_food_image" in body["safety_flags"]


def test_analyze_mock_cost_cap_exceeded_returns_503_and_logs(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "model_runs.jsonl"
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
    monkeypatch.setattr(log_writer, "LOG_PATH", log_path)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_MONTHLY_COST_CAP_USD", "1.0")
    monkeypatch.setattr(
        food_router,
        "select_food_analyzer",
        lambda: (_ for _ in ()).throw(AssertionError("provider should not be selected")),
    )
    get_settings.cache_clear()

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 503
    assert response.json()["code"] == "cost_cap_exceeded"
    record = ModelRun.model_validate(
        json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    )
    assert record.error_code == "cost_cap_exceeded"
    assert record.mode == "ai"
    assert record.model == "cost-cap"

    get_settings.cache_clear()


def _payload(
    filename: str | None = None,
    content_type: str = "image/jpeg",
    size_bytes: int = 345_678,
) -> dict[str, object]:
    return {
        "filename": filename or _filename_for_bucket(0),
        "content_type": content_type,
        "size_bytes": size_bytes,
        "last_modified_ms": 1_710_000_000_000,
    }


def _filename_for_bucket(bucket: int) -> str:
    for index in range(10_000):
        filename = f"mock-food-bucket-{bucket}-{index}.jpg"
        if scenario_bucket(filename) == bucket:
            return filename

    raise AssertionError(f"Could not find filename for bucket {bucket}")
