import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.ai.analyzer import (
    AIFoodAnalyzer,
    FoodAnalyzer,
    MockFoodAnalyzer,
    select_food_analyzer,
)
from app.config import get_settings
from app.main import app
from app.observability.model_run import ModelRun
from app.schemas.food import FoodAnalyzeMockRequest

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_select_food_analyzer_defaults_to_mock(monkeypatch) -> None:
    monkeypatch.delenv("FITPLATE_AI_MODE", raising=False)
    _clear_settings_cache()

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, MockFoodAnalyzer)


def test_select_food_analyzer_returns_mock_for_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "mock")
    _clear_settings_cache()

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, MockFoodAnalyzer)


def test_select_food_analyzer_returns_ai_analyzer_for_ai_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    _clear_settings_cache()

    analyzer = select_food_analyzer()

    assert isinstance(analyzer, AIFoodAnalyzer)
    assert analyzer.model == "fake-food-vision-v1"


def test_select_food_analyzer_raises_for_unknown_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "live-gpt")
    _clear_settings_cache()

    with pytest.raises(ValueError, match="FITPLATE_AI_MODE"):
        select_food_analyzer()


def test_select_food_analyzer_raises_for_unknown_ai_provider(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "real-provider")
    _clear_settings_cache()

    with pytest.raises(ValueError, match="FITPLATE_AI_PROVIDER"):
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
    analysis = result.analysis

    assert analysis.schema_version == "food_analysis.v1"
    assert analysis.mode == "mock"
    assert analysis.items_count == 3


def test_mock_analyzer_usage_is_zero() -> None:
    result = MockFoodAnalyzer().analyze(_request_payload())

    assert result.usage.input_tokens == 0
    assert result.usage.output_tokens == 0
    assert result.usage.cost_usd == 0.0


def test_ai_analyzer_returns_fake_provider_food_analysis() -> None:
    analyzer = AIFoodAnalyzer()

    result = analyzer.analyze(_request_payload())
    analysis = result.analysis

    assert analysis.schema_version == "food_analysis.v1"
    assert analysis.mode == "ai"


def test_analyze_route_with_ai_mode_returns_ai_food_analysis(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    _clear_settings_cache()

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 200
    assert response.json()["mode"] == "ai"


def test_model_run_log_records_ai_mode_on_ai_analyzer_success(tmp_path, monkeypatch) -> None:
    log_path = _use_log_path(tmp_path, monkeypatch)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    _clear_settings_cache()

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 200
    record = _read_records(log_path)[0]
    assert record.mode == "ai"
    assert record.model == "fake-food-vision-v1"
    assert record.error_code is None


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


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
