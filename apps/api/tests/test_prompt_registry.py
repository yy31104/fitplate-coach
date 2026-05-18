import pytest

from app.ai.prompts import get_prompt


def test_prompt_registry_loads_food_analysis_v1() -> None:
    record = get_prompt("food_analysis", "v1")

    assert record.name == "food_analysis"
    assert record.version == "v1"
    assert record.status == "active"


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
