"""Server-side calorie arithmetic for food analyses.

A model (or the mock) reports only what it can see: each item's name, grams,
food category or calorie density, and confidence. Every calorie number in a
FoodAnalysis is computed here with `calorie_range_from_density`, the same
function `POST /api/v0/food/corrections/mock` uses, so an analysis and a
correction with unchanged grams always agree.

`check_analysis_consistency` re-derives those numbers from a finished analysis
and lists every mismatch. Analyzers run it before returning.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.mock.density import (
    CALORIE_DENSITY_KCAL_PER_GRAM,
    calorie_range_from_density,
    sum_calorie_ranges,
)
from app.schemas.food import (
    AnalysisMode,
    CalorieRange,
    Confidence,
    FoodAnalysis,
    FoodItem,
    PortionEstimate,
    SafetyFlag,
)

FOOD_CATEGORIES: tuple[str, ...] = tuple(CALORIE_DENSITY_KCAL_PER_GRAM)
FALLBACK_CATEGORY = "generic_mixed_food"
# Pure fat is about 9 kcal/g; nothing edible is denser.
MAX_DENSITY_KCAL_PER_GRAM = 9.0
# Same ceiling as a user correction (FoodCorrectionMockRequest.corrected_grams).
MAX_ITEM_GRAMS = 2000


class ModelFoodItem(BaseModel):
    """One item as a model reports it. Calorie fields a model adds are ignored."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    grams: int = Field(ge=1, le=MAX_ITEM_GRAMS)
    category: str | None = None
    density_kcal_per_gram: float | None = Field(
        default=None,
        gt=0,
        le=MAX_DENSITY_KCAL_PER_GRAM,
    )
    confidence: Confidence


class ModelFoodOutput(BaseModel):
    """Everything a model is allowed to decide. No calories, counts or totals."""

    model_config = ConfigDict(extra="ignore")

    items: list[ModelFoodItem]
    uncertainty_notes: list[str]
    safety_flags: list[SafetyFlag]


class AnalysisConsistencyError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def resolve_density(item: ModelFoodItem) -> tuple[float, str]:
    """Return (kcal per gram, human-readable source). A known category wins."""
    if item.category in CALORIE_DENSITY_KCAL_PER_GRAM:
        density = CALORIE_DENSITY_KCAL_PER_GRAM[item.category]
        return density, f"Calorie density {density} kcal/g from category {item.category}."

    if item.density_kcal_per_gram is not None:
        density = item.density_kcal_per_gram
        return density, f"Calorie density {density} kcal/g estimated by the model."

    density = CALORIE_DENSITY_KCAL_PER_GRAM[FALLBACK_CATEGORY]
    return density, f"No known category or density; used {FALLBACK_CATEGORY} ({density} kcal/g)."


def build_food_item(item: ModelFoodItem, *, item_id: str) -> FoodItem:
    density, density_note = resolve_density(item)
    return FoodItem(
        item_id=item_id,
        name=item.name,
        portion=PortionEstimate(
            description=f"~{item.grams}g",
            grams_estimate=item.grams,
            assumptions=[density_note],
        ),
        calories=calorie_range_from_density(
            grams=item.grams,
            density=density,
            confidence=item.confidence,
        ),
        calorie_density_kcal_per_gram=density,
        confidence=item.confidence,
    )


def build_food_analysis(
    output: ModelFoodOutput,
    *,
    mode: AnalysisMode,
    analysis_id: str,
    analyzed_at: datetime,
    item_ids: list[str],
) -> FoodAnalysis:
    if len(item_ids) != len(output.items):
        raise ValueError("item_ids must have one id per item")

    items = [
        build_food_item(item, item_id=item_id)
        for item, item_id in zip(output.items, item_ids, strict=True)
    ]
    analysis = FoodAnalysis(
        analysis_id=analysis_id,
        schema_version="food_analysis.v1",
        mode=mode,
        analyzed_at=analyzed_at,
        items_count=len(items),
        items=items,
        total_calories=sum_calorie_ranges([item.calories for item in items]),
        uncertainty_notes=output.uncertainty_notes,
        safety_flags=output.safety_flags,
        user_corrections=[],
    )
    ensure_analysis_consistency(analysis)
    return analysis


def check_analysis_consistency(analysis: FoodAnalysis) -> list[str]:
    """Return every arithmetic mismatch in `analysis`; empty when consistent."""
    problems: list[str] = []

    if analysis.items_count != len(analysis.items):
        problems.append(
            f"items_count {analysis.items_count} != number of items {len(analysis.items)}"
        )

    for index, item in enumerate(analysis.items):
        label = f"items[{index}] ({item.name})"
        problems.extend(_range_order_problems(item.calories, label))
        expected = calorie_range_from_density(
            grams=item.portion.grams_estimate,
            density=item.calorie_density_kcal_per_gram,
            confidence=item.confidence,
        )
        if item.calories != expected:
            problems.append(
                f"{label} calories {_fmt(item.calories)} != "
                f"{item.portion.grams_estimate} g x {item.calorie_density_kcal_per_gram} kcal/g "
                f"at {item.confidence} confidence {_fmt(expected)}"
            )

    problems.extend(_range_order_problems(analysis.total_calories, "total_calories"))
    expected_total = sum_calorie_ranges([item.calories for item in analysis.items])
    if analysis.total_calories != expected_total:
        problems.append(
            f"total_calories {_fmt(analysis.total_calories)} != "
            f"sum of items {_fmt(expected_total)}"
        )

    return problems


def ensure_analysis_consistency(analysis: FoodAnalysis) -> None:
    problems = check_analysis_consistency(analysis)
    if problems:
        raise AnalysisConsistencyError(problems)


def _range_order_problems(calories: CalorieRange, label: str) -> list[str]:
    if calories.min <= calories.point_estimate <= calories.max:
        return []
    return [f"{label} point_estimate outside [min, max]: {_fmt(calories)}"]


def _fmt(calories: CalorieRange) -> str:
    return f"[{calories.min}, {calories.point_estimate}, {calories.max}]"
