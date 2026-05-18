from datetime import UTC, datetime
from typing import ClassVar, Literal, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import ValidationError

from app.ai.prompts import PromptRecord, get_prompt
from app.ai.provider import AIProvider, FakeAIProvider, ImageRef
from app.config import get_settings
from app.mock.food_analyzer import analyze_food_metadata
from app.schemas.food import FoodAnalysis, FoodAnalyzeMockRequest, SafetyFlag


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


class AIFoodAnalyzer:
    mode: ClassVar[Literal["ai"]] = "ai"

    def __init__(
        self,
        provider: AIProvider | None = None,
        prompt_record: PromptRecord | None = None,
    ) -> None:
        self.provider = provider if provider is not None else FakeAIProvider()
        self.prompt_record = (
            prompt_record
            if prompt_record is not None
            else get_prompt("food_analysis", "v1")
        )

    @property
    def model(self) -> str:
        return self.provider.model

    @property
    def prompt_name(self) -> str:
        return self.prompt_record.name

    @property
    def prompt_version(self) -> str:
        return self.prompt_record.version

    def analyze(self, payload: FoodAnalyzeMockRequest) -> FoodAnalysis:
        image_ref = ImageRef(
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
        raw_analysis = self.provider.call(self.prompt_record.body, image_ref)

        try:
            analysis = FoodAnalysis.model_validate(raw_analysis)
        except ValidationError as exc:
            raise AIAnalysisError("AI provider returned invalid food analysis output.") from exc

        return analysis.model_copy(
            update={
                "analysis_id": str(uuid4()),
                "schema_version": "food_analysis.v1",
                "mode": "ai",
                "analyzed_at": datetime.now(UTC),
            }
        )


def select_food_analyzer() -> FoodAnalyzer:
    settings = get_settings()
    mode = settings.ai_mode

    if mode == "mock":
        return MockFoodAnalyzer()

    if mode == "ai":
        if settings.ai_provider != "fake":
            raise ValueError(
                f"Unknown FITPLATE_AI_PROVIDER {settings.ai_provider!r}. Expected 'fake'."
            )
        return AIFoodAnalyzer(provider=FakeAIProvider())

    raise ValueError(f"Unknown FITPLATE_AI_MODE {mode!r}. Expected 'mock' or 'ai'.")
