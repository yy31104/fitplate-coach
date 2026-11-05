import pytest

from app.ai.prompts import ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION, get_prompt
from app.nutrition import FOOD_CATEGORIES


def test_prompt_registry_keeps_food_analysis_v1_as_deprecated() -> None:
    record = get_prompt("food_analysis", "v1")

    assert record.name == "food_analysis"
    assert record.version == "v1"
    assert record.status == "deprecated"


def test_prompt_registry_keeps_food_analysis_v2_as_deprecated() -> None:
    assert get_prompt("food_analysis", "v2").status == "deprecated"


def test_active_food_analysis_prompt_is_v3() -> None:
    record = get_prompt("food_analysis", ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION)

    assert ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION == "v3"
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


def test_active_prompt_lists_exactly_the_server_categories() -> None:
    """The prompt's category list must match the density table the server uses."""
    body = get_prompt("food_analysis", ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION).body
    listed = body.split("Categories:", 1)[1].split("\n\n", 1)[0]
    names = {name.strip().rstrip(".") for name in listed.replace("\n", " ").split(",")}

    assert names == set(FOOD_CATEGORIES)


def test_active_prompt_does_not_ask_the_model_for_calorie_numbers() -> None:
    body = get_prompt("food_analysis", ACTIVE_FOOD_ANALYSIS_PROMPT_VERSION).body

    assert "Do not return calories" in body
    assert "total_calories" not in body
    assert "items_count" not in body
