import json
from pathlib import Path
from typing import Any, Callable

from app.ai.analyzer import AIFoodAnalyzer, AnalyzerResult, MockFoodAnalyzer
from app.ai.provider import FakeAIProvider
from app.evaluation.runner import (
    _CASES_PATH,
    EvaluationCase,
    EvaluationResult,
    run_fake_ai_food_analysis_evaluation,
    run_food_analysis_evaluation,
)
from app.schemas.food import FoodAnalysis, FoodAnalyzeMockRequest

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
DEFAULT_MARKDOWN_REPORT_PATH = REPO_ROOT / "docs" / "evaluation" / "REPORT.md"
DEFAULT_JSON_REPORT_PATH = API_ROOT / "evaluation" / "report.json"

AnalyzeCallable = Callable[[FoodAnalyzeMockRequest], FoodAnalysis | AnalyzerResult]


def main() -> None:
    report = generate_evaluation_reports()
    summary = report["summary"]
    modes = " + ".join(report["provider_modes_covered"])
    print(
        f"{report['schema_version']} {modes}: "
        f"{summary['total']} total, {summary['passed']} passed, {summary['failed']} failed"
    )
    print(f"Wrote {DEFAULT_MARKDOWN_REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Wrote {DEFAULT_JSON_REPORT_PATH.relative_to(REPO_ROOT)}")


def generate_evaluation_reports(
    *,
    markdown_report_path: Path = DEFAULT_MARKDOWN_REPORT_PATH,
    json_report_path: Path = DEFAULT_JSON_REPORT_PATH,
) -> dict[str, Any]:
    mock_analyzer = MockFoodAnalyzer()
    fake_ai_analyzer = AIFoodAnalyzer(provider=FakeAIProvider())
    mock_result = run_food_analysis_evaluation(analyzer=mock_analyzer.analyze)
    fake_ai_result = run_fake_ai_food_analysis_evaluation()
    cases = _load_cases()

    provider_reports = [
        _provider_report(
            provider_mode="mock",
            evaluation_result=mock_result,
            analyze=mock_analyzer.analyze,
            cases=cases,
        ),
        _provider_report(
            provider_mode="ai/fake",
            evaluation_result=fake_ai_result,
            analyze=fake_ai_analyzer.analyze,
            cases=cases,
        ),
    ]
    total = sum(provider["total"] for provider in provider_reports)
    passed = sum(provider["passed"] for provider in provider_reports)
    failed = sum(provider["failed"] for provider in provider_reports)

    report = {
        "schema_version": "evaluation.v1",
        "provider_modes_covered": ["mock", "ai/fake"],
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
        },
        "all_cases_validate_against_food_analysis": True,
        "cost_latency_note": "Cost and latency are 0 because no real provider runs.",
        "providers": provider_reports,
    }

    markdown_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_report_path.write_text(_markdown_report(report), encoding="utf-8")
    json_report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def _provider_report(
    *,
    provider_mode: str,
    evaluation_result: EvaluationResult,
    analyze: AnalyzeCallable,
    cases: list[EvaluationCase],
) -> dict[str, Any]:
    results_by_case_id = {case.case_id: case for case in evaluation_result.cases}
    case_reports = []

    for case in cases:
        result = results_by_case_id[case.case_id]
        analysis = _validated_analysis(analyze(case.input))
        case_reports.append(
            {
                "case_id": case.case_id,
                "passed": result.passed,
                "safety_flags": analysis.safety_flags,
                "total_calories": {
                    "min": analysis.total_calories.min,
                    "max": analysis.total_calories.max,
                    "point_estimate": analysis.total_calories.point_estimate,
                },
                "expected_total_calorie_bounds": {
                    "min_at_least": case.expected_summary.total_calories.min_at_least,
                    "max_at_most": case.expected_summary.total_calories.max_at_most,
                },
                "diffs": result.diffs,
            }
        )

    return {
        "provider_mode": provider_mode,
        "total": evaluation_result.total,
        "passed": evaluation_result.passed,
        "failed": evaluation_result.failed,
        "cost_usd": 0.0,
        "latency_ms": 0,
        "cases": case_reports,
    }


def _validated_analysis(result: FoodAnalysis | AnalyzerResult) -> FoodAnalysis:
    analysis = result.analysis if isinstance(result, AnalyzerResult) else result
    return FoodAnalysis.model_validate(analysis.model_dump(mode="json"))


def _load_cases() -> list[EvaluationCase]:
    parsed = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return [EvaluationCase.model_validate(case) for case in parsed["cases"]]


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Evaluation Report",
        "",
        f"schema_version: `{report['schema_version']}`",
        "",
        f"Provider modes covered: {' + '.join(report['provider_modes_covered'])}",
        "",
        f"Total: {summary['total']}",
        f"Passed: {summary['passed']}",
        f"Failed: {summary['failed']}",
        "",
        "All cases validate against `FoodAnalysis`.",
        "",
        "Cost and latency are 0 because no real provider runs.",
        "",
    ]

    for provider in report["providers"]:
        lines.extend(
            [
                f"## {provider['provider_mode']}",
                "",
                f"Total: {provider['total']}",
                f"Passed: {provider['passed']}",
                f"Failed: {provider['failed']}",
                "",
                "| Case | Passed | Safety flags | Total calorie bounds | Expected bounds |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for case in provider["cases"]:
            calories = case["total_calories"]
            expected = case["expected_total_calorie_bounds"]
            safety_flags = ", ".join(case["safety_flags"]) or "none"
            lines.append(
                "| "
                f"{case['case_id']} | "
                f"{str(case['passed']).lower()} | "
                f"{safety_flags} | "
                f"{calories['min']}-{calories['max']} "
                f"(point {calories['point_estimate']}) | "
                f"min >= {expected['min_at_least']}, "
                f"max <= {expected['max_at_most']} |"
            )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
