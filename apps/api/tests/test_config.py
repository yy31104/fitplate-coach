import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_defaults(monkeypatch) -> None:
    _clear_settings_env(monkeypatch)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.ai_mode == "mock"
    assert settings.ai_provider == "fake"
    assert settings.ai_model == "gpt-5.4-mini"
    assert settings.ai_provider_api_key is None
    assert settings.monthly_cost_cap_usd == 0.0
    assert settings.ai_request_timeout_seconds == 30


def test_settings_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "fake")
    monkeypatch.setenv("FITPLATE_AI_MODEL", "gpt-test-model")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER_API_KEY", "test-key")
    monkeypatch.setenv("FITPLATE_MONTHLY_COST_CAP_USD", "12.5")
    monkeypatch.setenv("FITPLATE_AI_REQUEST_TIMEOUT_SECONDS", "45")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.ai_mode == "ai"
    assert settings.ai_provider == "fake"
    assert settings.ai_model == "gpt-test-model"
    assert settings.ai_provider_api_key == "test-key"
    assert settings.monthly_cost_cap_usd == 12.5
    assert settings.ai_request_timeout_seconds == 45


def test_settings_cache_can_be_cleared(monkeypatch) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("FITPLATE_AI_MODE", "mock")
    get_settings.cache_clear()
    assert get_settings().ai_mode == "mock"

    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    assert get_settings().ai_mode == "mock"

    get_settings.cache_clear()
    assert get_settings().ai_mode == "ai"


def _clear_settings_env(monkeypatch) -> None:
    for name in [
        "FITPLATE_AI_MODE",
        "FITPLATE_AI_PROVIDER",
        "FITPLATE_AI_MODEL",
        "FITPLATE_AI_PROVIDER_API_KEY",
        "FITPLATE_MONTHLY_COST_CAP_USD",
        "FITPLATE_AI_REQUEST_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)
