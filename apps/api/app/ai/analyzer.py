import os
from typing import ClassVar, Literal, Protocol, runtime_checkable

from app.mock.food_analyzer import analyze_food_metadata
from app.schemas.food import FoodAnalysis, FoodAnalyzeMockRequest


@runtime_checkable
class FoodAnalyzer(Protocol):
    mode: Literal["mock", "ai"]
    model: str

    def analyze(self, payload: FoodAnalyzeMockRequest) -> FoodAnalysis:
        ...


class MockFoodAnalyzer:
    mode: ClassVar[Literal["mock"]] = "mock"
    model: ClassVar[str] = "mock"

    def analyze(self, payload: FoodAnalyzeMockRequest) -> FoodAnalysis:
        return analyze_food_metadata(payload)


class AIFoodAnalyzer:
    mode: ClassVar[Literal["ai"]] = "ai"
    model: ClassVar[str] = "ai-provider-stub"

    def analyze(self, payload: FoodAnalyzeMockRequest) -> FoodAnalysis:
        raise NotImplementedError(
            "Real AI provider is not implemented yet. Use FITPLATE_AI_MODE=mock."
        )


def select_food_analyzer() -> FoodAnalyzer:
    mode = os.environ.get("FITPLATE_AI_MODE", "mock")

    if mode == "mock":
        return MockFoodAnalyzer()

    if mode == "ai":
        return AIFoodAnalyzer()

    raise ValueError(f"Unknown FITPLATE_AI_MODE {mode!r}. Expected 'mock' or 'ai'.")
