import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.ai.analyzer import AIFoodAnalyzer, FoodAnalyzer, MockFoodAnalyzer, select_food_analyzer
from app.main import app
from app.observability.model_run import ModelRun
from app.schemas.food import FoodAnalyzeMockRequest

client = TestClient(app)


def test_select_food_analyzer_defaults_to_mock(monkeypatch) -> None:
    monkeypatch.delenv("FITPLATE_AI_MODE", raising=False)

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, MockFoodAnalyzer)


def test_select_food_analyzer_returns_mock_for_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "mock")

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, MockFoodAnalyzer)


def test_select_food_analyzer_returns_ai_stub_for_ai_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, AIFoodAnalyzer)


def test_select_food_analyzer_raises_for_unknown_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "live-gpt")

    with pytest.raises(ValueError, match="FITPLATE_AI_MODE"):
        select_food_analyzer()


def test_analyzers_satisfy_protocol() -> None:
    assert isinstance(MockFoodAnalyzer(), FoodAnalyzer)
    assert isinstance(AIFoodAnalyzer(), FoodAnalyzer)


def test_mock_analyzer_exposes_mode_and_model() -> None:
    analyzer = MockFoodAnalyzer()

    assert analyzer.mode == "mock"
    assert analyzer.model == "mock"


def test_mock_analyzer_returns_food_analysis_with_current_mock_behavior() -> None:
    analyzer = MockFoodAnalyzer()

    result = analyzer.analyze(_request_payload())

    assert result.schema_version == "food_analysis.v1"
    assert result.mode == "mock"
    assert result.items_count == 3


def test_ai_analyzer_raises_not_implemented() -> None:
    analyzer = AIFoodAnalyzer()

    with pytest.raises(NotImplementedError, match="FITPLATE_AI_MODE=mock"):
        analyzer.analyze(_request_payload())


def test_analyze_route_with_ai_mode_returns_analysis_failed(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 500
    assert response.json() == {
        "code": "analysis_failed",
        "message": "Analysis unavailable. Please try again.",
    }


def test_model_run_log_records_ai_mode_on_ai_analyzer_error(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 500
    record = _read_records(log_path)[0]
    assert record.mode == "ai"
    assert record.model == "ai-provider-stub"
    assert record.error_code == "analysis_failed"


def _request_payload() -> FoodAnalyzeMockRequest:
    return FoodAnalyzeMockRequest(**_payload())


def _payload() -> dict[str, object]:
    return {
        "filename": "lunch-photo.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345678,
        "last_modified_ms": 1710000000000,
    }


def _use_log_path(tmp_path: Path, monkeypatch) -> Path:
    log_path = tmp_path / "model_runs.jsonl"
    monkeypatch.setattr(log_writer, "LOG_PATH", log_path)
    return log_path


def _read_records(log_path: Path) -> list[ModelRun]:
    return [
        ModelRun.model_validate(json.loads(line))
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
