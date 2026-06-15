import json
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.observability.model_run import ModelRun


class LatencyMetrics(BaseModel):
    count: int
    min: int | None
    max: int | None
    mean: float | None


class ModelRunMetrics(BaseModel):
    schema_version: Literal["model_run_metrics.v1"]
    total_runs: int
    runs_by_route: dict[str, int]
    runs_by_mode: dict[str, int]
    runs_by_model: dict[str, int]
    runs_by_prompt: dict[str, int]
    error_count: int
    error_rate: float
    success_rate: float
    errors_by_code: dict[str, int]
    safety_flag_counts: dict[str, int]
    runs_with_any_safety_flag: int
    latency_ms: LatencyMetrics
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    mean_cost_usd: float
    schema_versions_seen: list[str]


def load_model_runs(text: str) -> list[ModelRun]:
    records: list[ModelRun] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if not isinstance(raw, dict):
            continue
        if raw.get("model_run_schema_version") != "model_run.v1":
            continue

        try:
            records.append(ModelRun.model_validate(raw))
        except ValidationError:
            continue

    return records


def summarize_model_runs(records: list[ModelRun]) -> ModelRunMetrics:
    total_runs = len(records)
    error_count = sum(1 for record in records if record.error_code is not None)
    total_cost = sum(record.cost_usd for record in records)

    return ModelRunMetrics(
        schema_version="model_run_metrics.v1",
        total_runs=total_runs,
        runs_by_route=_sorted_counts(record.route for record in records),
        runs_by_mode=_sorted_counts(record.mode for record in records),
        runs_by_model=_sorted_counts(record.model for record in records),
        runs_by_prompt=_sorted_counts(_prompt_key(record) for record in records),
        error_count=error_count,
        error_rate=_rate(error_count, total_runs),
        success_rate=_rate(total_runs - error_count, total_runs),
        errors_by_code=_sorted_counts(
            record.error_code for record in records if record.error_code is not None
        ),
        safety_flag_counts=_sorted_counts(
            flag for record in records for flag in record.safety_flags
        ),
        runs_with_any_safety_flag=sum(1 for record in records if record.safety_flags),
        latency_ms=_latency_metrics([record.latency_ms for record in records]),
        total_input_tokens=sum(record.input_tokens for record in records),
        total_output_tokens=sum(record.output_tokens for record in records),
        total_cost_usd=round(total_cost, 6),
        mean_cost_usd=round(total_cost / total_runs, 6) if total_runs else 0.0,
        schema_versions_seen=sorted(
            {record.model_run_schema_version for record in records}
        ),
    )


def render_json(metrics: ModelRunMetrics) -> str:
    payload = metrics.model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_markdown(metrics: ModelRunMetrics) -> str:
    lines = [
        "# Model Run Metrics Report",
        "",
        f"schema_version: `{metrics.schema_version}`",
        "",
        f"Total runs: {metrics.total_runs}",
        f"Success rate: {metrics.success_rate:.4f}",
        f"Error rate: {metrics.error_rate:.4f}",
        f"Error count: {metrics.error_count}",
        f"Runs with safety flags: {metrics.runs_with_any_safety_flag}",
        "",
        "## Latency",
        "",
        f"Count: {metrics.latency_ms.count}",
        f"Min: {_format_optional_int(metrics.latency_ms.min)} ms",
        f"Max: {_format_optional_int(metrics.latency_ms.max)} ms",
        f"Mean: {_format_optional_float(metrics.latency_ms.mean, 1)} ms",
        "",
        "## Tokens And Cost",
        "",
        f"Total input tokens: {metrics.total_input_tokens}",
        f"Total output tokens: {metrics.total_output_tokens}",
        f"Total cost USD: {metrics.total_cost_usd:.6f}",
        f"Mean cost USD: {metrics.mean_cost_usd:.6f}",
        "",
        "## Breakdowns",
        "",
        _markdown_counts("Runs by route", metrics.runs_by_route),
        "",
        _markdown_counts("Runs by mode", metrics.runs_by_mode),
        "",
        _markdown_counts("Runs by model", metrics.runs_by_model),
        "",
        _markdown_counts("Runs by prompt", metrics.runs_by_prompt),
        "",
        _markdown_counts("Errors by code", metrics.errors_by_code),
        "",
        _markdown_counts("Safety flag counts", metrics.safety_flag_counts),
        "",
        "## Schema Versions Seen",
        "",
    ]
    lines.extend(f"- `{schema_version}`" for schema_version in metrics.schema_versions_seen)
    if not metrics.schema_versions_seen:
        lines.append("- none")
    lines.append("")

    return "\n".join(lines)


def _sorted_counts(values) -> dict[str, int]:
    counts = Counter(str(value) for value in values)
    return {key: counts[key] for key in sorted(counts)}


def _prompt_key(record: ModelRun) -> str:
    if record.prompt_name is None and record.prompt_version is None:
        return "none"
    if record.prompt_name is None:
        return f"unknown@{record.prompt_version}"
    if record.prompt_version is None:
        return f"{record.prompt_name}@unknown"
    return f"{record.prompt_name}@{record.prompt_version}"


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _latency_metrics(latencies: list[int]) -> LatencyMetrics:
    if not latencies:
        return LatencyMetrics(count=0, min=None, max=None, mean=None)

    return LatencyMetrics(
        count=len(latencies),
        min=min(latencies),
        max=max(latencies),
        mean=round(sum(latencies) / len(latencies), 1),
    )


def _markdown_counts(title: str, counts: dict[str, int]) -> str:
    lines = [f"### {title}", ""]
    if not counts:
        lines.append("- none")
    else:
        lines.extend(f"- `{key}`: {value}" for key, value in counts.items())
    return "\n".join(lines)


def _format_optional_int(value: int | None) -> str:
    return "none" if value is None else str(value)


def _format_optional_float(value: float | None, digits: int) -> str:
    return "none" if value is None else f"{value:.{digits}f}"
