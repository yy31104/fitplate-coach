from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.ai.analyzer import AIAnalysisError, AIFoodAnalyzer
from app.ai.provider import FakeAIProvider, ImageRef
from app.main import app
from app.routers import food as food_router
from app.schemas.food import FoodAnalyzeMockRequest

client = TestClient(app)


def test_ai_food_analyzer_with_fake_provider_returns_food_analysis() -> None:
    analysis = AIFoodAnalyzer(provider=FakeAIProvider()).analyze(_request_payload())

    assert analysis.schema_version == "food_analysis.v1"
    assert analysis.items_count == 3


def test_ai_food_analyzer_returns_ai_mode() -> None:
    analysis = AIFoodAnalyzer(provider=FakeAIProvider()).analyze(_request_payload())

    assert analysis.mode == "ai"


def test_ai_food_analyzer_generates_uuid_like_analysis_id() -> None:
    analysis = AIFoodAnalyzer(provider=FakeAIProvider()).analyze(_request_payload())

    assert str(UUID(analysis.analysis_id)) == analysis.analysis_id


def test_ai_food_analyzer_sets_backend_analyzed_at() -> None:
    analysis = AIFoodAnalyzer(provider=FakeAIProvider()).analyze(_request_payload())

    assert analysis.analyzed_at.year >= 2026
    assert analysis.analyzed_at.tzinfo is not None


def test_ai_food_analyzer_overrides_provider_identity_and_timing_fields() -> None:
    provider = IdentitySpoofingProvider()

    analysis = AIFoodAnalyzer(provider=provider).analyze(_request_payload())

    assert analysis.analysis_id != provider.analysis_id
    assert analysis.analyzed_at != provider.analyzed_at
    assert analysis.schema_version == "food_analysis.v1"
    assert analysis.mode == "ai"


def test_ai_food_analyzer_exposes_prompt_name_and_version() -> None:
    analyzer = AIFoodAnalyzer(provider=FakeAIProvider())

    assert analyzer.prompt_name == "food_analysis"
    assert analyzer.prompt_version == "v1"


def test_malformed_provider_output_raises_ai_analysis_error() -> None:
    analyzer = AIFoodAnalyzer(provider=MalformedProvider())

    with pytest.raises(AIAnalysisError):
        analyzer.analyze(_request_payload())


def test_route_returns_analysis_failed_for_malformed_provider_output(monkeypatch) -> None:
    analyzer = AIFoodAnalyzer(provider=MalformedProvider())
    monkeypatch.setattr(food_router, "select_food_analyzer", lambda: analyzer)

    response = client.post("/api/v0/food/analyze/mock", json=_payload())

    assert response.status_code == 500
    assert response.json() == {
        "code": "analysis_failed",
        "message": "Analysis unavailable. Please try again.",
    }


class IdentitySpoofingProvider(FakeAIProvider):
    analysis_id = "11111111-1111-4111-8111-111111111111"
    analyzed_at = datetime(2000, 1, 1, tzinfo=UTC)

    def call(self, prompt: str, image_ref: ImageRef) -> dict[str, object]:
        raw = super().call(prompt, image_ref)
        raw["analysis_id"] = self.analysis_id
        raw["analyzed_at"] = self.analyzed_at.isoformat()
        return raw


class MalformedProvider:
    name = "malformed"
    model = "malformed-model"

    def call(self, prompt: str, image_ref: ImageRef) -> dict[str, object]:
        return {"schema_version": "food_analysis.v1"}


def _request_payload() -> FoodAnalyzeMockRequest:
    return FoodAnalyzeMockRequest(**_payload())


def _payload() -> dict[str, object]:
    return {
        "filename": "lunch-photo.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345_678,
        "last_modified_ms": 1_710_000_000_000,
    }
