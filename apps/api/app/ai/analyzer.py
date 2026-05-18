from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, Literal, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import ValidationError

from app.ai.prompts import PromptRecord, get_prompt
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIAnalysisError, AIProvider, FakeAIProvider, ImageRef
from app.config import get_settings
from app.mock.food_analyzer import analyze_food_metadata
from app.schemas.food import FoodAnalysis, FoodAnalyzeMockRequest


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class AnalyzerResult:
    analysis: FoodAnalysis
    usage: ProviderUsage


@runtime_checkable
class FoodAnalyzer(Protocol):
    mode: Literal["mock", "ai"]
    model: str

    def analyze(
        self,
        payload: FoodAnalyzeMockRequest,
        *,
        image_ref: ImageRef | None = None,
    ) -> AnalyzerResult:
        ...


class MockFoodAnalyzer:
    mode: ClassVar[Literal["mock"]] = "mock"
    model: ClassVar[str] = "mock"

    def analyze(
        self,
        payload: FoodAnalyzeMockRequest,
        *,
        image_ref: ImageRef | None = None,
    ) -> AnalyzerResult:
        return AnalyzerResult(
            analysis=analyze_food_metadata(payload),
            usage=ProviderUsage(input_tokens=0, output_tokens=0, cost_usd=0.0),
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

    def analyze(
        self,
        payload: FoodAnalyzeMockRequest,
        *,
        image_ref: ImageRef | None = None,
    ) -> AnalyzerResult:
        effective_image_ref = image_ref or ImageRef(
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
        provider_result = self.provider.call(self.prompt_record.body, effective_image_ref)

        try:
            analysis = FoodAnalysis.model_validate(provider_result.raw_analysis)
        except ValidationError as exc:
            raise AIAnalysisError("AI provider returned invalid food analysis output.") from exc

        return AnalyzerResult(
            analysis=analysis.model_copy(
                update={
                    "analysis_id": str(uuid4()),
                    "schema_version": "food_analysis.v1",
                    "mode": "ai",
                    "analyzed_at": datetime.now(UTC),
                }
            ),
            usage=ProviderUsage(
                input_tokens=provider_result.input_tokens,
                output_tokens=provider_result.output_tokens,
                cost_usd=provider_result.cost_usd,
            ),
        )


def select_food_analyzer() -> FoodAnalyzer:
    settings = get_settings()
    mode = settings.ai_mode

    if mode == "mock":
        return MockFoodAnalyzer()

    if mode == "ai":
        if settings.ai_provider == "fake":
            return AIFoodAnalyzer(provider=FakeAIProvider())
        if settings.ai_provider == "openai":
            if not settings.ai_provider_api_key:
                raise ValueError(
                    "FITPLATE_AI_PROVIDER_API_KEY is required for OpenAI provider."
                )
            return AIFoodAnalyzer(
                provider=OpenAIProvider(
                    api_key=settings.ai_provider_api_key,
                    model=settings.ai_model,
                    timeout_seconds=settings.ai_request_timeout_seconds,
                )
            )
        raise ValueError(
            f"Unknown FITPLATE_AI_PROVIDER {settings.ai_provider!r}. Expected 'fake' or 'openai'."
        )

    raise ValueError(f"Unknown FITPLATE_AI_MODE {mode!r}. Expected 'mock' or 'ai'.")
