import pytest

from app.ai.prompts import ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION, get_prompt


def test_prompt_registry_keeps_food_analysis_v1_as_deprecated() -> None:
    record = get_prompt("food_analysis", "v1")

    assert record.name == "food_analysis"
    assert record.version == "v1"
    assert record.status == "deprecated"


def test_active_food_analysis_prompt_is_v2() -> None:
    record = get_prompt("food_analysis", ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION)

    assert ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION == "v2"
    assert record.status == "active"
    assert record.schema_version == "food_analysis.v1"


def test_active_prompt_has_no_stale_integration_notes() -> None:
    """v1 told the real provider it was a "future" prompt that no route calls."""
    body = get_prompt("food_analysis", ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION).body.lower()

    assert "future" not in body
    assert "mock route" not in body
    assert "does not call this prompt" not in body


def test_get_prompt_body_is_non_empty() -> None:
    record = get_prompt("food_analysis", "v1")

    assert len(record.body.strip()) > 0


def test_get_prompt_schema_version_is_food_analysis_v1() -> None:
    record = get_prompt("food_analysis", "v1")

    assert record.schema_version == "food_analysis.v1"


def test_get_prompt_raises_for_unknown_name() -> None:
    with pytest.raises(KeyError, match="exercise_analysis"):
        get_prompt("exercise_analysis", "v1")


def test_get_prompt_raises_for_unknown_version() -> None:
    with pytest.raises(KeyError, match="v99"):
        get_prompt("food_analysis", "v99")
