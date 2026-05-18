import logging
from pathlib import Path

from app.observability.model_run import ModelRun

logger = logging.getLogger(__name__)

LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "model_runs.jsonl"


def write_model_run(record: ModelRun) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = record.model_dump_json() + "\n"
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(line)
    except Exception:
        logger.exception("Failed to write model run log")
