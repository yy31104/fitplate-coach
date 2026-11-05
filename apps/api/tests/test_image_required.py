"""A vision provider must never be called without image bytes.

The web client's default flow sends only file metadata to /analyze/mock. In AI
mode with the OpenAI provider, that used to send `data:image/jpeg;base64,` (an
empty image) to a paid API. These tests use a stub client that counts calls; no
network request is made and no key is real.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.ai.openai_provider as openai_provider
import app.observability.log_writer as log_writer
from app.ai.analyzer import AIFoodAnalyzer
from app.ai.provider import FakeAIProvider, ImageRef, ImageRequiredError
from app.config import get_settings
from app.main import app
from app.schemas.food import FoodAnalyzeMockRequest

client = TestClient(app)


class CountingResponses:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs: object) -> object:
        self.calls += 1
        raise AssertionError("the provider must not be called without image bytes")


class CountingOpenAIClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.responses = CountingResponses()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def openai_mode(tmp_path, monkeypatch) -> list[CountingOpenAIClient]:
    created: list[CountingOpenAIClient] = []

    def factory(*args: object, **kwargs: object) -> CountingOpenAIClient:
        instance = CountingOpenAIClient()
        created.append(instance)
        return instance

    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path / "model_runs.jsonl")
    monkeypatch.setattr(openai_provider, "OpenAI", factory)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "openai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FITPLATE_MONTHLY_COST_CAP_USD", "0")
    get_settings.cache_clear()
    return created


def _metadata() -> dict[str, object]:
    return {
        "filename": "lunch.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345_678,
        "last_modified_ms": 1_710_000_000_000,
    }


def test_metadata_route_in_openai_mode_returns_422_without_calling_provider(openai_mode) -> None:
    response = client.post("/api/v0/food/analyze/mock", json=_metadata())

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "image_required"
    assert "upload" in body["message"].lower()
    assert sum(instance.responses.calls for instance in openai_mode) == 0


def test_metadata_route_logs_image_required(openai_mode, tmp_path) -> None:
    client.post("/api/v0/food/analyze/mock", json=_metadata())

    log = (tmp_path / "model_runs.jsonl").read_text(encoding="utf-8")
    assert '"error_code":"image_required"' in log.replace(" ", "")


def test_ai_analyzer_refuses_empty_bytes_before_provider_call() -> None:
    class RecordingProvider:
        name = "recording"
        model = "recording-model"

        def __init__(self) -> None:
            self.calls = 0

        def call(self, prompt: str, image_ref: ImageRef) -> object:
            self.calls += 1
            raise AssertionError("must not be called")

    provider = RecordingProvider()
    analyzer = AIFoodAnalyzer(provider=provider)
    payload = FoodAnalyzeMockRequest(**_metadata())

    with pytest.raises(ImageRequiredError):
        analyzer.analyze(payload)
    with pytest.raises(ImageRequiredError):
        analyzer.analyze(payload, image_ref=ImageRef(content_type="image/jpeg", size_bytes=0, data=b""))

    assert provider.calls == 0


def test_fake_provider_still_runs_from_metadata() -> None:
    """The fake picks a scenario from metadata by design, so it opts out of the check."""
    analyzer = AIFoodAnalyzer(provider=FakeAIProvider())

    result = analyzer.analyze(FoodAnalyzeMockRequest(**_metadata()))

    assert result.analysis.mode == "ai"
