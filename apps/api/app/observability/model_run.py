from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.food import ErrorCode, SafetyFlag


class ModelRun(BaseModel):
    request_id: str
    model_run_schema_version: Literal["model_run.v1"]
    route: str
    mode: Literal["mock", "ai"]
    prompt_name: str | None
    prompt_version: str | None
    model: str
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    safety_flags: list[SafetyFlag]
    error_code: ErrorCode | None
    error_message: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float


def now_utc() -> datetime:
    return datetime.now(UTC)


def latency_ms(started_at: datetime, ended_at: datetime) -> int:
    return max(0, round((ended_at - started_at).total_seconds() * 1000))


def build_model_run(
    *,
    request_id: str,
    route: str,
    mode: Literal["mock", "ai"] = "mock",
    model: str = "mock",
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    started_at: datetime,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    safety_flags: list[SafetyFlag] | None = None,
    error_code: ErrorCode | None = None,
    error_message: str | None = None,
    ended_at: datetime | None = None,
) -> ModelRun:
    completed_at = ended_at or now_utc()

    return ModelRun(
        request_id=request_id,
        model_run_schema_version="model_run.v1",
        route=route,
        mode=mode,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        model=model,
        started_at=started_at,
        ended_at=completed_at,
        latency_ms=latency_ms(started_at, completed_at),
        input_summary=input_summary,
        output_summary=output_summary,
        safety_flags=safety_flags or [],
        error_code=error_code,
        error_message=error_message,
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
    )
