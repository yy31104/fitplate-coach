import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/v0/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fitplate-api",
        "version": "0.1.0",
    }


def test_unknown_api_route_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/v0/nonexistent")

    assert response.status_code == 404


def test_health_endpoint_rejects_post() -> None:
    client = TestClient(app)

    response = client.post("/api/v0/health")

    assert response.status_code == 405


@pytest.mark.parametrize(
    "origin",
    ["http://127.0.0.1:3000", "http://localhost:3000"],
)
def test_local_web_origins_are_allowed_for_cors(origin: str) -> None:
    client = TestClient(app)

    response = client.options(
        "/api/v0/food/analyze/mock",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
