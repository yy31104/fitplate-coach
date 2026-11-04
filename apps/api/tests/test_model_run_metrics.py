import json
from pathlib import Path

from app.observability.metrics import (
    load_model_runs,
    render_json,
    render_markdown,
    summarize_model_runs,
)
from app.observability.model_run import ModelRun

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
SAMPLE_PATH = API_ROOT / "observability_samples" / "model_runs.sample.jsonl"
MARKDOWN_REPORT_PATH = REPO_ROOT / "devlog" / "evidence" / "metrics" / "METRICS_REPORT.md"
JSON_REPORT_PATH = REPO_ROOT / "devlog" / "evidence" / "metrics" / "metrics_report.json"


def test_load_model_runs_parses_valid_jsonl() -> None:
    text = json.dumps(_record_dict(request_id="sample-001")) + "\n"

    records = load_model_runs(text)

    assert len(records) == 1
    assert records[0].request_id == "sample-001"


def test_load_model_runs_skips_malformed_and_non_model_run_v1_lines() -> None:
    text = "\n".join(
        [
            "{not-json",
            json.dumps({"model_run_schema_version": "other.v1"}),
            json.dumps(["not", "an", "object"]),
            json.dumps(_record_dict(request_id="sample-002")),
        ]
    )

    records = load_model_runs(text)

    assert len(records) == 1
    assert records[0].request_id == "sample-002"


def test_summarize_model_runs_handles_empty_input() -> None:
    metrics = summarize_model_runs([])

    assert metrics.total_runs == 0
    assert metrics.error_rate == 0.0
    assert metrics.success_rate == 0.0
    assert metrics.latency_ms.count == 0
    assert metrics.latency_ms.min is None
    assert metrics.latency_ms.max is None
    assert metrics.latency_ms.mean is None
    assert metrics.total_cost_usd == 0.0


def test_summarize_model_runs_handles_single_record() -> None:
    metrics = summarize_model_runs(
        [
            _record(
                route="POST /api/v0/food/analyze/mock",
                mode="mock",
                model="mock",
                latency_ms=12,
            )
        ]
    )

    assert metrics.total_runs == 1
    assert metrics.runs_by_route == {"POST /api/v0/food/analyze/mock": 1}
    assert metrics.runs_by_mode == {"mock": 1}
    assert metrics.runs_by_model == {"mock": 1}
    assert metrics.runs_by_prompt == {"none": 1}


def test_summarize_model_runs_aggregates_multiple_records() -> None:
    metrics = summarize_model_runs(_sample_records())

    assert metrics.total_runs == 6
    assert metrics.runs_by_route == {
        "POST /api/v0/food/analyze": 1,
        "POST /api/v0/food/analyze/mock": 4,
        "POST /api/v0/food/corrections/mock": 1,
    }
    assert metrics.runs_by_mode == {"ai": 3, "mock": 3}
    assert metrics.runs_by_model == {"fake-food-vision-v1": 3, "mock": 3}
    assert metrics.runs_by_prompt == {"food_analysis@v1": 3, "none": 3}
    assert metrics.schema_versions_seen == ["model_run.v1"]


def test_summarize_model_runs_computes_error_rate() -> None:
    metrics = summarize_model_runs(
        [
            _record(request_id="success"),
            _record(request_id="error", error_code="analysis_failed"),
        ]
    )

    assert metrics.error_count == 1
    assert metrics.error_rate == 0.5
    assert metrics.success_rate == 0.5
    assert metrics.errors_by_code == {"analysis_failed": 1}


def test_summarize_model_runs_counts_safety_flags() -> None:
    metrics = summarize_model_runs(
        [
            _record(request_id="one", safety_flags=["low_confidence"]),
            _record(
                request_id="two",
                safety_flags=["low_confidence", "non_food_image"],
            ),
        ]
    )

    assert metrics.runs_with_any_safety_flag == 2
    assert metrics.safety_flag_counts == {
        "low_confidence": 2,
        "non_food_image": 1,
    }


def test_summarize_model_runs_computes_latency_stats() -> None:
    metrics = summarize_model_runs(
        [
            _record(request_id="one", latency_ms=10),
            _record(request_id="two", latency_ms=25),
            _record(request_id="three", latency_ms=26),
        ]
    )

    assert metrics.latency_ms.count == 3
    assert metrics.latency_ms.min == 10
    assert metrics.latency_ms.max == 26
    assert metrics.latency_ms.mean == 20.3


def test_summarize_model_runs_sums_tokens_and_costs() -> None:
    metrics = summarize_model_runs(
        [
            _record(request_id="one", input_tokens=10, output_tokens=5, cost_usd=0.0011114),
            _record(request_id="two", input_tokens=20, output_tokens=7, cost_usd=0.0022224),
        ]
    )

    assert metrics.total_input_tokens == 30
    assert metrics.total_output_tokens == 12
    assert metrics.total_cost_usd == 0.003334
    assert metrics.mean_cost_usd == 0.001667


def test_render_markdown_and_json_are_deterministic() -> None:
    metrics = summarize_model_runs(_sample_records())

    assert render_markdown(metrics) == render_markdown(metrics)
    assert render_json(metrics) == render_json(metrics)
    assert json.loads(render_json(metrics))["schema_version"] == "model_run_metrics.v1"


def test_committed_reports_regenerate_byte_identically_from_fixture() -> None:
    metrics = summarize_model_runs(_sample_records())

    assert render_markdown(metrics) == MARKDOWN_REPORT_PATH.read_text(encoding="utf-8")
    assert render_json(metrics) == JSON_REPORT_PATH.read_text(encoding="utf-8")


def test_rendered_reports_do_not_emit_private_or_raw_fields() -> None:
    records = _sample_records()
    rendered = render_markdown(summarize_model_runs(records)) + render_json(
        summarize_model_runs(records)
    )
    rendered_lower = rendered.lower()
    forbidden_terms = [
        "input_summary",
        "output_summary",
        "request_id",
        "started_at",
        "ended_at",
        "error_message",
        "base64",
        "api key",
        "api_key",
        "raw_provider_response",
    ]
    sample_filenames = [
        str(record.input_summary["filename"])
        for record in records
        if "filename" in record.input_summary
    ]

    for term in forbidden_terms:
        assert term not in rendered_lower
    for filename in sample_filenames:
        assert filename not in rendered


def _sample_records() -> list[ModelRun]:
    return load_model_runs(SAMPLE_PATH.read_text(encoding="utf-8"))


def _record(
    *,
    request_id: str = "sample-request",
    route: str = "POST /api/v0/food/analyze/mock",
    mode: str = "mock",
    model: str = "mock",
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    latency_ms: int = 10,
    safety_flags: list[str] | None = None,
    error_code: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> ModelRun:
    return ModelRun.model_validate(
        _record_dict(
            request_id=request_id,
            route=route,
            mode=mode,
            model=model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=latency_ms,
            safety_flags=safety_flags or [],
            error_code=error_code,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
    )


def _record_dict(
    *,
    request_id: str = "sample-request",
    route: str = "POST /api/v0/food/analyze/mock",
    mode: str = "mock",
    model: str = "mock",
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    latency_ms: int = 10,
    safety_flags: list[str] | None = None,
    error_code: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "model_run_schema_version": "model_run.v1",
        "route": route,
        "mode": mode,
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "model": model,
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:00:00.010000+00:00",
        "latency_ms": latency_ms,
        "input_summary": {"filename": "synthetic-test-input.jpg"},
        "output_summary": {"items_count": 1},
        "safety_flags": safety_flags or [],
        "error_code": error_code,
        "error_message": "Synthetic error." if error_code else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    }
