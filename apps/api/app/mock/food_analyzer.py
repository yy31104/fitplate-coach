from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.mock.density import (
    CALORIE_DENSITY_KCAL_PER_GRAM,
    calorie_range_for,
    sum_calorie_ranges,
)
from app.schemas.food import (
    Confidence,
    FoodAnalysis,
    FoodAnalyzeMockRequest,
    FoodItem,
    PortionEstimate,
    SafetyFlag,
)

SCHEMA_VERSION = "food_analysis.v1"

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


def scenario_bucket(filename: str) -> int:
    return sha256(filename.encode("utf-8")).digest()[0] % 10


def analyze_food_metadata(payload: FoodAnalyzeMockRequest) -> FoodAnalysis:
    bucket = scenario_bucket(payload.filename)

    if bucket <= 6:
        items = _build_items(STANDARD_ITEMS)
        flags: list[SafetyFlag] = []
        notes = [
            "Portions are estimated from visible image context.",
            "Cooking method is assumed to be standard.",
        ]
    elif bucket == 7:
        items = _build_items(LOW_CONFIDENCE_ITEMS)
        flags = ["low_confidence"]
        notes = [
            "The image appears difficult to estimate from metadata alone.",
            "Portion assumptions are intentionally broad.",
        ]
    elif bucket == 8:
        items = []
        flags = ["non_food_image"]
        notes = ["No food was detected in this mock scenario."]
    else:
        items = _build_items(COMPLEX_ITEMS)
        flags = []
        notes = [
            "Multiple foods are estimated separately.",
            "Mixed dishes can have wider uncertainty.",
        ]

    total = sum_calorie_ranges([item.calories for item in items])

    return FoodAnalysis(
        analysis_id=str(uuid4()),
        schema_version=SCHEMA_VERSION,
        mode="mock",
        analyzed_at=datetime.now(UTC),
        items_count=len(items),
        items=items,
        total_calories=total,
        uncertainty_notes=notes,
        safety_flags=flags,
        user_corrections=[],
    )


def _build_items(scenario_items: list[ScenarioItem]) -> list[FoodItem]:
    return [
        _build_item(name=name, density_key=density_key, grams=grams, confidence=confidence)
        for name, density_key, grams, confidence in scenario_items
    ]


def _build_item(
    name: str,
    density_key: str,
    grams: int,
    confidence: Confidence,
) -> FoodItem:
    calories = calorie_range_for(grams=grams, density_key=density_key, confidence=confidence)
    density = CALORIE_DENSITY_KCAL_PER_GRAM[density_key]

    return FoodItem(
        item_id=str(uuid4()),
        name=name,
        portion=PortionEstimate(
            description=f"~{grams}g",
            grams_estimate=grams,
            assumptions=["Portion estimated from visible plate size."],
        ),
        calories=calories,
        calorie_density_kcal_per_gram=density,
        confidence=confidence,
    )
