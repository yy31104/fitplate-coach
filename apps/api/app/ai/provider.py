from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from app.schemas.food import Confidence, SafetyFlag

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
    data: bytes = b""


@dataclass(frozen=True)
class ProviderResult:
    raw_analysis: dict[str, object]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    provider_latency_ms: int | None = None


class AIAnalysisError(Exception):
    def __init__(
        self,
        message: str,
        safety_flags: list[SafetyFlag] | None = None,
    ) -> None:
        super().__init__(message)
        self.safety_flags = (
            safety_flags if safety_flags is not None else ["schema_validation_failed"]
        )


class ImageRequiredError(AIAnalysisError):
    """Raised before a provider call when the provider needs image bytes and has none."""

    def __init__(self, message: str) -> None:
        super().__init__(message, safety_flags=[])


@runtime_checkable
class AIProvider(Protocol):
    name: str
    model: str

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        ...


class FakeAIProvider:
    name: ClassVar[str] = "fake"
    model: ClassVar[str] = "fake-food-vision-v1"
    # The fake chooses a scenario from file metadata, so it can run without bytes.
    requires_image_bytes: ClassVar[bool] = False

    def call(self, prompt: str, image_ref: ImageRef) -> ProviderResult:
        if image_ref.size_bytes < 700_000:
            return _provider_result(
                _analysis_dict(
                    items=_build_items(STANDARD_ITEMS),
                    safety_flags=[],
                    uncertainty_notes=[
                        "Portions are estimated from visible image context.",
                        "Cooking method is assumed to be standard.",
                    ],
                )
            )

        if image_ref.size_bytes < 800_000:
            return _provider_result(
                _analysis_dict(
                    items=_build_items(LOW_CONFIDENCE_ITEMS),
                    safety_flags=["low_confidence"],
                    uncertainty_notes=[
                        "The image appears difficult to estimate from metadata alone.",
                        "Portion assumptions are intentionally broad.",
                    ],
                )
            )

        if image_ref.size_bytes < 900_000:
            return _provider_result(
                _analysis_dict(
                    items=[],
                    safety_flags=["non_food_image"],
                    uncertainty_notes=["No food was detected in this fake AI scenario."],
                )
            )

        return _provider_result(
            _analysis_dict(
                items=_build_items(COMPLEX_ITEMS),
                safety_flags=[],
                uncertainty_notes=[
                    "Multiple foods are estimated separately.",
                    "Mixed dishes can have wider uncertainty.",
                ],
            )
        )


def _provider_result(raw_analysis: dict[str, object]) -> ProviderResult:
    return ProviderResult(
        raw_analysis=raw_analysis,
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
    )


def _analysis_dict(
    *,
    items: list[dict[str, object]],
    safety_flags: list[SafetyFlag],
    uncertainty_notes: list[str],
) -> dict[str, object]:
    # The same shape the real provider's strict schema allows: no calories,
    # counts or totals. The analyzer computes those.
    return {
        "items": items,
        "uncertainty_notes": uncertainty_notes,
        "safety_flags": safety_flags,
    }


def _build_items(scenario_items: list[ScenarioItem]) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "grams": grams,
            "category": category,
            "density_kcal_per_gram": None,
            "confidence": confidence,
        }
        for name, category, grams, confidence in scenario_items
    ]
