"""POST /analyze/metadata is the canonical route; /analyze/mock is a deprecated alias.

The old name said "mock", but with FITPLATE_AI_MODE=ai the same handler calls the
configured AI provider. The alias must keep working with identical behavior, and
it must say it is deprecated so clients can migrate.
"""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.config import get_settings
from app.main import app

client = TestClient(app)

CANONICAL = "/api/v0/food/analyze/metadata"
ALIAS = "/api/v0/food/analyze/mock"


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch) -> Iterator[None]:
    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path / "model_runs.jsonl")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "filename": "lunch.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 345_678,
        "last_modified_ms": 1_710_000_000_000,
    }
    payload.update(overrides)
    return payload


def _stable(body: dict[str, object]) -> dict[str, object]:
    """Drop per-request ids and timestamps so two responses can be compared."""
    stable = dict(body)
    stable.pop("analysis_id")
    stable.pop("analyzed_at")
    stable["items"] = [
        {key: value for key, value in item.items() if key != "item_id"}
        for item in body["items"]  # type: ignore[union-attr]
    ]
    return stable


def _log_records(tmp_path) -> list[dict[str, object]]:
    lines = (tmp_path / "model_runs.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_canonical_and_alias_return_the_same_analysis() -> None:
    canonical = client.post(CANONICAL, json=_payload())
    alias = client.post(ALIAS, json=_payload())

    assert canonical.status_code == alias.status_code == 200
    assert _stable(canonical.json()) == _stable(alias.json())


def test_alias_sets_deprecation_headers_and_canonical_does_not() -> None:
    canonical = client.post(CANONICAL, json=_payload())
    alias = client.post(ALIAS, json=_payload())

    assert "deprecation" not in canonical.headers
    assert alias.headers["deprecation"] == "true"
    assert CANONICAL in alias.headers["link"]
    assert 'rel="successor-version"' in alias.headers["link"]


def test_alias_sets_deprecation_headers_on_error_responses() -> None:
    response = client.post(ALIAS, json=_payload(content_type="image/gif"))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_file_type"
    assert response.headers["deprecation"] == "true"


def test_logs_record_which_path_was_hit(tmp_path) -> None:
    client.post(CANONICAL, json=_payload())
    client.post(ALIAS, json=_payload())

    routes = [record["route"] for record in _log_records(tmp_path)]
    assert routes == [
        "POST /api/v0/food/analyze/metadata",
        "POST /api/v0/food/analyze/mock",
    ]


def test_alias_reaches_the_ai_analyzer_in_ai_mode(monkeypatch) -> None:
    # The reason for the rename: the "mock" path is not always a mock.
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "fake")
    get_settings.cache_clear()

    for path in (CANONICAL, ALIAS):
        response = client.post(path, json=_payload())
        assert response.status_code == 200
        assert response.json()["mode"] == "ai"


def test_openapi_marks_only_the_alias_deprecated() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert paths[ALIAS]["post"].get("deprecated") is True
    assert not paths[CANONICAL]["post"].get("deprecated", False)
