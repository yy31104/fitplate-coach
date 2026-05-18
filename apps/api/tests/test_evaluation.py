import json

from app.evaluation.runner import (
    _CASES_PATH,
    EvaluationCase,
    evaluate_food_analysis_cases,
    run_fake_ai_food_analysis_evaluation,
    run_food_analysis_evaluation,
)
from app.mock.food_analyzer import analyze_food_metadata


def test_cases_file_parses_as_valid_json() -> None:
    parsed = json.loads(_CASES_PATH.read_text(encoding="utf-8"))

    assert parsed["schema_version"] == "evaluation.v1"


def test_cases_file_has_required_structure() -> None:
    parsed = json.loads(_CASES_PATH.read_text(encoding="utf-8"))

    assert "schema_version" in parsed
    assert "cases" in parsed
    assert isinstance(parsed["cases"], list)
    assert parsed["cases"]

    for case in parsed["cases"]:
        assert "case_id" in case
        assert "input" in case
        assert "expected_summary" in case


def test_evaluation_runner_passes_all_cases_on_mock_analyzer() -> None:
    result = run_food_analysis_evaluation()

    assert result.failed == 0


def test_evaluation_runner_passes_all_cases_on_fake_ai_analyzer() -> None:
    result = run_fake_ai_food_analysis_evaluation()

    assert result.failed == 0


def test_evaluation_result_counts_match_cases() -> None:
    result = run_food_analysis_evaluation()

    assert result.total == 4
    assert result.passed + result.failed == result.total


def test_evaluation_result_has_schema_version() -> None:
    result = run_food_analysis_evaluation()

    assert result.schema_version == "evaluation.v1"


def test_failed_case_produces_non_empty_diffs() -> None:
    bad_case = EvaluationCase.model_validate(
        {
            "case_id": "bad-standard-case",
            "description": "Deliberately wrong case to test diff reporting.",
            "input": {
                "filename": "lunch-photo.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 345678,
                "last_modified_ms": 1710000000000,
            },
            "expected_summary": {
                "items_count": 99,
                "item_names": [],
                "safety_flags": ["low_confidence"],
                "total_calories": {
                    "min_at_least": 9999,
                    "max_at_most": 1,
                },
            },
        }
    )

    result = evaluate_food_analysis_cases([bad_case])

    assert result.failed == 1
    assert result.cases[0].passed is False
    assert result.cases[0].diffs


def test_each_case_filename_produces_expected_mock_summary() -> None:
    parsed = json.loads(_CASES_PATH.read_text(encoding="utf-8"))

    for raw_case in parsed["cases"]:
        case = EvaluationCase.model_validate(raw_case)
        analysis = analyze_food_metadata(case.input)

        assert sorted(item.name for item in analysis.items) == sorted(
            case.expected_summary.item_names
        )
        assert sorted(analysis.safety_flags) == sorted(case.expected_summary.safety_flags)
