import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.food import ErrorResponse

logger = logging.getLogger(__name__)


def month_to_date_ai_cost(now: datetime, log_path: Path) -> float:
    if not log_path.exists():
        return 0.0

    current_month = _as_utc(now)
    total = 0.0

    try:
        with log_path.open(encoding="utf-8") as log_file:
            for line in log_file:
                try:
                    record = json.loads(line)
                    if _is_current_month_ai_record(record, current_month):
                        total += float(record.get("cost_usd", 0.0))
                except Exception:
                    logger.warning("Skipping malformed model run log line")
    except Exception:
        logger.warning("Unable to read model run log for cost cap", exc_info=True)
        return 0.0

    return total


def check_monthly_cost_cap(
    settings: Settings,
    now: datetime,
    log_path: Path,
) -> ErrorResponse | None:
    if settings.ai_mode != "ai" or settings.monthly_cost_cap_usd <= 0:
        return None

    if month_to_date_ai_cost(now, log_path) >= settings.monthly_cost_cap_usd:
        return ErrorResponse(
            code="cost_cap_exceeded",
            message="Monthly AI cost cap reached. Please try again later.",
        )

    return None


def _is_current_month_ai_record(record: Any, current_month: datetime) -> bool:
    if not isinstance(record, dict) or record.get("mode") != "ai":
        return False

    started_at_raw = record.get("started_at")
    if not isinstance(started_at_raw, str):
        return False

    try:
        started_at = _as_utc(datetime.fromisoformat(started_at_raw.replace("Z", "+00:00")))
    except ValueError:
        logger.warning("Skipping model run with invalid started_at")
        return False

    return (
        started_at.year == current_month.year
        and started_at.month == current_month.month
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
