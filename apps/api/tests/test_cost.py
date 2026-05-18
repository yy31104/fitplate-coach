import json
from datetime import UTC, datetime

from app.ai.cost import check_monthly_cost_cap, month_to_date_ai_cost
from app.config import Settings


NOW = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)


def test_missing_log_returns_zero(tmp_path) -> None:
    assert month_to_date_ai_cost(NOW, tmp_path / "missing.jsonl") == 0.0


def test_empty_log_returns_zero(tmp_path) -> None:
    log_path = tmp_path / "model_runs.jsonl"
    log_path.write_text("", encoding="utf-8")

    assert month_to_date_ai_cost(NOW, log_path) == 0.0


def test_mock_only_entries_return_zero(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        [{"mode": "mock", "started_at": NOW.isoformat(), "cost_usd": 4.0}],
    )

    assert month_to_date_ai_cost(NOW, log_path) == 0.0


def test_current_month_ai_entry_sums(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        [{"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 1.25}],
    )

    assert month_to_date_ai_cost(NOW, log_path) == 1.25


def test_multiple_current_month_ai_entries_sum(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        [
            {"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 1.25},
            {"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 2.75},
        ],
    )

    assert month_to_date_ai_cost(NOW, log_path) == 4.0


def test_prior_month_ai_entry_excluded(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        [
            {"mode": "ai", "started_at": "2026-04-30T12:00:00+00:00", "cost_usd": 9.0},
            {"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 1.0},
        ],
    )

    assert month_to_date_ai_cost(NOW, log_path) == 1.0


def test_malformed_lines_are_skipped(tmp_path) -> None:
    log_path = tmp_path / "model_runs.jsonl"
    log_path.write_text(
        "\n".join(
            [
                "{not-json",
                json.dumps({"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 2.0}),
            ]
        ),
        encoding="utf-8",
    )

    assert month_to_date_ai_cost(NOW, log_path) == 2.0


def test_cap_zero_is_disabled(tmp_path) -> None:
    settings = Settings(ai_mode="ai", monthly_cost_cap_usd=0.0)
    log_path = _write_log(
        tmp_path,
        [{"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 99.0}],
    )

    assert check_monthly_cost_cap(settings, NOW, log_path) is None


def test_mock_mode_is_disabled(tmp_path) -> None:
    settings = Settings(ai_mode="mock", monthly_cost_cap_usd=1.0)
    log_path = _write_log(
        tmp_path,
        [{"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 99.0}],
    )

    assert check_monthly_cost_cap(settings, NOW, log_path) is None


def test_cap_exceeded_returns_error_response(tmp_path) -> None:
    settings = Settings(ai_mode="ai", monthly_cost_cap_usd=1.0)
    log_path = _write_log(
        tmp_path,
        [{"mode": "ai", "started_at": NOW.isoformat(), "cost_usd": 1.0}],
    )

    error = check_monthly_cost_cap(settings, NOW, log_path)

    assert error is not None
    assert error.code == "cost_cap_exceeded"


def _write_log(tmp_path, records: list[dict[str, object]]):
    log_path = tmp_path / "model_runs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )
    return log_path
