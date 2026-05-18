import json
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import BaseModel

from app.ai.analyzer import AIFoodAnalyzer, AnalyzerResult, MockFoodAnalyzer
from app.ai.provider import FakeAIProvider
from app.schemas.food import FoodAnalysis, FoodAnalyzeMockRequest, SafetyFlag

_CASES_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "food_analysis" / "cases.json"


class TotalCalorieExpectation(BaseModel):
    min_at_least: int
    max_at_most: int


class ExpectedSummary(BaseModel):
    items_count: int
    item_names: list[str]
    safety_flags: list[SafetyFlag]
    total_calories: TotalCalorieExpectation


class EvaluationCase(BaseModel):
    case_id: str
    description: str
    input: FoodAnalyzeMockRequest
    expected_summary: ExpectedSummary


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    diffs: list[str]


class EvaluationResult(BaseModel):
    schema_version: Literal["evaluation.v1"]
    total: int
    passed: int
    failed: int
    cases: list[CaseResult]


class FoodAnalysisCallable(Protocol):
    def __call__(self, payload: FoodAnalyzeMockRequest) -> FoodAnalysis | AnalyzerResult:
        ...


AnalyzerInput = FoodAnalysisCallable | Callable[[], FoodAnalysisCallable]


def run_food_analysis_evaluation(analyzer: AnalyzerInput | None = None) -> EvaluationResult:
    cases_raw = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    cases = [EvaluationCase.model_validate(case) for case in cases_raw["cases"]]
    return evaluate_food_analysis_cases(cases, analyzer=analyzer)


def run_fake_ai_food_analysis_evaluation() -> EvaluationResult:
    return run_food_analysis_evaluation(
        analyzer=lambda: AIFoodAnalyzer(provider=FakeAIProvider()).analyze,
    )


def evaluate_food_analysis_cases(
    cases: list[EvaluationCase],
    analyzer: AnalyzerInput | None = None,
) -> EvaluationResult:
    analyze = _resolve_analyzer(analyzer)
    case_results = [_run_case(case, analyze=analyze) for case in cases]
    passed = sum(1 for result in case_results if result.passed)

    return EvaluationResult(
        schema_version="evaluation.v1",
        total=len(case_results),
        passed=passed,
        failed=len(case_results) - passed,
        cases=case_results,
    )


def _run_case(
    case: EvaluationCase,
    analyze: FoodAnalysisCallable | None = None,
) -> CaseResult:
    analyze_case = analyze or MockFoodAnalyzer().analyze
    analysis_result = analyze_case(case.input)
    analysis = (
        analysis_result.analysis
        if isinstance(analysis_result, AnalyzerResult)
        else analysis_result
    )
    expected = case.expected_summary
    diffs: list[str] = []

    if analysis.items_count != expected.items_count:
        diffs.append(
            f"items_count: expected {expected.items_count}, got {analysis.items_count}"
        )

    actual_names = sorted(item.name for item in analysis.items)
    expected_names = sorted(expected.item_names)
    if actual_names != expected_names:
        diffs.append(f"item_names: expected {expected_names}, got {actual_names}")

    actual_flags = sorted(analysis.safety_flags)
    expected_flags = sorted(expected.safety_flags)
    if actual_flags != expected_flags:
        diffs.append(f"safety_flags: expected {expected_flags}, got {actual_flags}")

    total_calories = analysis.total_calories
    min_floor = expected.total_calories.min_at_least
    max_ceiling = expected.total_calories.max_at_most
    if total_calories.min < min_floor:
        diffs.append(
            f"total_calories.min {total_calories.min} < min_at_least {min_floor}"
        )
    if total_calories.max > max_ceiling:
        diffs.append(
            f"total_calories.max {total_calories.max} > max_at_most {max_ceiling}"
        )

    return CaseResult(
        case_id=case.case_id,
        passed=len(diffs) == 0,
        diffs=diffs,
    )


def _resolve_analyzer(analyzer: AnalyzerInput | None) -> FoodAnalysisCallable:
    if analyzer is None:
        return MockFoodAnalyzer().analyze

    try:
        candidate = analyzer()
    except TypeError:
        return analyzer

    return candidate
