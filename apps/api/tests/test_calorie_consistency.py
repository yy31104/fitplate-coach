"""Calorie numbers are computed by the server, never taken from the model.

A provider reports names, grams, category or density, and confidence. The
analyzer computes each item's range with `calorie_range_from_density` (the
function the correction route uses), then items_count and total_calories.
`check_analysis_consistency` re-derives those numbers and lists mismatches.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.observability.log_writer as log_writer
from app.ai.analyzer import AIFoodAnalyzer, MockFoodAnalyzer
from app.ai.provider import AIAnalysisError, FakeAIProvider, ImageRef, ProviderResult
from app.config import get_settings
from app.evaluation.runner import EvaluationCase, evaluate_food_analysis_cases
from app.main import app
from app.mock.density import CALORIE_DENSITY_KCAL_PER_GRAM
from app.nutrition import (
    AnalysisConsistencyError,
    ModelFoodItem,
    check_analysis_consistency,
    ensure_analysis_consistency,
    resolve_density,
)
from app.schemas.food import CalorieRange, FoodAnalysis, FoodAnalyzeMockRequest

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch) -> Iterator[None]:
    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path / "model_runs.jsonl")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class StubProvider:
    """Returns a fixed raw output; works from metadata like the fake."""

    name = "stub"
    model = "stub-model"
    requires_image_bytes = False

    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        return ProviderResult(raw_analysis=self.raw, input_tokens=0, output_tokens=0, cost_usd=0.0)


def _payload(size_bytes: int = 345_678) -> FoodAnalyzeMockRequest:
    return FoodAnalyzeMockRequest(
        filename="lunch.jpg",
        content_type="image/jpeg",
        size_bytes=size_bytes,
        last_modified_ms=1_710_000_000_000,
    )


def _item(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "name": "Chicken breast",
        "grams": 150,
        "category": "chicken_breast",
        "density_kcal_per_gram": None,
        "confidence": "medium",
    }
    item.update(overrides)
    return item


def _raw(*items: dict[str, object], **extra: object) -> dict[str, object]:
    return {"items": list(items), "uncertainty_notes": [], "safety_flags": [], **extra}


def _analyze(raw: dict[str, object]) -> FoodAnalysis:
    return AIFoodAnalyzer(provider=StubProvider(raw)).analyze(_payload()).analysis


def _consistent_analysis() -> FoodAnalysis:
    return _analyze(_raw(_item(), _item(name="Steamed rice", grams=200, category="rice_cooked")))


# --- the server ignores calorie numbers a provider sends ----------------------


def test_provider_calorie_numbers_are_ignored_and_recomputed() -> None:
    raw = _raw(
        _item(calories={"min": 1, "max": 2, "point_estimate": 99_999}),
        items_count=7,
        total_calories={"min": 0, "max": 0, "point_estimate": 0},
    )

    analysis = _analyze(raw)

    # 150 g x 1.65 kcal/g = 247.5 -> 248; medium confidence = +/-20 %.
    assert analysis.items[0].calories == CalorieRange(min=198, max=298, point_estimate=248)
    assert analysis.items_count == 1
    assert analysis.total_calories == analysis.items[0].calories
    assert check_analysis_consistency(analysis) == []


def test_items_count_and_total_follow_the_items() -> None:
    analysis = _consistent_analysis()

    assert analysis.items_count == len(analysis.items) == 2
    assert analysis.total_calories == CalorieRange(
        min=sum(item.calories.min for item in analysis.items),
        max=sum(item.calories.max for item in analysis.items),
        point_estimate=sum(item.calories.point_estimate for item in analysis.items),
    )


def test_empty_items_give_zero_total() -> None:
    analysis = _analyze(_raw(safety_flags=["non_food_image"]))

    assert analysis.items_count == 0
    assert analysis.total_calories == CalorieRange(min=0, max=0, point_estimate=0)


# --- density resolution -----------------------------------------------------


def test_known_category_wins_over_model_density() -> None:
    density, note = resolve_density(
        ModelFoodItem(name="Rice", grams=100, category="rice_cooked", density_kcal_per_gram=8.0, confidence="high")
    )

    assert density == CALORIE_DENSITY_KCAL_PER_GRAM["rice_cooked"]
    assert "category rice_cooked" in note


def test_model_density_is_used_when_category_is_null_or_unknown() -> None:
    for category in (None, "dumplings"):
        density, note = resolve_density(
            ModelFoodItem(name="Dumplings", grams=100, category=category, density_kcal_per_gram=2.2, confidence="low")
        )
        assert density == 2.2
        assert "estimated by the model" in note


def test_no_category_and_no_density_falls_back_to_generic() -> None:
    density, _ = resolve_density(ModelFoodItem(name="Stew", grams=100, confidence="low"))

    assert density == CALORIE_DENSITY_KCAL_PER_GRAM["generic_mixed_food"]


def test_density_source_is_shown_in_item_assumptions() -> None:
    analysis = _analyze(_raw(_item(category=None, density_kcal_per_gram=2.5)))

    assert analysis.items[0].calorie_density_kcal_per_gram == 2.5
    assert analysis.items[0].portion.assumptions == [
        "Calorie density 2.5 kcal/g estimated by the model."
    ]


@pytest.mark.parametrize(
    "bad_item",
    [
        _item(grams=0),
        _item(grams=2001),
        _item(category=None, density_kcal_per_gram=0),
        _item(category=None, density_kcal_per_gram=9.5),
        _item(name=""),
        _item(confidence="certain"),
    ],
)
def test_out_of_range_model_values_are_rejected(bad_item: dict[str, object]) -> None:
    with pytest.raises(AIAnalysisError) as exc:
        _analyze(_raw(bad_item))

    assert exc.value.safety_flags == ["schema_validation_failed"]


# --- analysis and correction use the same function --------------------------


@pytest.mark.parametrize("size_bytes", [345_678, 745_678, 945_678])
def test_correction_with_unchanged_grams_reproduces_every_ai_item(size_bytes: int) -> None:
    analysis = AIFoodAnalyzer(provider=FakeAIProvider()).analyze(_payload(size_bytes)).analysis
    assert analysis.items

    for item in analysis.items:
        assert _correct(item.model_dump(), item.portion.grams_estimate) == item.calories.model_dump()


def test_correction_with_unchanged_grams_reproduces_every_mock_item() -> None:
    analysis = MockFoodAnalyzer().analyze(_payload()).analysis

    for item in analysis.items:
        assert _correct(item.model_dump(), item.portion.grams_estimate) == item.calories.model_dump()


def _correct(item: dict[str, object], grams: int) -> dict[str, object]:
    response = client.post(
        "/api/v0/food/corrections/mock",
        json={
            "item_id": item["item_id"],
            "original_name": item["name"],
            "original_grams": item["portion"]["grams_estimate"],  # type: ignore[index]
            "corrected_grams": grams,
            "calorie_density_kcal_per_gram": item["calorie_density_kcal_per_gram"],
            "confidence": item["confidence"],
            "original_calories": item["calories"],
        },
    )
    assert response.status_code == 200
    return response.json()["corrected_calories"]


# --- check_analysis_consistency catches each kind of mismatch -----------------


def test_consistent_analysis_has_no_problems() -> None:
    analysis = _consistent_analysis()

    assert check_analysis_consistency(analysis) == []
    ensure_analysis_consistency(analysis)


def test_items_count_mismatch_is_reported() -> None:
    analysis = _consistent_analysis().model_copy(update={"items_count": 3})

    assert check_analysis_consistency(analysis) == ["items_count 3 != number of items 2"]


def test_total_mismatch_is_reported() -> None:
    analysis = _consistent_analysis()
    wrong_total = analysis.total_calories.model_copy(
        update={"point_estimate": analysis.total_calories.point_estimate + 1}
    )

    problems = check_analysis_consistency(analysis.model_copy(update={"total_calories": wrong_total}))

    assert len(problems) == 1
    assert problems[0].startswith("total_calories ")
    assert "!= sum of items" in problems[0]


def test_total_point_estimate_outside_range_is_reported() -> None:
    analysis = _consistent_analysis()
    total = analysis.total_calories
    bad_total = total.model_copy(update={"point_estimate": total.max + 1})

    problems = check_analysis_consistency(analysis.model_copy(update={"total_calories": bad_total}))

    assert "total_calories point_estimate outside [min, max]" in problems[0]


def test_item_point_estimate_outside_range_is_reported() -> None:
    analysis = _consistent_analysis()
    first = analysis.items[0]
    bad_calories = first.calories.model_copy(update={"point_estimate": first.calories.min - 1})
    bad_item = first.model_copy(update={"calories": bad_calories})

    problems = check_analysis_consistency(
        analysis.model_copy(update={"items": [bad_item, *analysis.items[1:]]})
    )

    assert any("items[0] (Chicken breast) point_estimate outside [min, max]" in p for p in problems)


def test_item_calories_that_do_not_match_grams_times_density_are_reported() -> None:
    analysis = _consistent_analysis()
    first = analysis.items[0]
    bigger = first.portion.model_copy(update={"grams_estimate": first.portion.grams_estimate * 2})
    bad_item = first.model_copy(update={"portion": bigger})

    problems = check_analysis_consistency(
        analysis.model_copy(update={"items": [bad_item, *analysis.items[1:]]})
    )

    assert problems == [
        "items[0] (Chicken breast) calories [198, 248, 298] != "
        "300 g x 1.65 kcal/g at medium confidence [396, 495, 594]"
    ]


def test_ensure_raises_with_every_problem() -> None:
    analysis = _consistent_analysis().model_copy(update={"items_count": 0})

    with pytest.raises(AnalysisConsistencyError) as exc:
        ensure_analysis_consistency(analysis)

    assert exc.value.problems == ["items_count 0 != number of items 2"]


def test_evaluation_marks_inconsistent_analysis_as_failed() -> None:
    inconsistent = _consistent_analysis().model_copy(update={"items_count": 5})
    case = EvaluationCase.model_validate(
        {
            "case_id": "inconsistent",
            "description": "items_count disagrees with items",
            "input": _payload().model_dump(),
            "expected_summary": {
                "items_count": 5,
                "item_names": ["Chicken breast", "Steamed rice"],
                "safety_flags": [],
                "total_calories": {"min_at_least": 0, "max_at_most": 10_000},
            },
        }
    )

    result = evaluate_food_analysis_cases([case], analyzer=lambda payload: inconsistent)

    assert result.failed == 1
    assert result.cases[0].diffs == ["consistency: items_count 5 != number of items 2"]


# --- through the HTTP route ---------------------------------------------------


def test_route_returns_server_computed_numbers_in_ai_mode(monkeypatch) -> None:
    monkeypatch.setenv("FITPLATE_AI_MODE", "ai")
    monkeypatch.setenv("FITPLATE_AI_PROVIDER", "fake")
    get_settings.cache_clear()

    response = client.post(
        "/api/v0/food/analyze/mock",
        json=_payload().model_dump(),
    )

    assert response.status_code == 200
    analysis = FoodAnalysis.model_validate(response.json())
    assert analysis.mode == "ai"
    assert check_analysis_consistency(analysis) == []
