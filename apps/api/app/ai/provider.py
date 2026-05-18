from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, Protocol, runtime_checkable

from app.mock.density import (
    CALORIE_DENSITY_KCAL_PER_GRAM,
    calorie_range_for,
    sum_calorie_ranges,
)
from app.schemas.food import CalorieRange, Confidence, SafetyFlag

ScenarioItem = tuple[str, str, int, Confidence]

STANDARD_ITEMS: list[ScenarioItem] = [
    ("Chicken breast", "chicken_breast", 150, "medium"),
    ("Steamed rice", "rice_cooked", 200, "high"),
    ("Mixed salad", "mixed_salad", 80, "low"),
]

LOW_CONFIDENCE_ITEMS: list[ScenarioItem] = [
    ("Mixed entree", "generic_mixed_food", 220, "low"),
    ("Avocado", "avocado", 60, "low"),
]

COMPLEX_ITEMS: list[ScenarioItem] = [
    ("Salmon", "salmon", 130, "medium"),
    ("Pasta", "pasta_cooked", 170, "medium"),
    ("Beans", "beans", 100, "high"),
    ("Fried egg", "fried_egg", 50, "medium"),
    ("Tortilla", "tortilla", 40, "low"),
]


@dataclass(frozen=True)
class ImageRef:
    content_type: str
    size_bytes: int


@runtime_checkable
class AIProvider(Protocol):
    name: str
    model: str

    def call(self, prompt: str, image_ref: ImageRef) -> dict[str, object]:
        ...


class FakeAIProvider:
    name: ClassVar[str] = "fake"
    model: ClassVar[str] = "fake-food-vision-v1"

    def call(self, prompt: str, image_ref: ImageRef) -> dict[str, object]:
        if image_ref.size_bytes < 700_000:
            return _analysis_dict(
                items=_build_items(STANDARD_ITEMS),
                safety_flags=[],
                uncertainty_notes=[
                    "Portions are estimated from visible image context.",
                    "Cooking method is assumed to be standard.",
                ],
            )

        if image_ref.size_bytes < 800_000:
            return _analysis_dict(
                items=_build_items(LOW_CONFIDENCE_ITEMS),
                safety_flags=["low_confidence"],
                uncertainty_notes=[
                    "The image appears difficult to estimate from metadata alone.",
                    "Portion assumptions are intentionally broad.",
                ],
            )

        if image_ref.size_bytes < 900_000:
            return _analysis_dict(
                items=[],
                safety_flags=["non_food_image"],
                uncertainty_notes=["No food was detected in this fake AI scenario."],
            )

        return _analysis_dict(
            items=_build_items(COMPLEX_ITEMS),
            safety_flags=[],
            uncertainty_notes=[
                "Multiple foods are estimated separately.",
                "Mixed dishes can have wider uncertainty.",
            ],
        )


def _analysis_dict(
    *,
    items: list[dict[str, object]],
    safety_flags: list[SafetyFlag],
    uncertainty_notes: list[str],
) -> dict[str, object]:
    calories = sum_calorie_ranges(
        [CalorieRange.model_validate(item["calories"]) for item in items]
    )

    return {
        "analysis_id": "00000000-0000-4000-8000-000000000000",
        "schema_version": "food_analysis.v1",
        "mode": "ai",
        "analyzed_at": datetime(2000, 1, 1, tzinfo=UTC).isoformat(),
        "items_count": len(items),
        "items": items,
        "total_calories": calories.model_dump(),
        "uncertainty_notes": uncertainty_notes,
        "safety_flags": safety_flags,
        "user_corrections": [],
    }


def _build_items(scenario_items: list[ScenarioItem]) -> list[dict[str, object]]:
    return [
        _build_item(
            index=index,
            name=name,
            density_key=density_key,
            grams=grams,
            confidence=confidence,
        )
        for index, (name, density_key, grams, confidence) in enumerate(
            scenario_items,
            start=1,
        )
    ]


def _build_item(
    *,
    index: int,
    name: str,
    density_key: str,
    grams: int,
    confidence: Confidence,
) -> dict[str, object]:
    calories = calorie_range_for(
        grams=grams,
        density_key=density_key,
        confidence=confidence,
    )

    return {
        "item_id": f"fake-item-{index}",
        "name": name,
        "portion": {
            "description": f"~{grams}g",
            "grams_estimate": grams,
            "assumptions": ["Portion estimated from visible plate size."],
        },
        "calories": calories.model_dump(),
        "calorie_density_kcal_per_gram": CALORIE_DENSITY_KCAL_PER_GRAM[density_key],
        "confidence": confidence,
    }
