import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.ai.analyzer import AIFoodAnalyzer
from app.ai.provider import ImageRef, ProviderResult
from app.config import get_settings
from app.main import app
from app.observability.model_run import ModelRun, build_model_run, now_utc
from app.routers import food as food_router

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_successful_analyze_writes_one_valid_jsonl_record(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())

    assert response.status_code == 200
    records = _read_records(log_path)
    assert len(records) == 1
    assert records[0].route == "POST /api/v0/food/analyze/mock"
    assert records[0].mode == "mock"
    assert records[0].model == "mock"
    assert records[0].input_summary == {
        "filename": "lunch-photo.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345678,
    }
    assert records[0].output_summary["analysis_id"] == response.json()["analysis_id"]
    assert records[0].output_summary["items_count"] == response.json()["items_count"]
    assert records[0].error_code is None
    assert records[0].input_tokens == 0
    assert records[0].output_tokens == 0
    assert records[0].cost_usd == 0.0


def test_successful_correction_writes_one_valid_jsonl_record(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    response = client.post("/api/v0/food/corrections/mock", json=_correction_payload())

    assert response.status_code == 200
    records = _read_records(log_path)
    assert len(records) == 1
    assert records[0].route == "POST /api/v0/food/corrections/mock"
    assert records[0].input_summary == {
        "item_id": "item-001",
        "original_name": "Chicken breast",
        "original_grams": 150,
        "corrected_grams": 200,
        "confidence": "medium",
    }
    assert records[0].output_summary["correction_id"] == response.json()["correction_id"]
    assert records[0].output_summary["corrected_calories"] == response.json()["corrected_calories"]
    assert records[0].error_code is None


def test_n_requests_produce_n_json_lines(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    for _ in range(3):
        response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())
        assert response.status_code == 200

    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 3


def test_each_line_is_valid_json_and_validates_as_model_run(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    client.post("/api/v0/food/analyze/mock", json=_analyze_payload())
    client.post("/api/v0/food/corrections/mock", json=_correction_payload())

    for line in log_path.read_text(encoding="utf-8").splitlines():
        parsed = json.loads(line)
        record = ModelRun.model_validate(parsed)
        assert record.model_run_schema_version == "model_run.v1"
        assert record.started_at <= record.ended_at
        assert record.latency_ms >= 0


def test_analyze_forced_exception_writes_error_log(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    class FailingAnalyzer:
        mode = "mock"
        model = "mock"

        def analyze(self, _payload) -> None:
            raise RuntimeError("forced analyze failure")

    monkeypatch.setattr(food_router, "select_food_analyzer", lambda: FailingAnalyzer())

    response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())

    assert response.status_code == 500
    record = _read_records(log_path)[0]
    assert record.error_code == "analysis_failed"
    assert record.error_message == "Analysis unavailable. Please try again."
    assert record.ended_at is not None
    assert record.latency_ms >= 0


def test_correction_forced_exception_writes_error_log(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)

    def fail_correction(*, grams: int, density: float, confidence: str) -> None:
        raise RuntimeError("forced correction failure")

    monkeypatch.setattr(food_router, "calorie_range_from_density", fail_correction)

    response = client.post("/api/v0/food/corrections/mock", json=_correction_payload())

    assert response.status_code == 500
    record = _read_records(log_path)[0]
    assert record.error_code == "correction_failed"
    assert record.error_message == "Correction unavailable. Please try again."
    assert record.ended_at is not None
    assert record.latency_ms >= 0


def test_logging_failure_does_not_break_successful_route_response(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path)

    response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())

    assert response.status_code == 200
    assert response.json()["mode"] == "mock"


def test_build_model_run_preserves_prompt_fields_when_passed() -> None:
    record = build_model_run(
        request_id="request-001",
        route="POST /api/v0/food/analyze/mock",
        started_at=now_utc(),
        input_summary={},
        output_summary={},
        prompt_name="food_analysis",
        prompt_version="v1",
    )

    assert record.prompt_name == "food_analysis"
    assert record.prompt_version == "v1"


def test_build_model_run_prompt_fields_default_to_none() -> None:
    record = build_model_run(
        request_id="request-001",
        route="POST /api/v0/food/analyze/mock",
        started_at=now_utc(),
        input_summary={},
        output_summary={},
    )

    assert record.prompt_name is None
    assert record.prompt_version is None


def test_build_model_run_preserves_usage_when_passed() -> None:
    record = build_model_run(
        request_id="request-001",
        route="POST /api/v0/food/analyze/mock",
        started_at=now_utc(),
        input_summary={},
        output_summary={},
        input_tokens=11,
        output_tokens=22,
        cost_usd=0.0034,
    )

    assert record.input_tokens == 11
    assert record.output_tokens == 22
    assert record.cost_usd == 0.0034


def test_build_model_run_usage_defaults_to_zero() -> None:
    record = build_model_run(
        request_id="request-001",
        route="POST /api/v0/food/analyze/mock",
        started_at=now_utc(),
        input_summary={},
        output_summary={},
    )

    assert record.input_tokens == 0
    assert record.output_tokens == 0
    assert record.cost_usd == 0.0


def test_ai_mode_analyze_log_records_fake_provider_and_prompt(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    get_settings.cache_clear()

    response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())

    assert response.status_code == 200
    record = _read_records(log_path)[0]
    assert record.mode == "ai"
    assert record.model == "fake-food-vision-v1"
    assert record.prompt_name == "food_analysis"
    assert record.prompt_version == "v1"
    assert record.input_tokens == 0
    assert record.output_tokens == 0
    assert record.cost_usd == 0.0
    assert record.error_code is None

    get_settings.cache_clear()


def test_malformed_ai_provider_output_logs_schema_validation_flag(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    analyzer = AIFoodAnalyzer(provider=MalformedProvider())
    monkeypatch.setattr(food_router, "select_food_analyzer", lambda: analyzer)

    response = client.post("/api/v0/food/analyze/mock", json=_analyze_payload())

    assert response.status_code == 500
    record = _read_records(log_path)[0]
    assert record.mode == "ai"
    assert record.model == "malformed-model"
    assert record.error_code == "analysis_failed"
    assert record.safety_flags == ["schema_validation_failed"]


class MalformedProvider:
    name = "malformed"
    model = "malformed-model"

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        return ProviderResult(
            raw_analysis={"schema_version": "food_analysis.v1"},
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
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


def _analyze_payload() -> dict[str, object]:
    return {
        "filename": "lunch-photo.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345678,
        "last_modified_ms": 1710000000000,
    }


def _correction_payload() -> dict[str, object]:
    return {
        "item_id": "item-001",
        "original_name": "Chicken breast",
        "original_grams": 150,
        "corrected_grams": 200,
        "calorie_density_kcal_per_gram": 1.65,
        "confidence": "medium",
        "original_calories": {
            "min": 198,
            "max": 298,
            "point_estimate": 248,
        },
    }
