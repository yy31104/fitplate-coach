import base64
import json
import os

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.config import get_settings
from app.main import app

client = TestClient(app)


@pytest.mark.real_provider
def test_real_openai_provider_upload_flow(tmp_path, monkeypatch) -> None:
    """Spends real OpenAI API money when explicitly enabled."""
    api_key = os.environ.get("FITPLATE_AI_PROVIDER_API_KEY")
    if not api_key:
        pytest.skip("FITPLATE_AI_PROVIDER_API_KEY is not set")
    if os.environ.get("FITPLATE_RUN_REAL_PROVIDER_TEST") != "1":
        pytest.skip("FITPLATE_RUN_REAL_PROVIDER_TEST=1 is not set")

    log_path = tmp_path / "model_runs.jsonl"
    monkeypatch.setattr(log_writer, "LOG_PATH", log_path)
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "openai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER_API_KEY", api_key)
    monkeypatch.setenv("FITPLATE_MONTHLY_COST_CAP_USD", "1.00")
    get_settings.cache_clear()

    response = client.post(
        "/api/v0/food/analyze",
        files={"image": ("tiny.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ai"
    assert body["schema_version"] == "food_analysis.v1"

    latest_log = log_path.read_text(encoding="utf-8").splitlines()[-1]
    record = json.loads(latest_log)
    assert record["cost_usd"] > 0
    assert record["model"] == get_settings().ai_model


def _tiny_png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
