import json

from app.evaluation.__main__ import generate_evaluation_reports


def test_evaluation_report_generator_runs_and_is_deterministic(tmp_path) -> None:
    markdown_report_path = tmp_path / "REPORT.md"
    json_report_path = tmp_path / "report.json"

    first = generate_evaluation_reports(
        markdown_report_path=markdown_report_path,
        json_report_path=json_report_path,
    )
    first_markdown = markdown_report_path.read_text(encoding="utf-8")
    first_json = json_report_path.read_text(encoding="utf-8")

    second = generate_evaluation_reports(
        markdown_report_path=markdown_report_path,
        json_report_path=json_report_path,
    )

    assert first["summary"]["failed"] == 0
    assert second["summary"]["failed"] == 0
    assert first_markdown
    assert first_json
    assert markdown_report_path.read_text(encoding="utf-8") == first_markdown
    assert json_report_path.read_text(encoding="utf-8") == first_json

    parsed = json.loads(first_json)
    assert parsed["provider_modes_covered"] == ["mock", "ai/fake"]
    assert parsed["all_cases_validate_against_food_analysis"] is True
