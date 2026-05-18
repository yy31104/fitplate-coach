from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_correction_returns_200() -> None:
    response = client.post("/api/v0/food/corrections/mock", json=_payload())

    assert response.status_code == 200


def test_correction_response_schema_fields_present() -> None:
    response = client.post("/api/v0/food/corrections/mock", json=_payload())

    body = response.json()

    assert response.status_code == 200
    assert {
        "correction_id",
        "item_id",
        "original_name",
        "corrected_name",
        "original_grams",
        "corrected_grams",
        "original_calories",
        "corrected_calories",
        "correction_timestamp",
        "correction_source",
    }.issubset(body.keys())


def test_correction_recomputes_calories_correctly() -> None:
    response = client.post("/api/v0/food/corrections/mock", json=_payload())

    assert response.json()["corrected_calories"] == {
        "min": 264,
        "max": 396,
        "point_estimate": 330,
    }


def test_correction_confidence_margins_high() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(
            corrected_grams=100,
            calorie_density_kcal_per_gram=1.30,
            confidence="high",
        ),
    )

    assert response.json()["corrected_calories"] == {
        "min": 117,
        "max": 143,
        "point_estimate": 130,
    }


def test_correction_confidence_margins_low() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(
            corrected_grams=80,
            calorie_density_kcal_per_gram=0.35,
            confidence="low",
        ),
    )

    assert response.json()["corrected_calories"] == {
        "min": 20,
        "max": 36,
        "point_estimate": 28,
    }


def test_correction_preserves_original_calories() -> None:
    payload = _payload()
    response = client.post("/api/v0/food/corrections/mock", json=payload)

    assert response.json()["original_calories"] == payload["original_calories"]


def test_correction_preserves_original_grams() -> None:
    payload = _payload()
    response = client.post("/api/v0/food/corrections/mock", json=payload)

    assert response.json()["original_grams"] == payload["original_grams"]


def test_correction_corrected_name_equals_original_name() -> None:
    payload = _payload()
    response = client.post("/api/v0/food/corrections/mock", json=payload)

    assert response.json()["corrected_name"] == payload["original_name"]


def test_correction_source_is_user() -> None:
    response = client.post("/api/v0/food/corrections/mock", json=_payload())

    assert response.json()["correction_source"] == "user"


def test_correction_id_unique_across_calls() -> None:
    payload = _payload()

    first = client.post("/api/v0/food/corrections/mock", json=payload).json()
    second = client.post("/api/v0/food/corrections/mock", json=payload).json()

    assert first["correction_id"] != second["correction_id"]


def test_correction_timestamp_exists_and_is_iso_datetime() -> None:
    response = client.post("/api/v0/food/corrections/mock", json=_payload())

    timestamp = response.json()["correction_timestamp"]
    parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    assert parsed_timestamp.tzinfo is not None


def test_correction_item_id_passed_through() -> None:
    payload = _payload(item_id="custom-item-id")
    response = client.post("/api/v0/food/corrections/mock", json=payload)

    assert response.json()["item_id"] == "custom-item-id"


def test_correction_rejects_zero_original_grams() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(original_grams=0),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("corrected_grams", [0, -1, 2001])
def test_correction_rejects_invalid_corrected_grams(corrected_grams: int) -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(corrected_grams=corrected_grams),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("density", [0, -1.0])
def test_correction_rejects_invalid_density(density: float) -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(calorie_density_kcal_per_gram=density),
    )

    assert response.status_code == 422


def test_correction_rejects_invalid_confidence() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(confidence="very_high"),
    )

    assert response.status_code == 422


def test_correction_rejects_empty_item_id() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(item_id=""),
    )

    assert response.status_code == 422


def test_correction_rejects_empty_original_name() -> None:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json=_payload(original_name=""),
    )

    assert response.status_code == 422


def test_correction_rejects_missing_required_field() -> None:
    payload = _payload()
    del payload["corrected_grams"]

    response = client.post("/api/v0/food/corrections/mock", json=payload)

    assert response.status_code == 422


def _payload(
    item_id: str = "test-item-id-001",
    original_name: str = "Chicken breast",
    original_grams: int = 150,
    corrected_grams: int = 200,
    calorie_density_kcal_per_gram: float = 1.65,
    confidence: str = "medium",
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "original_name": original_name,
        "original_grams": original_grams,
        "corrected_grams": corrected_grams,
        "calorie_density_kcal_per_gram": calorie_density_kcal_per_gram,
        "confidence": confidence,
        "original_calories": {
            "min": 198,
            "max": 298,
            "point_estimate": 248,
        },
    }
