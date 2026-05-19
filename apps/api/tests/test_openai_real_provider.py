import binascii
import json
import os
import struct
import zlib

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
        files={"image": ("food-test.png", _food_like_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ai"
    assert body["schema_version"] == "food_analysis.v1"

    latest_log = log_path.read_text(encoding="utf-8").splitlines()[-1]
    record = json.loads(latest_log)
    assert record["cost_usd"] > 0
    assert record["model"] == get_settings().ai_model


def _food_like_png_bytes() -> bytes:
    width = 128
    height = 128
    rows = bytearray()

    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(_pixel_rgb(x, y))

    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _pixel_rgb(x: int, y: int) -> tuple[int, int, int]:
    plate_distance = (x - 64) ** 2 + (y - 68) ** 2
    food_distance = (x - 64) ** 2 + (y - 60) ** 2

    if plate_distance > 48**2:
        return (245, 241, 232)
    if plate_distance > 43**2:
        return (218, 212, 199)
    if food_distance < 32**2:
        if x < 56 and y < 66:
            return (61, 130, 77)
        if x > 76 and y > 52:
            return (226, 169, 67)
        if y > 72:
            return (238, 232, 205)
        return (203, 104, 58)
    return (250, 248, 240)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)
